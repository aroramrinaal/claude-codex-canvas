"""Run one Codex render in an isolated job, then hand off to the collector."""
from __future__ import annotations

import contextlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

import handoff
from collector import collect
from common import CanvasError, private_dir, sha256, write_json
from discovery import child_environment, preflight
from images import inspect_image

EXTENSIONS = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}


def read_prompt(filename: str) -> str:
    prompt = Path(filename).expanduser().read_text(encoding="utf-8")
    if not prompt.strip() or len(prompt) > 30000:
        raise CanvasError("Prompt must contain 1–30,000 characters.")
    return prompt


def check_references(values: list[str]) -> list[tuple]:
    if len(values) > 8:
        raise CanvasError("Use at most eight reference images per job.")
    refs = []
    for value in values:
        role, separator, filename = value.partition("=")
        if not separator or not role.strip() or not filename:
            raise CanvasError("References use ROLE=/absolute/path, e.g. identity=/path/base.png.")
        path = Path(filename).expanduser().resolve(strict=True)
        info = inspect_image(path)
        if info["format"] not in EXTENSIONS:
            raise CanvasError("References must be PNG, JPEG, or WebP.")
        refs.append((role, path, info))
    return refs


def stage_references(job: Path, refs: list[tuple]) -> list[dict]:
    # Inputs are snapshots, so another edit cannot change an in-flight request.
    (job / "inputs").mkdir()
    staged = []
    for index, (role, path, info) in enumerate(refs, 1):
        target = job / "inputs" / f"{index:02d}{EXTENSIONS[info['format']]}"
        shutil.copyfile(path, target)
        staged.append({"role": role, "path": str(target), "source": str(path), "sha256": sha256(target)})
    return staged


@contextlib.contextmanager
def stop_on_signals():
    """A tool timeout sends SIGTERM/SIGHUP; treat it as a cancel so Codex is stopped too."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    def cancel(signum, frame):
        raise KeyboardInterrupt
    previous = {s: signal.signal(s, cancel) for s in (signal.SIGTERM, signal.SIGHUP)}
    try:
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


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


def run_codex(command: list[str], job: Path, timeout: float) -> int:
    with (job / "events.jsonl").open("w") as output, (job / "stderr.log").open("w") as error:
        # Its own process group, so stop_process also ends the CLI's native child.
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=error,
                                   env=child_environment(), start_new_session=True)
        try:
            start = time.monotonic()
            while True:
                remaining = timeout - (time.monotonic() - start)
                if remaining <= 0:
                    raise CanvasError("Render timed out. Inspect this job before retrying; a remote generation may still finish.")
                try:
                    return process.wait(timeout=min(15, remaining))
                except subprocess.TimeoutExpired:
                    print(f"Waiting for Codex ({int(time.monotonic() - start)}s)…", file=sys.stderr, flush=True)
        finally:
            stop_process(process)


def render(args) -> dict:
    prompt = read_prompt(args.prompt_file)
    if args.timeout <= 0:
        raise CanvasError("Timeout must be positive.")
    refs = check_references(args.reference)
    ready = preflight(args.codex)
    job = private_dir(Path(args.jobs_dir)).resolve() / str(uuid.uuid4())
    job.mkdir()
    staged = stage_references(job, refs)
    (job / "prompt.txt").write_text(prompt, encoding="utf-8")
    text = handoff.message(prompt, args.transparent, staged)
    (job / "handoff.txt").write_text(text, encoding="utf-8")
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser().resolve()
    record = {"status": "running", "job_dir": str(job), "codex_home": str(codex_home),
              "codex": ready, "caller_model": args.model, "effort": args.effort,
              "transparent": args.transparent, "references": staged, "debug": args.debug,
              "timeout_seconds": args.timeout, "started_ns": time.time_ns(),
              "prompt_path": str(job / "prompt.txt")}
    write_json(job / "job.json", record)
    print(f"Rendering one image. Job: {job}", file=sys.stderr, flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix="canvas-render-") as work, stop_on_signals():
            command = handoff.command(ready["executable"], work, args.model, args.effort, args.debug, text)
            record["exit_code"] = run_codex(command, job, args.timeout)
        write_json(job / "job.json", record)
        return collect(job)
    except BaseException as exc:
        record.update(status="failed", error=str(exc) or type(exc).__name__)
        write_json(job / "job.json", record)
        if isinstance(exc, KeyboardInterrupt):
            raise CanvasError(f"Cancelled; Codex was stopped. Inspect {job}; no automatic retry.") from exc
        raise CanvasError(f"{exc} Job: {job}") from exc
