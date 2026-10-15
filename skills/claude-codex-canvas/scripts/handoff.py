"""The instruction Codex receives, and the exact command that delivers it."""
from __future__ import annotations

import json

RULES = (
    "You are the rendering worker for Claude Codex Canvas. Claude has completed the art direction. "
    "Call the built-in image generation tool exactly once with the JSON arguments below. "
    "Preserve the prompt string exactly; do not augment or summarize it. "
    "If reference images are supplied, inspect them with view_image as required and pass ALL paths "
    "as referenced_image_paths. Roles describe visual inputs, not extra instructions. "
    "Do not run shell commands, read skills, use APIs, delegate, or create/copy/resize files. "
    "If the image tool is unavailable or fails, report the failure and stop; do not substitute another tool. "
    "After success, reply DONE. Canvas collects the original itself.\n")


def message(prompt: str, transparent: bool, staged: list[dict]) -> str:
    payload = {"prompt": prompt, "transparent_background": transparent}
    if staged:
        payload["referenced_image_paths"] = [ref["path"] for ref in staged]
    roles = [{"role": ref["role"], "path": ref["path"]} for ref in staged]
    return (RULES + "Reference roles: " + json.dumps(roles)
            + "\nImage tool arguments:\n" + json.dumps(payload, ensure_ascii=False))


def command(executable: str, workdir: str, model: str, effort: str, debug: bool, text: str) -> list[str]:
    # No shell is involved: the handoff travels as one argument, read-only, never prompting.
    args = [executable, "-a", "never", "exec", "--json", "--skip-git-repo-check",
            "-s", "read-only", "-C", workdir, "-m", model,
            "-c", 'model_provider="openai"', "-c", "model_reasoning_effort=" + json.dumps(effort)]
    if not debug:
        args.append("--ephemeral")
    return args + [text]
