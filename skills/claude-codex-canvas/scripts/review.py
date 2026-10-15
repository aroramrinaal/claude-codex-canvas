"""Labeled contact sheets for reviewing sets and sprite frames together."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from common import CanvasError, save_image
from images import checkerboard, load_image

LABEL_HEIGHT = 28


def make_contact(images: list[Image.Image], labels: list[str], columns: int, cell: int = 192) -> Image.Image:
    if not images or not 1 <= columns <= 32 or not 16 <= cell <= 1024:
        raise CanvasError("Contact sheet needs images, 1–32 columns, and 16–1024px cells.")
    columns = min(columns, len(images))
    rows = math.ceil(len(images) / columns)
    if columns * cell * rows * (cell + LABEL_HEIGHT) > 40_000_000:
        raise CanvasError("Contact sheet exceeds 40 megapixels.")
    sheet = Image.new("RGBA", (columns * cell, rows * (cell + LABEL_HEIGHT)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (image, label) in enumerate(zip(images, labels)):
        x, y = (i % columns) * cell, (i // columns) * (cell + LABEL_HEIGHT)
        tile = checkerboard((cell, cell))
        thumb = ImageOps.contain(image, (cell - 12, cell - 12), Image.Resampling.NEAREST)
        tile.alpha_composite(thumb, ((cell - thumb.width) // 2, (cell - thumb.height) // 2))
        sheet.alpha_composite(tile, (x, y))
        # ASCII-safe labels also work with Pillow's bundled default font.
        label = label.encode("ascii", "replace").decode()[:26]
        draw.text((x + 6, y + cell + 6), label, fill="#222222")
    return sheet


def contact_sheet(args) -> dict:
    paths = [Path(p).expanduser().resolve() for p in args.inputs]
    image = make_contact([load_image(p) for p in paths], [p.name for p in paths], args.columns, args.cell)
    output = save_image(image, Path(args.output))
    return {"status": "preview", "path": str(output), "inputs": [str(p) for p in paths]}
