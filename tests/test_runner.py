import contextlib
import io
import json
import os
import signal
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from helpers import ROOT, WorkspaceTest

import collector
import common


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
        self.assertEqual(collector.collect(Path(result["job_dir"]))["thread_id"], result["thread_id"])

    def test_jobs_dir_is_git_ignored(self):
        self.render()
        self.assertEqual((self.root / "jobs/.gitignore").read_text().splitlines()[-1], "*")

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

    def test_sigterm_cancels_and_stops_codex(self):
        # What happens when Claude's Bash tool times out: Codex must not keep spending quota.
        pid_file = self.home / "fake.pid"
        def terminate():
            deadline = time.monotonic() + 10
            while not pid_file.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            os.kill(os.getpid(), signal.SIGTERM)
        threading.Thread(target=terminate, daemon=True).start()
        with patch.dict(os.environ, {"FAKE_CODEX_MODE": "timeout"}):
            with self.assertRaisesRegex(common.CanvasError, "Cancelled"):
                self.render()
        with self.assertRaises(ProcessLookupError):
            os.kill(int(pid_file.read_text()), 0)
        self.assertIs(signal.getsignal(signal.SIGTERM), signal.SIG_DFL)
        record = json.loads(next((self.root / "jobs").glob("*/job.json")).read_text())
        self.assertEqual(record["status"], "failed")

    def test_input_errors_happen_before_render(self):
        for extra in (("--reference", "missing-role"), ("--timeout", "0")):
            with self.subTest(extra=extra), self.assertRaises(common.CanvasError):
                self.render(*extra)
        self.assertFalse((self.root / "jobs").exists())

    def test_thread_path_traversal_rejected(self):
        log = self.root / "events.jsonl"
        log.write_text('{"type":"thread.started","thread_id":"../../other"}\n{"type":"turn.completed"}\n')
        with self.assertRaises(common.CanvasError):
            collector.parse_events(log)

    def test_tampered_original_rejected(self):
        result = self.render()
        Path(result["original_path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(common.CanvasError, "changed"):
            collector.collect(Path(result["job_dir"]))


if __name__ == "__main__":
    unittest.main()
