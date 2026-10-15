"""Shared timing, playback and GIF palette handling for exports and sprite previews."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from common import CanvasError, save_image


def timing_arguments(parser) -> None:
    timing = parser.add_mutually_exclusive_group()
    timing.add_argument("--duration", type=int, default=120, help="Milliseconds per frame (default: 120)")
    timing.add_argument("--durations", help="Comma-separated milliseconds, one value per input frame")
    parser.add_argument("--play-once", action="store_true", help="Play once instead of looping forever")


def frame_durations(args, count: int) -> list[int]:
    try:
        values = ([int(value.strip()) for value in args.durations.split(",")]
                  if args.durations is not None else [args.duration] * count)
    except ValueError as exc:
        raise CanvasError("--durations must contain comma-separated integer milliseconds.") from exc
    if len(values) != count or any(not 20 <= value <= 10000 for value in values):
        raise CanvasError("Supply exactly one duration per frame, each 20–10,000ms.")
    return values


def gif_frames(frames: list[Image.Image]) -> list[Image.Image]:
    """Train one bounded palette across the sequence to reduce frame-to-frame color flicker."""
    samples = Image.new("RGB", (128, 128 * len(frames)))
    for index, frame in enumerate(frames):
        # Sample all of the frame without inventing blended colors at pixel-art edges.
        samples.paste(frame.convert("RGB").resize((128, 128), Image.Resampling.NEAREST), (0, index * 128))
    palette = samples.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    return [frame.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]


def save_animation(frames: list[Image.Image], path: Path, durations: list[int], play_once: bool, **kwargs) -> tuple[Path, list[int]]:
    suffix = path.suffix.lower()
    encoded = durations
    if suffix == ".gif":
        # GIF stores centiseconds. Round explicitly rather than silently truncating.
        encoded = [max(20, ((value + 5) // 10) * 10) for value in durations]
        frames = gif_frames(frames)
        kwargs.update(disposal=2, optimize=False)
        # Omitting the loop extension means one play. loop=1 would repeat a GIF.
        if not play_once:
            kwargs["loop"] = 0
    else:
        # APNG and WebP count total plays; 0 means forever.
        kwargs["loop"] = 1 if play_once else 0
    saved = save_image(frames[0], path, save_all=True, append_images=frames[1:], duration=encoded, **kwargs)
    return saved, encoded
