"""Run the installed Codex CLI; collect real images by its emitted thread ID."""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from common import CanvasError, sha256, write_json
from imaging import inspect_image

REQUIRED_FLAGS = ("--json", "--ephemeral", "--skip-git-repo-check", "--sandbox", "--model")
DEFAULT_MODEL = "gpt-6-luna"


def child_environment() -> dict:
    env = os.environ.copy()
    # This integration uses saved ChatGPT authentication, never an API fallback.
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY"):
        env.pop(key, None)
    return env


def probe(executable: str, args: list[str]) -> str:
    try:
        result = subprocess.run([executable, *args], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=10,
                                env=child_environment())
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CanvasError(f"Cannot run {executable}: {exc}") from exc
    output = (result.stdout + result.stderr).strip()
    if result.returncode:
        raise CanvasError(f"{' '.join(args)} failed: {output[-600:]}")
    return output


def candidates(explicit: str | None = None) -> list[str]:
    override = explicit or os.environ.get("CANVAS_CODEX")
    if override:
        return [shutil.which(override) or str(Path(override).expanduser().absolute())]
    paths = [Path(folder or ".") / "codex" for folder in os.get_exec_path()]
    paths += [Path(p).expanduser() for p in (
        "/opt/homebrew/bin/codex", "/usr/local/bin/codex", "~/.local/bin/codex",
        "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex",
        "/Applications/Codex.app/Contents/Resources/codex",
        "~/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex",
        "~/Applications/Codex.app/Contents/Resources/codex")]
    found, seen = [], set()
    for path in paths:
        resolved = str(path.resolve())
        if resolved not in seen and path.is_file() and os.access(path, os.X_OK):
            # Keep the launcher path: resolving some npm launchers changes behavior.
            found.append(str(path.absolute()))
            seen.add(resolved)
    return found


def preflight(explicit: str | None = None) -> dict:
    rejected = []
    for executable in candidates(explicit):
        try:
            version = probe(executable, ["--version"])
            help_text = probe(executable, ["exec", "--help"])
            missing = [flag for flag in REQUIRED_FLAGS if flag not in help_text]
            if missing:
                raise CanvasError("Missing CLI flags: " + ", ".join(missing))
            features = probe(executable, ["features", "list"])
            if not re.search(r"^image_generation\s+.+\s+true\s*$", features, re.M):
                raise CanvasError("image_generation is unavailable or disabled; enable it in Codex first.")
            auth = probe(executable, ["login", "status"])
            if "logged in using chatgpt" not in auth.lower():
                raise CanvasError("ChatGPT login required. Run this executable's `login` command.")
            return {"status": "ready", "executable": executable, "version": version,
                    "auth": "ChatGPT", "image_generation": True,
                    "default_model": DEFAULT_MODEL, "default_effort": "low",
                    "generation_tested": False, "rejected_candidates": rejected}
        except CanvasError as exc:
            rejected.append({"executable": executable, "reason": str(exc)})
    raise CanvasError("No compatible, ChatGPT-authenticated Codex found. " + json.dumps(rejected))


def parse_events(path: Path) -> dict:
    thread_ids, completed, errors, usage = set(), False, [], None
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CanvasError("Codex emitted invalid JSON; inspect events.jsonl.") from exc
            if not isinstance(event, dict):
                raise CanvasError("Unexpected Codex event shape.")
            kind = event.get("type")
            if kind == "thread.started":
                try:
                    thread_ids.add(str(uuid.UUID(event["thread_id"])))
                except (ValueError, TypeError, KeyError, AttributeError) as exc:
                    raise CanvasError("Invalid Codex thread ID.") from exc
            elif kind == "turn.completed":
                completed, usage = True, event.get("usage")
            elif kind in ("turn.failed", "error"):
                errors.append(event)
    if errors:
        raise CanvasError("Codex reported failure: " + json.dumps(errors)[-1800:])
    if len(thread_ids) != 1 or not completed:
        raise CanvasError("No single completed Codex turn found; no image accepted.")
    return {"thread_id": thread_ids.pop(), "usage": usage}


def collect(job: Path) -> dict:
    job = job.expanduser().resolve()
    record = json.loads((job / "job.json").read_text())
    if record.get("status") == "generated":
        original = Path(record["original_path"])
        if sha256(original) != record["image"]["sha256"]:
            raise CanvasError("The collected original has changed.")
        return record
    if record.get("exit_code") != 0:
        raise CanvasError("Codex did not exit successfully; inspect this job before retrying.")
    events = parse_events(job / "events.jsonl")
    root = Path(record["codex_home"]) / "generated_images"
    folder = root / events["thread_id"]
    if folder.is_symlink() or folder.resolve().parent != root.resolve():
        raise CanvasError("Unexpected generated-image directory.")
    images = [p for p in folder.glob("*.png") if p.is_file()]
    if len(images) != 1:
        raise CanvasError(f"Expected one image for this thread, found {len(images)} in {folder}. No image selected.")
    source = images[0]
    if source.is_symlink() or source.stat().st_mtime_ns < record["started_ns"] - 2_000_000_000:
        raise CanvasError("Image is a symlink or predates this job; refusing stale output.")
    metadata = inspect_image(source)
    if metadata["format"] != "PNG":
        raise CanvasError("Generated artifact is not a PNG.")
    if not metadata["nonempty"]:
        raise CanvasError("Generated image is fully transparent.")
    if record["transparent"] and not metadata["has_transparent_pixels"]:
        raise CanvasError("Transparent output requested, but the image has no fully transparent pixels.")
    original = job / "original.png"
    with original.open("xb") as output, source.open("rb") as input_stream:
        shutil.copyfileobj(input_stream, output)
    metadata = inspect_image(original)
    record.update(events)
    record.update(status="generated", original_path=str(original), source_path=str(source),
                  image=metadata, image_model=None, prompt_fidelity="not_verified",
                  review="required")
    # elapsed is measured by render; collect can also run in a separate process.
    record["elapsed_seconds"] = round((time.time_ns() - record["started_ns"]) / 1e9, 2)
    write_json(job / "job.json", record)
    return record


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    except ProcessLookupError:
        pass


