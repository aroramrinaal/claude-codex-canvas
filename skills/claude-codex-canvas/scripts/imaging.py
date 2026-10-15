"""Exact exports and sprite normalization, using Pillow only.

Sprite workflow adapted from OpenAI Game Studio (MIT); see ../NOTICE and
../licenses/game-studio-MIT.txt. Canvas adds validation, padding, source anchors,
versioned exports, manifests, and animation previews.
"""
from __future__ import annotations

import math
from collections import deque
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageOps

from common import CanvasError, reserve_directory, save_image, sha256, write_json


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


def finish(args) -> dict:
    source = Path(args.input).expanduser().resolve()
    image = load_image(source)
    size = size_value(args.size)
    resample = Image.Resampling.NEAREST if args.pixel_art else Image.Resampling.LANCZOS
    anchors = {"center": (0.5, 0.5), "top": (0.5, 0), "bottom": (0.5, 1), "left": (0, 0.5), "right": (1, 0.5)}
    anchor = anchors[args.anchor]
    background = color_value(args.background) if args.background else (0, 0, 0, 0)
    if args.fit == "crop":
        output = ImageOps.fit(image, size, method=resample, centering=anchor)
    elif args.fit == "pad":
        fitted = ImageOps.contain(image, size, method=resample)
        output = Image.new("RGBA", size, background)
        output.alpha_composite(fitted, (round((size[0] - fitted.width) * anchor[0]), round((size[1] - fitted.height) * anchor[1])))
    else:
        output = image.resize(size, resample)
    suffix = Path(args.output).suffix.lower()
    kwargs = {}
    if suffix in (".jpg", ".jpeg"):
        if output.getchannel("A").getextrema()[0] < 255 and (not args.background or background[3] != 255):
            raise CanvasError("JPEG loses transparency. Supply an opaque --background or export PNG/WebP.")
        flattened = Image.new("RGBA", size, background)
        flattened.alpha_composite(output)
        output = flattened.convert("RGB")
        kwargs = {"quality": 95, "subsampling": 0}
    elif suffix == ".webp":
        kwargs = {"lossless": True, "exact": True}
    elif suffix == ".ico":
        if size[0] != size[1] or size[0] > 256:
            raise CanvasError("ICO output must be square and no larger than 256x256.")
        kwargs = {"sizes": [size]}
    elif suffix != ".png":
        raise CanvasError("Finish supports PNG, WebP, JPEG, or ICO.")
    path = save_image(output, Path(args.output), **kwargs)
    return {"status": "exported", "source": str(source), "fit": args.fit, "anchor": args.anchor,
            "pixel_art": args.pixel_art, "image": inspect_image(path)}


