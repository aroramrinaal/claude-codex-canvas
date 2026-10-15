"""Find a compatible, ChatGPT-authenticated Codex CLI. Never generates an image."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from common import CanvasError

REQUIRED_FLAGS = ("--json", "--ephemeral", "--skip-git-repo-check", "--sandbox", "--model")
DEFAULT_MODEL = "gpt-6-luna"
DEFAULT_EFFORT = "low"
KNOWN_PATHS = (
    "/opt/homebrew/bin/codex", "/usr/local/bin/codex", "~/.local/bin/codex",
    "~/.volta/bin/codex", "~/.bun/bin/codex", "~/.npm-global/bin/codex",
    "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex",
    "/Applications/Codex.app/Contents/Resources/codex",
    "~/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex",
    "~/Applications/Codex.app/Contents/Resources/codex")


def child_environment() -> dict:
    env = os.environ.copy()
    # This integration uses saved ChatGPT authentication, never an API fallback.
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY"):
        env.pop(key, None)
    return env


def probe(executable: str, args: list[str]) -> str:
    try:
        result = subprocess.run([executable, *args], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=10,
                                env=child_environment())
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CanvasError(f"Cannot run {executable}: {exc}") from exc
    output = (result.stdout + result.stderr).strip()
    if result.returncode:
        raise CanvasError(f"{' '.join(args)} failed: {output[-600:]}")
    return output


def nvm_installs() -> list[Path]:
    """GUI-launched apps may lack nvm's PATH; newest Node version first."""
    found = Path.home().glob(".nvm/versions/node/*/bin/codex")
    return sorted(found, key=lambda p: [int(n) for n in re.findall(r"\d+", p.parts[-3])], reverse=True)


def candidates(explicit: str | None = None) -> list[str]:
    override = explicit or os.environ.get("CANVAS_CODEX")
    if override:
        return [shutil.which(override) or str(Path(override).expanduser().absolute())]
    paths = [Path(folder or ".") / "codex" for folder in os.get_exec_path()]
    paths += [Path(p).expanduser() for p in KNOWN_PATHS] + nvm_installs()
    found, seen = [], set()
    for path in paths:
        resolved = str(path.resolve())
        if resolved not in seen and path.is_file() and os.access(path, os.X_OK):
            # Keep the launcher path: resolving some npm launchers changes behavior.
            found.append(str(path.absolute()))
            seen.add(resolved)
    return found


def check(executable: str) -> dict:
    version = probe(executable, ["--version"])
    help_text = probe(executable, ["exec", "--help"])
    missing = [flag for flag in REQUIRED_FLAGS if flag not in help_text]
    if missing:
        raise CanvasError("Missing CLI flags: " + ", ".join(missing))
    features = probe(executable, ["features", "list"])
    if not re.search(r"^image_generation\s+.+\s+true\s*$", features, re.M):
        raise CanvasError("image_generation is unavailable or disabled; enable it in Codex first.")
    if "logged in using chatgpt" not in probe(executable, ["login", "status"]).lower():
        raise CanvasError("ChatGPT login required. Run this executable's `login` command.")
    return {"status": "ready", "executable": executable, "version": version,
            "auth": "ChatGPT", "image_generation": True,
            "default_model": DEFAULT_MODEL, "default_effort": DEFAULT_EFFORT,
            "generation_tested": False}


def preflight(explicit: str | None = None) -> dict:
    rejected = []
    for executable in candidates(explicit):
        try:
            return {**check(executable), "rejected_candidates": rejected}
        except CanvasError as exc:
            rejected.append({"executable": executable, "reason": str(exc)})
    raise CanvasError("No compatible, ChatGPT-authenticated Codex found. " + json.dumps(rejected))
