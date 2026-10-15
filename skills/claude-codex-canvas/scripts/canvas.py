#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=11.3,<13"]
# ///
"""Claude Codex Canvas command line. JSON results on stdout; progress on stderr."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import PIL  # noqa: F401
except ImportError:
    raise SystemExit("Pillow is required. Use `uv run --script canvas.py …` or install Pillow>=11.3,<13 in your Python environment.")

from alpha import alpha_key
from collector import collect
from common import CanvasError, private_dir
from discovery import DEFAULT_EFFORT, DEFAULT_MODEL, preflight
from exports import animate, finish
from images import inspect_image
from review import contact_sheet
from runner import render
from sprites import sprite_guide, sprites


def workspace(args) -> dict:
    root = private_dir(Path(args.dir))
    return {"status": "ready", "workspace": str(root), "jobs_dir": str(root / "jobs"), "git_ignored": True}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Check CLI capabilities and ChatGPT login; no generation")
    doctor.add_argument("--codex", help="Explicit Codex executable (or CANVAS_CODEX)")
    doctor.set_defaults(run=lambda a: preflight(a.codex))
    init = commands.add_parser("init", help="Create a git-ignored workspace for briefs, prompts and jobs")
    init.add_argument("--dir", default=".canvas")
    init.set_defaults(run=workspace)
    draw = commands.add_parser("render", help="Generate one original through authenticated Codex")
    draw.add_argument("--prompt-file", required=True)
    draw.add_argument("--reference", action="append", default=[], metavar="ROLE=PATH")
    draw.add_argument("--transparent", action="store_true")
    draw.add_argument("--jobs-dir", default=".canvas/jobs")
    draw.add_argument("--codex")
    draw.add_argument("--model", default=os.environ.get("CANVAS_MODEL", DEFAULT_MODEL), help="Codex caller model, not image backend")
    draw.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default=os.environ.get("CANVAS_EFFORT", DEFAULT_EFFORT))
    draw.add_argument("--timeout", type=float, default=180, help="Seconds; keep the Bash tool timeout longer")
    draw.add_argument("--debug", action="store_true", help="Keep Codex session logs (omit --ephemeral)")
    draw.set_defaults(run=render)
    gather = commands.add_parser("collect", help="Re-check an existing completed job without generating")
    gather.add_argument("job")
    gather.set_defaults(run=lambda a: collect(Path(a.job)))
    inspect = commands.add_parser("inspect", help="Check dimensions, alpha, decoding, and checksum")
    inspect.add_argument("input")
    inspect.set_defaults(run=lambda a: inspect_image(Path(a.input)))
    export = commands.add_parser("finish", help="Export exact dimensions without overwriting")
    export.add_argument("--input", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--size", required=True, metavar="WIDTHxHEIGHT")
    export.add_argument("--fit", choices=["crop", "pad", "stretch"], required=True)
    export.add_argument("--anchor", choices=["center", "top", "bottom", "left", "right"], default="center")
    export.add_argument("--pixel-art", action="store_true")
    export.add_argument("--background", help="Explicit padding/JPEG background, e.g. #ffffff")
    export.set_defaults(run=finish)
    contact = commands.add_parser("contact-sheet", help="Build a labeled review sheet for a set")
    contact.add_argument("--inputs", nargs="+", required=True)
    contact.add_argument("--output", required=True)
    contact.add_argument("--columns", type=int, default=4)
    contact.add_argument("--cell", type=int, default=192)
    contact.set_defaults(run=contact_sheet)
    animation = commands.add_parser("animate", help="Export accepted frames as animated WebP, APNG, or flattened GIF")
    animation.add_argument("--frames", nargs="+", required=True, help="Frame paths in playback order")
    animation.add_argument("--output", required=True)
    animation.add_argument("--duration", type=int, default=120, help="Milliseconds per frame")
    animation.add_argument("--background", help="Opaque GIF background; WebP/APNG retain alpha")
    animation.set_defaults(run=animate)
    alpha = commands.add_parser("alpha", help="Explicit border-connected chroma-key cleanup")
    alpha.add_argument("--input", required=True)
    alpha.add_argument("--output", required=True)
    alpha.add_argument("--chroma", required=True)
    alpha.add_argument("--tolerance", type=int, default=24)
    alpha.set_defaults(run=alpha_key)
    guide = commands.add_parser("sprite-guide", help="Place approved seed in the first slot of a reference canvas")
    guide.add_argument("--seed", required=True)
    guide.add_argument("--frames", type=int, required=True)
    guide.add_argument("--slot-size", type=int, default=256)
    guide.add_argument("--output", required=True)
    guide.set_defaults(run=sprite_guide)
    sprite = commands.add_parser("sprites", help="Normalize a generated horizontal strip and make atlas/previews")
    sprite.add_argument("--input", required=True)
    sprite.add_argument("--frames", type=int, required=True)
    sprite.add_argument("--frame-size", default="64x64")
    sprite.add_argument("--output-dir", required=True)
    sprite.add_argument("--padding", type=int, default=2)
    sprite.add_argument("--anchor", choices=["bottom", "center", "source"], default="bottom")
    sprite.add_argument("--alpha-threshold", type=int, default=8)
    sprite.add_argument("--duration", type=int, default=120, help="Milliseconds per frame")
    sprite.add_argument("--smooth", action="store_true", help="Use Lanczos for non-pixel artwork")
    sprite.add_argument("--lock-first", help="Replace first frame with approved seed at exact final cell size")
    sprite.set_defaults(run=sprites)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        result = args.run(args)
    except (CanvasError, OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