def checkerboard(size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGBA", size, "#f1f1f1")
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], 12):
        for x in range(0, size[0], 12):
            if (x // 12 + y // 12) % 2:
                draw.rectangle((x, y, x + 11, y + 11), fill="#d6d6d6")
    return image


def make_contact(images: list[Image.Image], labels: list[str], columns: int, cell: int = 192) -> Image.Image:
    if not images or not 1 <= columns <= 32 or not 16 <= cell <= 1024:
        raise CanvasError("Contact sheet needs images, 1–32 columns, and 16–1024px cells.")
    columns = min(columns, len(images))
    rows = math.ceil(len(images) / columns)
    if columns * cell * rows * (cell + 28) > 40_000_000:
        raise CanvasError("Contact sheet exceeds 40 megapixels.")
    sheet = Image.new("RGBA", (columns * cell, rows * (cell + 28)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (image, label) in enumerate(zip(images, labels)):
        x, y = (i % columns) * cell, (i // columns) * (cell + 28)
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


def animate(args) -> dict:
    if not 2 <= len(args.frames) <= 256 or not 20 <= args.duration <= 10000:
        raise CanvasError("Animation needs 2–256 frames and a duration of 20–10,000ms per frame.")
    frames = [load_image(Path(p).expanduser()) for p in args.frames]
    if len({frame.size for frame in frames}) != 1:
        raise CanvasError("Normalize frames to the same dimensions before animation export.")
    if frames[0].width * frames[0].height * len(frames) > 40_000_000:
        raise CanvasError("Animation exceeds 40 million total frame pixels.")
    suffix = Path(args.output).suffix.lower()
    kwargs = {"save_all": True, "duration": args.duration, "loop": 0}
    if suffix == ".gif":
        transparent = any(frame.getchannel("A").getextrema()[0] < 255 for frame in frames)
        if transparent and not args.background:
            raise CanvasError("GIF cannot retain soft alpha. Choose an opaque --background, or export WebP/APNG.")
        background = color_value(args.background or "#ffffff")
        if background[3] != 255:
            raise CanvasError("GIF background must be opaque.")
        flattened = []
        for frame in frames:
            composite = Image.new("RGBA", frame.size, background)
            composite.alpha_composite(frame)
            flattened.append(composite.convert("RGB"))
        frames = flattened
        kwargs.update(disposal=2)
    elif suffix == ".webp":
        kwargs.update(lossless=True, exact=True)
    elif suffix == ".png":
        kwargs.update(disposal=0, blend=0)
    else:
        raise CanvasError("Animation output must be .webp, .png (APNG), or .gif.")
    kwargs["append_images"] = frames[1:]
    path = save_image(frames[0], Path(args.output), **kwargs)
    with Image.open(path) as saved:
        actual_count = getattr(saved, "n_frames", 1)
    return {"status": "exported", "path": str(path), "width": frames[0].width,
            "height": frames[0].height, "input_frames": len(frames), "saved_frames": actual_count,
            "duration_ms": args.duration, "sha256": sha256(path)}


def alpha_key(args) -> dict:
    """Remove only matching background connected to an edge; preserve enclosed colors."""
    if not 0 <= args.tolerance <= 255:
        raise CanvasError("Tolerance must be 0–255.")
    image = load_image(Path(args.input).expanduser())
    key = color_value(args.chroma)[:3]
    pixels = image.load()
    width, height = image.size
    seen = bytearray(width * height)
    queue = deque([(x, 0) for x in range(width)] + [(x, height - 1) for x in range(width)]
                  + [(0, y) for y in range(height)] + [(width - 1, y) for y in range(height)])
    removed = 0
    while queue:
        x, y = queue.popleft()
        offset = y * width + x
        if seen[offset]:
            continue
        seen[offset] = 1
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
    if Path(args.output).suffix.lower() not in (".png", ".webp"):
        raise CanvasError("Alpha output must be PNG or WebP.")
    output = save_image(image, Path(args.output), **({"lossless": True, "exact": True} if Path(args.output).suffix.lower() == ".webp" else {}))
    return {"status": "processed", "removed_pixels": removed, "image": inspect_image(output)}


def sprite_guide(args) -> dict:
    if not 2 <= args.frames <= 32 or not 32 <= args.slot_size <= 512:
        raise CanvasError("Use 2–32 frames and a slot size of 32–512.")
    seed = load_image(Path(args.seed).expanduser())
    canvas = Image.new("RGBA", (args.frames * args.slot_size, args.slot_size))
    thumb = ImageOps.contain(seed, (args.slot_size - 16, args.slot_size - 16), Image.Resampling.NEAREST)
    canvas.alpha_composite(thumb, ((args.slot_size - thumb.width) // 2, args.slot_size - 8 - thumb.height))
    path = save_image(canvas, Path(args.output))
    return {"status": "layout_reference", "path": str(path), "frames": args.frames,
            "instruction": "First slot is identity reference; fill every equal slot with one pose. Do not copy empty slots."}


def sprites(args) -> dict:
    if not 2 <= args.frames <= 32:
        raise CanvasError("Use 2–32 frames per strip.")
    size = size_value(args.frame_size)
    if max(size) > 1024 or not 0 <= args.padding < min(size) / 2:
        raise CanvasError("Sprite cells must be at most 1024px; padding must leave content space.")
    if not 0 <= args.alpha_threshold < 255 or not 20 <= args.duration <= 10000:
        raise CanvasError("Alpha threshold must be 0–254; frame duration must be 20–10,000ms.")
    source = Path(args.input).expanduser().resolve()
    strip = load_image(source)
    if strip.width < args.frames:
        raise CanvasError("Strip is narrower than its frame count.")
    slots, boxes = [], []
    for i in range(args.frames):
        left, right = round(i * strip.width / args.frames), round((i + 1) * strip.width / args.frames)
        slot = strip.crop((left, 0, right, strip.height))
        bbox = slot.getchannel("A").point(lambda v: 255 if v > args.alpha_threshold else 0).getbbox()
        if not bbox:
            raise CanvasError(f"Frame {i + 1} is empty. Regenerate the strip or correct the frame count.")
        if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == slot.width or bbox[3] == slot.height:
            raise CanvasError(f"Frame {i + 1} touches a slot edge or has opaque background. Review clipping/transparency before normalization.")
        slots.append(slot)
        boxes.append(bbox)
    if args.anchor == "source":
        # Preserve displacement (jump height etc.) relative to the raw slot.
        max_width, max_height = max(s.width for s in slots), strip.height
    else:
        max_width = max(b[2] - b[0] for b in boxes)
        max_height = max(b[3] - b[1] for b in boxes)
    scale = min((size[0] - 2 * args.padding) / max_width, (size[1] - 2 * args.padding) / max_height)
    resample = Image.Resampling.LANCZOS if args.smooth else Image.Resampling.NEAREST
    frames = []
    for slot, bbox in zip(slots, boxes):
        content = slot if args.anchor == "source" else slot.crop(bbox)
        dimensions = (max(1, round(content.width * scale)), max(1, round(content.height * scale)))
        scaled = content.resize(dimensions, resample)
        frame = Image.new("RGBA", size)
        x = (size[0] - scaled.width) // 2
        y = size[1] - args.padding - scaled.height if args.anchor == "bottom" else (size[1] - scaled.height) // 2
        frame.alpha_composite(scaled, (x, y))
        frames.append(frame)
    if args.lock_first:
        seed = load_image(Path(args.lock_first).expanduser())
        if seed.size != size or not seed.getchannel("A").getbbox():
            raise CanvasError("--lock-first must be a nonempty approved frame already at the final cell size.")
        frames[0] = seed
    warnings = []
    if len({frame.tobytes() for frame in frames}) == 1:
        raise CanvasError("Every frame is identical; this strip contains no animation.")
    output = reserve_directory(Path(args.output_dir))
    frame_dir = output / "frames"
    frame_dir.mkdir()
    atlas = Image.new("RGBA", (size[0] * len(frames), size[1]))
    records = []
    for i, frame in enumerate(frames):
        path = save_image(frame, frame_dir / f"{i + 1:02d}.png")
        atlas.alpha_composite(frame, (i * size[0], 0))
        records.append({"file": str(path.relative_to(output)), "x": i * size[0], "y": 0,
                        "width": size[0], "height": size[1], "duration_ms": args.duration})
    save_image(atlas, output / "atlas.png")
    save_image(make_contact(frames, [str(i + 1) for i in range(len(frames))], min(8, len(frames))), output / "contact-sheet.png")
    # Flatten only the review GIF onto a checkerboard; PNG frames retain alpha.
    preview = []
    for frame in frames:
        tile = checkerboard(size)
        tile.alpha_composite(frame)
        preview.append(tile.convert("RGB"))
    save_image(preview[0], output / "preview.gif", save_all=True, append_images=preview[1:],
               duration=args.duration, loop=0, disposal=2)
    record = {"status": "normalized", "source": str(source), "source_sha256": sha256(source),
              "output_dir": str(output), "atlas": "atlas.png", "frame_size": list(size),
              "frame_count": len(frames), "scale": scale, "anchor": args.anchor,
              "source_boxes": boxes, "frames": records, "warnings": warnings,
              "review": "required: identity, motion, frame count, baseline, loop seam"}
    write_json(output / "manifest.json", record)
    return record
