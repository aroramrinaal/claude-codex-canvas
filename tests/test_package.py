import json
import re
import subprocess
import sys
import unittest

from helpers import ROOT, SCRIPTS, WorkspaceTest

SKILL = ROOT / "skills/claude-codex-canvas"


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

    def test_init_creates_ignored_workspace(self):
        result = self.command("init", "--dir", str(self.root / ".canvas"))
        self.assertTrue(result["git_ignored"])
        self.assertIn("*", (self.root / ".canvas/.gitignore").read_text().splitlines())
        self.command("init", "--dir", str(self.root / ".canvas"))

    def test_documented_commands_match_allowed_tools(self):
        # A quoted path would not match the pre-approved `Bash(${CLAUDE_SKILL_DIR}/scripts/canvas *)` rule.
        for doc in [SKILL / "SKILL.md", *(SKILL / "references").glob("*.md")]:
            with self.subTest(doc=doc.name):
                self.assertNotIn('"${CLAUDE_SKILL_DIR}', doc.read_text())
                self.assertIsNone(re.search(r"scripts/canvas [^\n]*\\\n", doc.read_text()))


if __name__ == "__main__":
    unittest.main()
