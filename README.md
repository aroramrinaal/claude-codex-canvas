# Claude Codex Canvas

**Claude art-directs. Your logged-in Codex renders.**

A Claude Code skill for images, reference-guided edits, transparent assets,
consistent sets, and 2D sprite strips. Claude writes prompts and reviews images;
local scripts preserve originals and deliver exact dimensions.

Includes focused recipes for photos, products, raster logos, edits and consistent sets,
plus action-by-action sprite guidance, per-frame timing and transparent WebP/APNG exports.

## Get started

From this repository, install the skill:

```bash
python3 scripts/install.py
```

Start a new Claude Code CLI or desktop local session, then ask:

```text
/claude-codex-canvas Make a transparent six-frame walk cycle with 64x64 frames.
```

[Installation and requirements](docs/installation.md) · [How it works](docs/HOW_IT_WORKS.md) · [Skill](skills/claude-codex-canvas/SKILL.md)

[Apache-2.0](LICENSE). Adapts OpenAI imagegen, Hatch Pet, and Game Studio recipes;
see [NOTICE](NOTICE) for credits and upstream licenses.
