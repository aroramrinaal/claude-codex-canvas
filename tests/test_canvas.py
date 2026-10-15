import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/claude-codex-canvas/scripts"
sys.path.insert(0, str(SCRIPTS))
import common
import imaging
import runner
import canvas


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="canvas-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def image(self, name="input.png", size=(100, 60), color="red"):
        path = self.root / name
        Image.new("RGBA", size, color).save(path)
        return path

    def command(self, *args):
        parsed = canvas.parser().parse_args(list(args))
        return parsed.run(parsed)


class RunnerTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.fake = self.root / "fake codex"
        self.fake.write_text(f"#!{sys.executable}\n" + (ROOT / "tests/fixtures/fake_codex.py").read_text())
        self.fake.chmod(0o755)
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text('A lemon. Keep "quoted text"; $HOME `literal` $(also literal)\nSecond line.')
        self.home = self.root / "codex-data"
        self.env = patch.dict(os.environ, {"CODEX_HOME": str(self.home), "FAKE_CODEX_MODE": "success",
                                           "OPENAI_API_KEY": "not-a-real-key", "CODEX_API_KEY": "not-a-real-key"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def render(self, *extra):
        with contextlib.redirect_stderr(io.StringIO()):
            return self.command("render", "--codex", str(self.fake), "--prompt-file", str(self.prompt),
                                "--jobs-dir", str(self.root / "jobs"), *extra)

    def test_doctor_reports_capabilities_without_rendering(self):
        result = runner.preflight(str(self.fake))
        self.assertEqual(result["auth"], "ChatGPT")
        self.assertFalse(result["generation_tested"])
        self.assertFalse(self.home.exists())

    def test_discovery_skips_old_executable(self):
        stale = self.root / "old-codex"
        stale.write_text('#!/bin/sh\nprintf "old CLI\\n"\n')
        stale.chmod(0o755)
        with patch.object(runner, "candidates", return_value=[str(stale), str(self.fake)]):
            result = runner.preflight()
        self.assertEqual(result["executable"], str(self.fake))
        self.assertEqual(len(result["rejected_candidates"]), 1)

    def test_explicit_executable_does_not_fall_back(self):
        with self.assertRaises(common.CanvasError):
            runner.preflight(str(self.root / "absent"))

    def test_disabled_and_api_auth_rejected(self):
        for mode in ("disabled", "api-auth"):
            with self.subTest(mode=mode), patch.dict(os.environ, {"FAKE_CODEX_MODE": mode}):
                with self.assertRaises(common.CanvasError):
                    runner.preflight(str(self.fake))

    def test_collects_without_image_event_and_preserves_prompt(self):
        result = self.render("--transparent")
        self.assertEqual(result["status"], "generated")
        self.assertEqual(result["caller_model"], "gpt-6-luna")
        self.assertEqual(result["effort"], "low")
        self.assertIsNone(result["image_model"])
        self.assertEqual(result["prompt_fidelity"], "not_verified")
        self.assertEqual(result["usage"]["input_tokens"], 100)
        self.assertEqual(Path(result["prompt_path"]).read_text(), self.prompt.read_text())
        payload = json.loads((Path(result["job_dir"]) / "handoff.txt").read_text().split("Image tool arguments:\n")[1])
        self.assertEqual(payload["prompt"], self.prompt.read_text())
        self.assertEqual(common.sha256(Path(result["original_path"])), common.sha256(Path(result["source_path"])))
        self.assertEqual(runner.collect(Path(result["job_dir"]))["thread_id"], result["thread_id"])

    def test_reference_snapshots_and_model_override(self):
        ref = self.image("ref with spaces.png")
        result = self.render("--reference", f"identity={ref}", "--model", "gpt-6-astra", "--effort", "medium", "--debug")
        staged = Path(result["references"][0]["path"])
        self.assertNotEqual(staged, ref)
        self.assertEqual(staged.read_bytes(), ref.read_bytes())
        self.assertEqual(result["caller_model"], "gpt-6-astra")
        self.assertTrue(result["debug"])
        ref.unlink()
        self.assertTrue(staged.exists())

    def test_failed_runs_cannot_claim_existing_image(self):
        other = self.home / "generated_images" / "unrelated"
        other.mkdir(parents=True)
        Image.new("RGB", (40, 40)).save(other / "old.png")
        for mode in ("missing", "multiple", "stale", "corrupt", "symlink", "failure", "exit-failure", "partial", "bad-json", "blank", "opaque"):
            with self.subTest(mode=mode), patch.dict(os.environ, {"FAKE_CODEX_MODE": mode}):
                with self.assertRaises(common.CanvasError):
                    self.render("--transparent")
        records = [json.loads(p.read_text()) for p in (self.root / "jobs").glob("*/job.json")]
        self.assertTrue(all(r["status"] == "failed" for r in records))
        self.assertFalse(list((self.root / "jobs").glob("*/original.png")))

    def test_timeout_stops_owned_process(self):
        with patch.dict(os.environ, {"FAKE_CODEX_MODE": "timeout"}):
            start = time.monotonic()
            with self.assertRaisesRegex(common.CanvasError, "timed out"):
                self.render("--timeout", "0.2")
            self.assertLess(time.monotonic() - start, 5)

    def test_input_errors_happen_before_render(self):
        for extra in (("--reference", "missing-role"), ("--timeout", "0")):
            with self.subTest(extra=extra), self.assertRaises(common.CanvasError):
                self.render(*extra)
        self.assertFalse((self.root / "jobs").exists())

    def test_thread_path_traversal_rejected(self):
        log = self.root / "events.jsonl"
        log.write_text('{"type":"thread.started","thread_id":"../../other"}\n{"type":"turn.completed"}\n')
        with self.assertRaises(common.CanvasError):
            runner.parse_events(log)

    def test_tampered_original_rejected(self):
        result = self.render()
        Path(result["original_path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(common.CanvasError, "changed"):
            runner.collect(Path(result["job_dir"]))


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
                imaging.size_value(size)
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


class PackageTests(WorkspaceTest):
    def test_standalone_install_is_idempotent_and_refuses_replacement(self):
        target = self.root / "skills"
        command = [sys.executable, str(ROOT / "scripts/install.py"), "--skills-dir", str(target)]
        for _ in range(2):
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        linked = target / "claude-codex-canvas"
        linked.unlink()
        linked.mkdir()
        result = subprocess.run(command, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(linked.is_dir())

    def test_plugin_paths_resolve(self):
        manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        self.assertTrue((ROOT / manifest["skills"]).is_dir())
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.assertTrue((ROOT / marketplace["plugins"][0]["source"] / ".claude-plugin/plugin.json").is_file())

    def test_cli_error_is_json_and_nonzero(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "canvas.py"), "inspect", str(self.root / "absent.png")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "error")


if __name__ == "__main__":
    unittest.main()
