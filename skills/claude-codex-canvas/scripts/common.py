"""Local artifact operations. No network or credential handling."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


class CanvasError(Exception):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, data: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    os.replace(temporary, path)


def versioned(path: Path, index: int) -> Path:
    return path if index == 1 else path.with_name(f"{path.stem}-v{index}{path.suffix}")


def reserve_directory(path: Path) -> Path:
    path = path.expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    for index in range(1, 10000):
        candidate = versioned(path, index)
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue
    raise CanvasError(f"Too many existing versions of {path}")


def save_image(image, path: Path, **kwargs) -> Path:
    """Reserve atomically, so concurrent jobs never overwrite each other."""
    path = path.expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    formats = {".png": "PNG", ".webp": "WEBP", ".jpg": "JPEG", ".jpeg": "JPEG", ".ico": "ICO", ".gif": "GIF"}
    if path.suffix.lower() not in formats:
        raise CanvasError("Output must be PNG, WebP, JPEG, ICO, or GIF.")
    for index in range(1, 10000):
        candidate = versioned(path, index)
        try:
            stream = candidate.open("xb")
        except FileExistsError:
            continue
        try:
            with stream:
                image.save(stream, format=formats[path.suffix.lower()], **kwargs)
            return candidate
        except BaseException:
            candidate.unlink(missing_ok=True)
            raise
    raise CanvasError(f"Too many existing versions of {path}")
