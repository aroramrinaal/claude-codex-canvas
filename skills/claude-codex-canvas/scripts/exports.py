"""Exact-size stills and animation exports. Never overwrites; never distorts silently."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from common import CanvasError, save_image, sha256
from images import ANCHORS, LOSSLESS_WEBP, color_value, flatten, inspect_image, load_image, size_value


def fit(image: Image.Image, size: tuple, mode: str, anchor: tuple, background: tuple, resample) -> Image.Image:
    if mode == "crop":
        return ImageOps.fit(image, size, method=resample, centering=anchor)
    if mode == "stretch":
        return image.resize(size, resample)
    fitted = ImageOps.contain(image, size, method=resample)
    output = Image.new("RGBA", size, background)
    output.alpha_composite(fitted, (round((size[0] - fitted.width) * anchor[0]),
                                    round((size[1] - fitted.height) * anchor[1])))
    return output


def still_format(output: Image.Image, suffix: str, size: tuple, background: tuple, explicit: bool):
    if suffix in (".jpg", ".jpeg"):
        if output.getchannel("A").getextrema()[0] < 255 and (not explicit or background[3] != 255):
            raise CanvasError("JPEG loses transparency. Supply an opaque --background or export PNG/WebP.")
        return flatten(output, background), {"quality": 95, "subsampling": 0}
    if suffix == ".webp":
        return output, LOSSLESS_WEBP
    if suffix == ".ico":
        if size[0] != size[1] or size[0] > 256:
            raise CanvasError("ICO output must be square and no larger than 256x256.")
        return output, {"sizes": [size]}
    if suffix != ".png":
        raise CanvasError("Finish supports PNG, WebP, JPEG, or ICO.")
    return output, {}


def finish(args) -> dict:
    source = Path(args.input).expanduser().resolve()
    size = size_value(args.size)
    resample = Image.Resampling.NEAREST if args.pixel_art else Image.Resampling.LANCZOS
    background = color_value(args.background) if args.background else (0, 0, 0, 0)
    output = fit(load_image(source), size, args.fit, ANCHORS[args.anchor], background, resample)
    output, kwargs = still_format(output, Path(args.output).suffix.lower(), size, background, bool(args.background))
    path = save_image(output, Path(args.output), **kwargs)
    return {"status": "exported", "source": str(source), "fit": args.fit, "anchor": args.anchor,
            "pixel_art": args.pixel_art, "image": inspect_image(path)}


def animation_format(frames: list, suffix: str, background: str | None):
    if suffix == ".gif":
        transparent = any(frame.getchannel("A").getextrema()[0] < 255 for frame in frames)
        if transparent and not background:
            raise CanvasError("GIF cannot retain soft alpha. Choose an opaque --background, or export WebP/APNG.")
        color = color_value(background or "#ffffff")
        if color[3] != 255:
            raise CanvasError("GIF background must be opaque.")
        return [flatten(frame, color) for frame in frames], {"disposal": 2}
    if suffix == ".webp":
        return frames, LOSSLESS_WEBP
    if suffix == ".png":
        return frames, {"disposal": 0, "blend": 0}
    raise CanvasError("Animation output must be .webp, .png (APNG), or .gif.")


def animate(args) -> dict:
    if not 2 <= len(args.frames) <= 256 or not 20 <= args.duration <= 10000:
        raise CanvasError("Animation needs 2–256 frames and a duration of 20–10,000ms per frame.")
    frames = [load_image(Path(p).expanduser()) for p in args.frames]
    if len({frame.size for frame in frames}) != 1:
        raise CanvasError("Normalize frames to the same dimensions before animation export.")
    if frames[0].width * frames[0].height * len(frames) > 40_000_000:
        raise CanvasError("Animation exceeds 40 million total frame pixels.")
    frames, kwargs = animation_format(frames, Path(args.output).suffix.lower(), args.background)
    path = save_image(frames[0], Path(args.output), save_all=True, append_images=frames[1:],
                      duration=args.duration, loop=0, **kwargs)
    with Image.open(path) as saved:
        actual_count = getattr(saved, "n_frames", 1)
    return {"status": "exported", "path": str(path), "width": frames[0].width,
            "height": frames[0].height, "input_frames": len(frames), "saved_frames": actual_count,
            "duration_ms": args.duration, "sha256": sha256(path)}
