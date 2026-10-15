"""Explicit chroma-key cleanup for intentionally flat backgrounds."""
from __future__ import annotations

from collections import deque
from pathlib import Path

from common import CanvasError, save_image
from images import LOSSLESS_WEBP, color_value, inspect_image, load_image


def border(width: int, height: int) -> deque:
    return deque([(x, 0) for x in range(width)] + [(x, height - 1) for x in range(width)]
                 + [(0, y) for y in range(height)] + [(width - 1, y) for y in range(height)])


def alpha_key(args) -> dict:
    """Remove only matching background connected to an edge; preserve enclosed colors."""
    if not 0 <= args.tolerance <= 255:
        raise CanvasError("Tolerance must be 0–255.")
    suffix = Path(args.output).suffix.lower()
    if suffix not in (".png", ".webp"):
        raise CanvasError("Alpha output must be PNG or WebP.")
    image = load_image(Path(args.input).expanduser())
    key = color_value(args.chroma)[:3]
    pixels = image.load()
    width, height = image.size
    seen = bytearray(width * height)
    queue, removed = border(width, height), 0
    while queue:
        x, y = queue.popleft()
        if seen[y * width + x]:
            continue
        seen[y * width + x] = 1
        pixel = pixels[x, y]
        if pixel[3] and max(abs(pixel[i] - key[i]) for i in range(3)) > args.tolerance:
            continue
        removed += int(pixel[3] > 0)
        pixels[x, y] = (pixel[0], pixel[1], pixel[2], 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height and not seen[ny * width + nx]:
                queue.append((nx, ny))
    if not image.getchannel("A").getbbox():
        raise CanvasError("Chroma key would erase the entire image; no output written.")
    output = save_image(image, Path(args.output), **(LOSSLESS_WEBP if suffix == ".webp" else {}))
    return {"status": "processed", "removed_pixels": removed, "image": inspect_image(output)}
