import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

from helpers import WorkspaceTest

import common
import images


class ExportTests(WorkspaceTest):
    def finish(self, source, output, *extra):
        return self.command("finish", "--input", str(source), "--output", str(output), *extra)

    def test_crop_pad_and_stretch_have_exact_dimensions(self):
        for fit in ("crop", "pad", "stretch"):
            with self.subTest(fit=fit):
                result = self.finish(self.image(), self.root / f"{fit}.png", "--size", "80x80", "--fit", fit)
                self.assertEqual((result["image"]["width"], result["image"]["height"]), (80, 80))
                self.assertEqual(result["image"]["has_transparent_pixels"], fit == "pad")

    def test_lossless_webp_and_ico(self):
        source = self.image()
        for suffix, size in (("webp", "80x80"), ("ico", "32x32")):
            result = self.finish(source, self.root / f"asset.{suffix}", "--size", size, "--fit", "pad")
            self.assertTrue(Path(result["image"]["path"]).exists())

    def test_jpeg_requires_deliberate_flattening(self):
        source = self.image(color=(255, 0, 0, 100))
        with self.assertRaises(common.CanvasError):
            self.finish(source, self.root / "out.jpg", "--size", "50x50", "--fit", "pad")
        result = self.finish(source, self.root / "out.jpg", "--size", "50x50", "--fit", "pad", "--background", "#ffffff")
        self.assertFalse(result["image"]["has_transparent_pixels"])

    def test_exports_are_collision_safe_under_concurrency(self):
        image = Image.new("RGB", (20, 20), "red")
        with ThreadPoolExecutor(max_workers=4) as pool:
            outputs = list(pool.map(lambda _: common.save_image(image, self.root / "same.png"), range(8)))
        self.assertEqual(len(set(outputs)), 8)
        self.assertTrue(all(path.is_file() for path in outputs))

    def test_original_is_not_overwritten(self):
        source = self.image()
        before = source.read_bytes()
        result = self.finish(source, source, "--size", "10x10", "--fit", "crop")
        self.assertNotEqual(result["image"]["path"], str(source))
        self.assertEqual(source.read_bytes(), before)

    def test_pixel_art_does_not_invent_colors(self):
        source = self.image(size=(2, 2))
        image = Image.open(source).convert("RGBA")
        image.putpixel((0, 0), (0, 0, 255, 255))
        image.save(source)
        result = self.finish(source, self.root / "large.png", "--size", "30x30", "--fit", "stretch", "--pixel-art")
        output = Image.open(result["image"]["path"])
        self.assertEqual(len(output.getcolors()), 2)

    def test_invalid_sizes_and_formats_rejected(self):
        for size in ("0x2", "-1x20", "huge", "20000x20000"):
            with self.subTest(size=size), self.assertRaises(common.CanvasError):
                images.size_value(size)
        with self.assertRaises(common.CanvasError):
            self.finish(self.image(), self.root / "bad.ico", "--size", "1024x1024", "--fit", "pad")

    def test_chroma_only_removes_border_connected_color(self):
        source = self.image(size=(20, 20), color="#00ff00")
        image = Image.open(source).convert("RGBA")
        draw = ImageDraw.Draw(image)
        draw.rectangle((5, 5, 14, 14), fill="red")
        draw.rectangle((8, 8, 10, 10), fill="#00ff00")
        image.save(source)
        result = self.command("alpha", "--input", str(source), "--output", str(self.root / "cutout.png"), "--chroma", "#00ff00")
        output = Image.open(result["image"]["path"])
        self.assertEqual(output.getpixel((0, 0))[3], 0)
        self.assertEqual(output.getpixel((9, 9))[3], 255)


if __name__ == "__main__":
    unittest.main()
