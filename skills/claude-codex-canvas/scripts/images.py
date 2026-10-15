"""Image decoding, inspection and argument parsing shared by every command."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageOps

from common import CanvasError, sha256

ANCHORS = {"center": (0.5, 0.5), "top": (0.5, 0), "bottom": (0.5, 1), "left": (0, 0.5), "right": (1, 0.5)}
LOSSLESS_WEBP = {"lossless": True, "exact": True}


def load_image(path: Path) -> Image.Image:
    try:
        with Image.open(path) as source:
            if getattr(source, "n_frames", 1) != 1:
                raise CanvasError("Use a still image as input, not an animation.")
            source.load()
            return ImageOps.exif_transpose(source).convert("RGBA")
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise CanvasError(f"Cannot decode image {path}: {exc}") from exc


def inspect_image(path: Path) -> dict:
    path = path.expanduser().resolve()
    image = load_image(path)
    with Image.open(path) as source:
        format_name = source.format
    histogram = image.getchannel("A").histogram()
    total = image.width * image.height
    return {"path": str(path), "format": format_name, "width": image.width, "height": image.height,
            "sha256": sha256(path), "nonempty": histogram[0] < total,
            "has_transparent_pixels": histogram[0] > 0,
            "transparent_fraction": round(histogram[0] / total, 6),
            "soft_alpha_fraction": round(sum(histogram[1:255]) / total, 6)}


def size_value(value: str) -> tuple[int, int]:
    try:
        width, height = (int(x) for x in value.lower().split("x"))
    except (ValueError, AttributeError) as exc:
        raise CanvasError("Size must be WIDTHxHEIGHT, e.g. 1200x630.") from exc
    if min(width, height) <= 0 or max(width, height) > 16384 or width * height > 40_000_000:
        raise CanvasError("Size must be positive, at most 16,384 per edge and 40 megapixels.")
    return width, height


def color_value(value: str) -> tuple:
    try:
        return ImageColor.getcolor(value, "RGBA")
    except ValueError as exc:
        raise CanvasError(f"Invalid color: {value}") from exc


def flatten(image: Image.Image, background: tuple) -> Image.Image:
    composite = Image.new("RGBA", image.size, background)
    composite.alpha_composite(image)
    return composite.convert("RGB")


def checkerboard(size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGBA", size, "#f1f1f1")
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], 12):
        for x in range(0, size[0], 12):
            if (x // 12 + y // 12) % 2:
                draw.rectangle((x, y, x + 11, y + 11), fill="#d6d6d6")
    return image
