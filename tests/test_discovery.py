import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import ROOT, WorkspaceTest

import common
import discovery


class DiscoveryTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.fake = self.root / "fake codex"
        self.fake.write_text(f"#!{sys.executable}\n" + (ROOT / "tests/fixtures/fake_codex.py").read_text())
        self.fake.chmod(0o755)
        self.home = self.root / "codex-data"
        self.env = patch.dict(os.environ, {"CODEX_HOME": str(self.home), "FAKE_CODEX_MODE": "success"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_doctor_reports_capabilities_without_rendering(self):
        result = discovery.preflight(str(self.fake))
        self.assertEqual(result["auth"], "ChatGPT")
        self.assertFalse(result["generation_tested"])
        self.assertFalse(self.home.exists())

    def test_discovery_skips_old_executable(self):
        stale = self.root / "old-codex"
        stale.write_text('#!/bin/sh\nprintf "old CLI\\n"\n')
        stale.chmod(0o755)
        with patch.object(discovery, "candidates", return_value=[str(stale), str(self.fake)]):
            result = discovery.preflight()
        self.assertEqual(result["executable"], str(self.fake))
        self.assertEqual(len(result["rejected_candidates"]), 1)

    def test_explicit_executable_does_not_fall_back(self):
        with self.assertRaises(common.CanvasError):
            discovery.preflight(str(self.root / "absent"))

    def test_disabled_and_api_auth_rejected(self):
        for mode in ("disabled", "api-auth"):
            with self.subTest(mode=mode), patch.dict(os.environ, {"FAKE_CODEX_MODE": mode}):
                with self.assertRaises(common.CanvasError):
                    discovery.preflight(str(self.fake))

    def test_nvm_installs_found_newest_first(self):
        for version in ("v9.11.2", "v23.11.1", "v18.20.0"):
            folder = self.root / f".nvm/versions/node/{version}/bin"
            folder.mkdir(parents=True)
            (folder / "codex").write_text("")
        with patch.object(Path, "home", return_value=self.root):
            found = [p.parts[-3] for p in discovery.nvm_installs()]
        self.assertEqual(found, ["v23.11.1", "v18.20.0", "v9.11.2"])


if __name__ == "__main__":
    unittest.main()