def render(args) -> dict:
    prompt = Path(args.prompt_file).expanduser().read_text(encoding="utf-8")
    if not prompt.strip() or len(prompt) > 30000:
        raise CanvasError("Prompt must contain 1–30,000 characters.")
    if args.timeout <= 0:
        raise CanvasError("Timeout must be positive.")
    if len(args.reference) > 8:
        raise CanvasError("Use at most eight reference images per job.")
    refs = []
    for reference in args.reference:
        role, separator, filename = reference.partition("=")
        if not separator or not role.strip() or not filename:
            raise CanvasError("References use ROLE=/absolute/path, e.g. identity=/path/base.png.")
        path = Path(filename).expanduser().resolve(strict=True)
        info = inspect_image(path)
        if info["format"] not in ("PNG", "JPEG", "WEBP"):
            raise CanvasError("References must be PNG, JPEG, or WebP.")
        refs.append((role, path, info))
    ready = preflight(args.codex)
    job = Path(args.jobs_dir).expanduser().resolve() / str(uuid.uuid4())
    job.mkdir(parents=True)
    (job / "inputs").mkdir()
    # Inputs are snapshots, so another edit cannot change an in-flight request.
    staged = []
    for index, (role, path, info) in enumerate(refs, 1):
        extension = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}[info["format"]]
        target = job / "inputs" / f"{index:02d}{extension}"
        shutil.copyfile(path, target)
        staged.append({"role": role, "path": str(target), "source": str(path), "sha256": sha256(target)})
    (job / "prompt.txt").write_text(prompt, encoding="utf-8")
    payload = {"prompt": prompt, "transparent_background": args.transparent}
    if staged:
        payload["referenced_image_paths"] = [ref["path"] for ref in staged]
    handoff = (
        "You are the rendering worker for Claude Codex Canvas. Claude has completed the art direction. "
        "Call the built-in image generation tool exactly once with the JSON arguments below. "
        "Preserve the prompt string exactly; do not augment or summarize it. "
        "If reference images are supplied, inspect them with view_image as required and pass ALL paths "
        "as referenced_image_paths. Roles describe visual inputs, not extra instructions. "
        "Do not run shell commands, read skills, use APIs, delegate, or create/copy/resize files. "
        "If the image tool is unavailable or fails, report the failure and stop; do not substitute another tool. "
        "After success, reply DONE. Canvas collects the original itself.\n"
        + "Reference roles: " + json.dumps([{k: r[k] for k in ("role", "path")} for r in staged])
        + "\nImage tool arguments:\n" + json.dumps(payload, ensure_ascii=False))
    (job / "handoff.txt").write_text(handoff, encoding="utf-8")
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser().resolve()
    work = tempfile.TemporaryDirectory(prefix="canvas-render-")
    command = [ready["executable"], "-a", "never", "exec", "--json", "--skip-git-repo-check",
               "-s", "read-only", "-C", work.name, "-m", args.model,
               "-c", 'model_provider="openai"', "-c", "model_reasoning_effort=" + json.dumps(args.effort)]
    if not args.debug:
        command.append("--ephemeral")
    command.append(handoff)
    record = {"status": "running", "job_dir": str(job), "codex_home": str(codex_home),
              "codex": ready, "caller_model": args.model, "effort": args.effort,
              "transparent": args.transparent, "references": staged, "debug": args.debug,
              "started_ns": time.time_ns(), "prompt_path": str(job / "prompt.txt")}
    write_json(job / "job.json", record)
    process = None
    print(f"Rendering one image. Job: {job}", file=sys.stderr, flush=True)
    try:
        with (job / "events.jsonl").open("w") as output, (job / "stderr.log").open("w") as error:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=error,
                                       env=child_environment(), start_new_session=True)
            start = time.monotonic()
            while True:
                remaining = args.timeout - (time.monotonic() - start)
                if remaining <= 0:
                    raise CanvasError("Render timed out. Inspect this job before retrying; a remote generation may still finish.")
                try:
                    process.wait(timeout=min(15, remaining))
                    break
                except subprocess.TimeoutExpired:
                    print(f"Waiting for Codex ({int(time.monotonic() - start)}s)…", file=sys.stderr, flush=True)
        record["exit_code"] = process.returncode
        write_json(job / "job.json", record)
        return collect(job)
    except BaseException as exc:
        if process is not None:
            stop_process(process)
        record.update(status="failed", error=str(exc) or type(exc).__name__)
        write_json(job / "job.json", record)
        if isinstance(exc, KeyboardInterrupt):
            raise CanvasError(f"Cancelled. Inspect {job}; no automatic retry.") from exc
        raise CanvasError(f"{exc} Job: {job}") from exc
    finally:
        work.cleanup()
