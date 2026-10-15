import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from helpers import WorkspaceTest

import common


class AnimationTests(WorkspaceTest):
    def frames(self):
        paths = []
        for index in range(3):
            image = Image.new("RGBA", (32, 32))
            draw = ImageDraw.Draw(image)
            draw.rectangle((2 + index * 4, 4, 6 + index * 4, 8), fill="#e63b28")
            draw.rectangle((20, 20, 28, 28), fill="#4b8497")
            path = self.root / f"{index}.png"
            image.save(path)
            paths.append(str(path))
        return paths

    def test_individual_durations_and_one_shot_survive_encoding(self):
        paths = self.frames()
        for extension in ("png", "webp", "gif"):
            with self.subTest(extension=extension):
                result = self.command("animate", "--frames", *paths, "--durations", "85,120,235", "--play-once",
                                      "--output", str(self.root / f"out.{extension}"), "--background", "#ffffff")
                expected = [90, 120, 240] if extension == "gif" else [85, 120, 235]
                self.assertEqual(result["encoded_durations_ms"], expected)
                self.assertEqual(result["total_duration_ms"], sum(expected))
                with Image.open(result["path"]) as saved:
                    self.assertEqual(saved.n_frames, 3)
                    self.assertEqual(saved.info.get("loop"), None if extension == "gif" else 1)
                    actual = []
                    for index in range(saved.n_frames):
                        saved.seek(index)
                        saved.load()
                        actual.append(saved.info["duration"])
                    self.assertEqual(actual, expected)

    def test_default_is_infinite_loop_in_each_format(self):
        paths = self.frames()
        for extension in ("png", "webp", "gif"):
            result = self.command("animate", "--frames", *paths, "--output", str(self.root / f"out.{extension}"),
                                  "--background", "#ffffff")
            with Image.open(result["path"]) as saved:
                self.assertEqual(saved.info["loop"], 0)
            self.assertEqual(result["duration_ms"], 120)

    def test_invalid_timing_does_not_create_outputs(self):
        paths = self.frames()
        for durations in ("", "80,120", "80,no,120", "80,,120", "0,120,120", "120,120,10001"):
            with self.subTest(durations=durations), self.assertRaises(common.CanvasError):
                self.command("animate", "--frames", *paths, "--durations", durations,
                             "--output", str(self.root / "invalid.png"))
        self.assertFalse((self.root / "invalid.png").exists())

    def test_gif_keeps_shared_colors_stable_across_frames(self):
        result = self.command("animate", "--frames", *self.frames(), "--output", str(self.root / "out.gif"),
                              "--background", "#ffffff")
        with Image.open(result["path"]) as saved:
            colors = []
            for index in range(saved.n_frames):
                saved.seek(index)
                colors.append(saved.convert("RGB").getpixel((24, 24)))
            self.assertEqual(colors, [(75, 132, 151)] * 3)

    def test_identical_adjacent_frames_preserve_total_hold(self):
        paths = self.frames()
        result = self.command("animate", "--frames", paths[0], paths[0], paths[1], "--durations", "80,120,240",
                              "--output", str(self.root / "holds.gif"), "--background", "#ffffff")
        with Image.open(result["path"]) as saved:
            total = 0
            for index in range(saved.n_frames):
                saved.seek(index)
                total += saved.info["duration"]
            self.assertEqual(total, 440)
        self.assertTrue(Path(result["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
