"""Sprite guides and strip normalization into frames, atlas, manifest and previews.

Workflow adapted from OpenAI Game Studio (MIT); see ../NOTICE and
../licenses/game-studio-MIT.txt. Canvas adds validation, padding, source anchors,
versioned exports, manifests, and animation previews.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from animation import frame_durations, save_animation
from common import CanvasError, reserve_directory, save_image, sha256, write_json
from images import checkerboard, load_image, size_value
from review import make_contact


def sprite_guide(args) -> dict:
    if not 2 <= args.frames <= 32 or not 32 <= args.slot_size <= 512:
        raise CanvasError("Use 2–32 frames and a slot size of 32–512.")
    seed = load_image(Path(args.seed).expanduser())
    if not seed.getchannel("A").getbbox():
        raise CanvasError("The guide seed is empty; use an accepted visible character frame.")
    canvas = Image.new("RGBA", (args.frames * args.slot_size, args.slot_size))
    margin = max(8, round(args.slot_size * .12)) if args.show_guides else 8
    thumb = ImageOps.contain(seed, (args.slot_size - 2 * margin, args.slot_size - 2 * margin), Image.Resampling.NEAREST)
    canvas.alpha_composite(thumb, ((args.slot_size - thumb.width) // 2, args.slot_size - margin - thumb.height))
    if args.show_guides:
        draw = ImageDraw.Draw(canvas)
        for index in range(args.frames):
            left = index * args.slot_size
            draw.rectangle((left, 0, left + args.slot_size - 1, args.slot_size - 1), outline="#687d9e")
            draw.rectangle((left + margin, margin, left + args.slot_size - margin - 1, args.slot_size - margin - 1), outline="#b6c3d5")
    path = save_image(canvas, Path(args.output))
    return {"status": "layout_reference", "path": str(path), "frames": args.frames,
            "instruction": "First slot is identity reference; fill every equal slot with one pose. Do not copy empty slots."}


def check_args(args) -> tuple[int, int]:
    if not 2 <= args.frames <= 32:
        raise CanvasError("Use 2–32 frames per strip.")
    size = size_value(args.frame_size)
    if max(size) > 1024 or not 0 <= args.padding < min(size) / 2:
        raise CanvasError("Sprite cells must be at most 1024px; padding must leave content space.")
    if not 0 <= args.alpha_threshold < 255:
        raise CanvasError("Alpha threshold must be 0–254.")
    return size


def slice_strip(strip: Image.Image, count: int, threshold: int) -> tuple[list, list]:
    if strip.width < count:
        raise CanvasError("Strip is narrower than its frame count.")
    slots, boxes = [], []
    for i in range(count):
        left, right = round(i * strip.width / count), round((i + 1) * strip.width / count)
        slot = strip.crop((left, 0, right, strip.height))
        bbox = slot.getchannel("A").point(lambda v: 255 if v > threshold else 0).getbbox()
        if not bbox:
            raise CanvasError(f"Frame {i + 1} is empty. Regenerate the strip or correct the frame count.")
        if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == slot.width or bbox[3] == slot.height:
            raise CanvasError(f"Frame {i + 1} touches a slot edge or has opaque background. Review clipping/transparency before normalization.")
        slots.append(slot)
        boxes.append(bbox)
    return slots, boxes


def normalize(slots: list, boxes: list, size: tuple, args, seed: Image.Image | None = None) -> tuple[list, float]:
    """One shared scale for every frame, so the character never changes size mid-loop."""
    if args.anchor == "source":
        # Preserve displacement (jump height etc.) relative to the raw slot.
        max_width, max_height = max(s.width for s in slots), slots[0].height
    else:
        max_width = max(b[2] - b[0] for b in boxes)
        max_height = max(b[3] - b[1] for b in boxes)
    scale = min((size[0] - 2 * args.padding) / max_width, (size[1] - 2 * args.padding) / max_height)
    seed_box = seed.getchannel("A").getbbox() if seed is not None else None
    if seed_box:
        # Match the generated first pose to the shipped seed, instead of enlarging
        # every other pose to fill the cell and introducing a scale pop at frame 1.
        first = boxes[0]
        scale = min((seed_box[2] - seed_box[0]) / (first[2] - first[0]),
                    (seed_box[3] - seed_box[1]) / (first[3] - first[1]))
    resample = Image.Resampling.LANCZOS if args.smooth else Image.Resampling.NEAREST
    frames = []
    for slot, bbox in zip(slots, boxes):
        # With a locked seed, preserve source offsets by positioning the crop. Do not
        # upscale a potentially enormous transparent raw slot just to crop it again.
        content = slot if args.anchor == "source" and not seed_box else slot.crop(bbox)
        width, height = max(1, round(content.width * scale)), max(1, round(content.height * scale))
        x = (size[0] - width) // 2
        y = size[1] - args.padding - height if args.anchor == "bottom" else (size[1] - height) // 2
        if seed_box:
            center_x = (seed_box[0] + seed_box[2]) / 2
            if args.anchor == "source":
                x = round(center_x + (bbox[0] - (boxes[0][0] + boxes[0][2]) / 2) * scale)
                y = round(seed_box[3] + (bbox[1] - boxes[0][3]) * scale)
            else:
                x = round(center_x - width / 2)
                y = (seed_box[3] - height if args.anchor == "bottom"
                     else round((seed_box[1] + seed_box[3] - height) / 2))
            if (x < args.padding or y < args.padding
                    or x + width > size[0] - args.padding or y + height > size[1] - args.padding):
                raise CanvasError("Poses do not fit at the locked seed's scale and position. Use a seed with more room for motion or revise the strip; do not shrink frames independently.")
        scaled = content.resize((width, height), resample)
        frame = Image.new("RGBA", size)
        frame.alpha_composite(scaled, (x, y))
        frames.append(frame)
    return frames, scale


def load_seed(seed_path: str, size: tuple) -> Image.Image:
    seed = load_image(Path(seed_path).expanduser())
    if seed.size != size or not seed.getchannel("A").getbbox():
        raise CanvasError("--lock-first must be a nonempty approved frame already at the final cell size.")
    return seed


def write_outputs(frames: list, size: tuple, output: Path, durations: list[int], play_once: bool) -> list[dict]:
    frame_dir = output / "frames"
    frame_dir.mkdir()
    atlas = Image.new("RGBA", (size[0] * len(frames), size[1]))
    records = []
    for i, frame in enumerate(frames):
        path = save_image(frame, frame_dir / f"{i + 1:02d}.png")
        atlas.alpha_composite(frame, (i * size[0], 0))
        records.append({"file": str(path.relative_to(output)), "x": i * size[0], "y": 0,
                        "width": size[0], "height": size[1], "duration_ms": durations[i]})
    save_image(atlas, output / "atlas.png")
    labels = [str(i + 1) for i in range(len(frames))]
    save_image(make_contact(frames, labels, min(8, len(frames))), output / "contact-sheet.png")
    # Flatten only the review GIF onto a checkerboard; PNG frames retain alpha.
    preview = []
    for frame in frames:
        tile = checkerboard(size)
        tile.alpha_composite(frame)
        preview.append(tile.convert("RGB"))
    save_animation(preview, output / "preview.gif", durations, play_once)
    return records


def sprites(args) -> dict:
    size = check_args(args)
    durations = frame_durations(args, args.frames)
    source = Path(args.input).expanduser().resolve()
    slots, boxes = slice_strip(load_image(source), args.frames, args.alpha_threshold)
    if len({slot.tobytes() for slot in slots}) == 1:
        raise CanvasError("Every source pose is identical; this strip contains no animation.")
    seed = load_seed(args.lock_first, size) if args.lock_first else None
    frames, scale = normalize(slots, boxes, size, args, seed)
    if len({frame.tobytes() for frame in frames}) == 1:
        raise CanvasError("Every normalized pose is identical; choose source anchoring if displacement was intended, or repair the strip.")
    if seed is not None:
        frames[0] = seed
    if len({frame.tobytes() for frame in frames}) == 1:
        raise CanvasError("Every frame is identical; this strip contains no animation.")
    output = reserve_directory(Path(args.output_dir))
    records = write_outputs(frames, size, output, durations, args.play_once)
    record = {"status": "normalized", "source": str(source), "source_sha256": sha256(source),
              "output_dir": str(output), "atlas": "atlas.png", "frame_size": list(size),
              "frame_count": len(frames), "scale": scale, "anchor": args.anchor,
              "durations_ms": durations, "play_once": args.play_once,
              "source_boxes": boxes, "frames": records, "warnings": [],
              "review": "required: identity, motion, frame count, baseline, loop seam"}
    write_json(output / "manifest.json", record)
    return record
