"""Accept exactly one fresh PNG from the Codex thread this job started."""
from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path

from common import CanvasError, sha256, write_json
from images import inspect_image


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


def thread_image(record: dict, thread_id: str) -> Path:
    # $CODEX_HOME/generated_images/<thread>/ is Codex's storage convention: an adapter boundary.
    root = Path(record["codex_home"]) / "generated_images"
    folder = root / thread_id
    if folder.is_symlink() or folder.resolve().parent != root.resolve():
        raise CanvasError("Unexpected generated-image directory.")
    images = [p for p in folder.glob("*.png") if p.is_file()]
    if len(images) != 1:
        raise CanvasError(f"Expected one image for this thread, found {len(images)} in {folder}. No image selected.")
    source = images[0]
    if source.is_symlink() or source.stat().st_mtime_ns < record["started_ns"] - 2_000_000_000:
        raise CanvasError("Image is a symlink or predates this job; refusing stale output.")
    return source


def validate(source: Path, transparent: bool) -> None:
    metadata = inspect_image(source)
    if metadata["format"] != "PNG":
        raise CanvasError("Generated artifact is not a PNG.")
    if not metadata["nonempty"]:
        raise CanvasError("Generated image is fully transparent.")
    if transparent and not metadata["has_transparent_pixels"]:
        raise CanvasError("Transparent output requested, but the image has no fully transparent pixels.")


def collect(job: Path) -> dict:
    job = job.expanduser().resolve()
    record = json.loads((job / "job.json").read_text())
    if record.get("status") == "generated":
        if sha256(Path(record["original_path"])) != record["image"]["sha256"]:
            raise CanvasError("The collected original has changed.")
        return record
    if record.get("exit_code") != 0:
        raise CanvasError("Codex did not exit successfully; inspect this job before retrying.")
    events = parse_events(job / "events.jsonl")
    source = thread_image(record, events["thread_id"])
    validate(source, record["transparent"])
    original = job / "original.png"
    with original.open("xb") as output, source.open("rb") as input_stream:
        shutil.copyfileobj(input_stream, output)
    record.update(events)
    record.update(status="generated", original_path=str(original), source_path=str(source),
                  image=inspect_image(original), image_model=None, prompt_fidelity="not_verified",
                  review="required")
    # Measured here so a separate `collect` run still reports elapsed time.
    record["elapsed_seconds"] = round((time.time_ns() - record["started_ns"]) / 1e9, 2)
    write_json(job / "job.json", record)
    return record
