import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from helpers import WorkspaceTest

import common


class SpriteTests(WorkspaceTest):
    def strip(self, mode="normal"):
        image = Image.new("RGBA", (128, 64))
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 24, 43, 55), fill="red")
        if mode != "empty":
            draw.rectangle((80, 16, 111, 55 if mode != "jump" else 40), fill="blue")
        if mode == "clipped":
            draw.rectangle((0, 0, 10, 63), fill="red")
        if mode == "identical":
            image.paste(image.crop((0, 0, 64, 64)), (64, 0))
        path = self.root / "strip.png"
        image.save(path)
        return path

    def normalize(self, source, *extra):
        return self.command("sprites", "--input", str(source), "--frames", "2", "--frame-size", "32x32",
                            "--output-dir", str(self.root / "walk"), *extra)

    def test_shared_scale_baseline_and_atlas(self):
        result = self.normalize(self.strip())
        output = Path(result["output_dir"])
        first, second = [Image.open(output / f["file"]).convert("RGBA") for f in result["frames"]]
        a, b = first.getbbox(), second.getbbox()
        self.assertEqual(a[3], b[3])
        self.assertLess(a[2] - a[0], b[2] - b[0])
        with Image.open(output / "atlas.png") as atlas:
            self.assertEqual(atlas.size, (64, 32))
        self.assertTrue((output / "contact-sheet.png").is_file())
        with Image.open(output / "preview.gif") as preview:
            self.assertEqual(preview.n_frames, 2)

    def test_source_anchor_retains_vertical_motion(self):
        result = self.normalize(self.strip("jump"), "--anchor", "source")
        frames = [Image.open(Path(result["output_dir"]) / f["file"]).convert("RGBA") for f in result["frames"]]
        self.assertGreater(frames[0].getbbox()[3], frames[1].getbbox()[3])

    def test_bad_strips_fail_before_export(self):
        for mode in ("empty", "clipped", "identical"):
            with self.subTest(mode=mode), self.assertRaises(common.CanvasError):
                self.normalize(self.strip(mode))
        self.assertFalse((self.root / "walk").exists())

    def test_repeated_exports_use_new_directories(self):
        source = self.strip()
        first = self.normalize(source)
        second = self.normalize(source)
        self.assertNotEqual(first["output_dir"], second["output_dir"])

    def test_lock_first_requires_final_dimensions(self):
        seed = self.image(size=(30, 30))
        with self.assertRaises(common.CanvasError):
            self.normalize(self.strip(), "--lock-first", str(seed))

    def test_guide_keeps_other_slots_transparent(self):
        seed = self.image(size=(20, 20))
        result = self.command("sprite-guide", "--seed", str(seed), "--frames", "4", "--slot-size", "64", "--output", str(self.root / "guide.png"))
        image = Image.open(result["path"]).convert("RGBA")
        self.assertEqual(image.size, (256, 64))
        self.assertIsNone(image.crop((64, 0, 256, 64)).getbbox())

    def test_final_animation_preserves_frames_and_alpha(self):
        result = self.normalize(self.strip())
        paths = [str(Path(result["output_dir"]) / frame["file"]) for frame in result["frames"]]
        for suffix in ("webp", "png"):
            with self.subTest(suffix=suffix):
                exported = self.command("animate", "--frames", *paths, "--output", str(self.root / f"walk.{suffix}"))
                with Image.open(exported["path"]) as animation:
                    self.assertEqual(animation.n_frames, 2)
                    animation.seek(1)
                    self.assertEqual(animation.convert("RGBA").getpixel((0, 0))[3], 0)
        with self.assertRaises(common.CanvasError):
            self.command("animate", "--frames", *paths, "--output", str(self.root / "walk.gif"))
        exported = self.command("animate", "--frames", *paths, "--output", str(self.root / "walk.gif"), "--background", "#ffffff")
        self.assertEqual(exported["saved_frames"], 2)

    def test_mismatched_animation_frames_rejected(self):
        a = self.image("a.png", size=(32, 32))
        b = self.image("b.png", size=(30, 30))
        with self.assertRaises(common.CanvasError):
            self.command("animate", "--frames", str(a), str(b), "--output", str(self.root / "bad.webp"))


if __name__ == "__main__":
    unittest.main()
