"""Shared test workspace. Puts the skill's scripts on the import path."""
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/claude-codex-canvas/scripts"
sys.path.insert(0, str(SCRIPTS))

import canvas  # noqa: E402


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
