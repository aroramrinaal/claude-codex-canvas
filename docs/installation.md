# Installation and runtime

[Back to README](../README.md) · [How it works](HOW_IT_WORKS.md)

## Requirements

Requires macOS/Linux, Python 3.10+, Pillow 11.3+ (or [uv](https://docs.astral.sh/uv/)),
and a compatible Codex CLI signed in with ChatGPT. No API key or API fallback.
Image generations count toward your Codex usage allowance.

## Install locally

From this repository:

```bash
python3 scripts/install.py
```

This links the skill into `~/.claude/skills/` without replacing an existing skill.
Claude Code watches that folder, so edits to the linked repository apply immediately.
Cowork, cloud sessions and routines do not read `~/.claude/skills/`; Canvas needs local Codex anyway.
Start a new Claude Code CLI or desktop **local** session, then ask:

```text
/claude-codex-canvas Make a transparent six-frame walk cycle for this character,
with 64x64 frames. Keep the same face and palette, and preview the animation.
```

For plugin installation, add this repository's absolute path through
`/plugin marketplace add /absolute/path/to/claude-codex-canvas`, then run
`/plugin install codex-canvas@codex-canvas`.
Choose either standalone or plugin installation to avoid duplicate skills.
The plugin invocation is `/codex-canvas:claude-codex-canvas`.
Claude reserves the `claude-` prefix for plugin IDs, so the plugin ID is `codex-canvas`.
The `skills/claude-codex-canvas/` folder is also a self-contained Agent Skill.

## Runtime

```bash
skills/claude-codex-canvas/scripts/canvas doctor
skills/claude-codex-canvas/scripts/canvas init
skills/claude-codex-canvas/scripts/canvas --help
python3 -m unittest discover -s tests -v
```

The launcher uses uv when installed; otherwise install `Pillow>=11.3,<13` in your
Python environment. `CANVAS_PYTHON` selects that interpreter explicitly.
Default Codex caller: `gpt-6-luna`, low effort; override `--model` / `--effort`.
That setting selects the calling agent, not the image backend behind Codex's tool.
`CANVAS_CODEX` selects an executable; automatic discovery rejects incompatible copies.
Claude's shell sandbox must permit Codex network access and writes to its data directory.

Each render creates `.canvas/jobs/<id>/` with input snapshots, prompt, original,
events and metadata. `init` and `render` add a `.gitignore` there, so it stays out of git
in any project. Outputs never overwrite existing files. `--debug` retains
Codex session logs; the default is ephemeral. Private job data is gitignored here.
Visual acceptance belongs to Claude; geometry checks alone cannot certify good art.
Codex pets, API fallback and remote/cloud Claude sessions are outside v1.

## Credits and license

Apache-2.0. Adapts OpenAI **imagegen** and **Hatch Pet** recipes (Apache-2.0), and
**Game Studio** sprite workflow (MIT); see [NOTICE](../NOTICE) for sources and changes.
Upstream license copies travel inside the skill. No upstream icons or logos are included.
Built on the [Agent Skills format](https://agentskills.io/home),
[Codex CLI](https://github.com/openai/codex), and
[Claude Code skills](https://code.claude.com/docs/en/skills).
The direction mirrors [Codex Claude Crew](https://github.com/aroramrinaal/codex-claude-crew):
Canvas keeps Claude in charge of art direction and uses Codex for image rendering.
