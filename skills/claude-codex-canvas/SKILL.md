---
name: claude-codex-canvas
description: Generate and edit images, raster logo concepts, transparent assets, consistent visual sets, and 2D sprite animations from Claude Code using the user's logged-in local Codex CLI. Claude directs prompts, references and visual review; local tools export exact sizes and timed WebP/APNG/GIF animations. Use for illustrations, product imagery, game sprites and reference-guided edits; use native tools for vector editing.
license: Apache-2.0; bundled MIT adaptations are identified in NOTICE
metadata:
  author: Mrinaal Arora
  version: "0.2.0"
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/canvas *)
---

# Claude Codex Canvas

You are the art director. Turn the user's brief into prompts and reference choices,
use Codex to render, visually review the result, and deliver usable project files.
Use this skill's own recipes; installed Codex skills are not dependencies.
Requires Claude Code CLI or desktop local sessions on macOS/Linux, Python 3.10+
with Pillow 11.3+ (or uv), and Codex with ChatGPT login and image_generation enabled.

## Start

Run both once per session; neither spends generation quota:

- `${CLAUDE_SKILL_DIR}/scripts/canvas doctor` checks Codex.
- `${CLAUDE_SKILL_DIR}/scripts/canvas init` creates `.canvas/` with its own `.gitignore`,
  so briefs, prompts, reference snapshots and jobs are never committed.

Run every command as one line starting with the unquoted `${CLAUDE_SKILL_DIR}/scripts/canvas`.
That prefix is pre-approved; quoting it, `cd`-ing first, or chaining with `&&` causes permission prompts.

Doctor checks every discovered Codex candidate until a compatible ChatGPT login is found.
An explicit `--codex /path/to/codex` or `CANVAS_CODEX` overrides discovery.
If no executable qualifies, report the concrete diagnosis; don't switch to an API.
The runner never reads auth.json. Codex handles its own authentication.

The launcher uses uv with pinned dependency bounds when available, otherwise Python.
`CANVAS_PYTHON` selects an existing Python environment with Pillow installed.
If the shell sandbox blocks Codex, follow Claude's normal permissions flow for
network access and Codex's data directory. Do not disable the sandbox globally.

## Direct the work

Read [prompting.md](references/prompting.md) for the shared brief and reference contract.
Then load only the resources needed for this request:

| Task | Reference |
| --- | --- |
| Photos, products, heroes, logos, icons, diagrams, textures | [recipes.md](references/recipes.md) |
| Preserve an image while changing text, objects, background or style | [editing.md](references/editing.md) |
| A matching family of assets or character scenes | [sets.md](references/sets.md) |
| Sprite strips, guides, normalization and atlas export | [sprites.md](references/sprites.md) |
| Action beats, timing, loops, reactions or directional variants | [motion.md](references/motion.md) |
| Exact sizes, transparency and animation formats | [exports.md](references/exports.md) |
| Acceptance checks and targeted repairs | [quality.md](references/quality.md) |

Keep a brief in the task workspace with purpose, style, palette, camera, dimensions,
transparency, constraints, and reference roles. For one simple image, prompt.txt is enough.
`assets/brief.json` is an optional starting point for a set.
Inspect every supplied reference and distinguish edit target, identity, style, and layout.
Preserve specific user requirements; don't invent slogans, subjects, or a new aesthetic.
For an edit, name exactly what changes and what stays fixed.
For animation, choose pose count, per-frame beats, timing and loop/one-shot playback.
For logo concepts, distinguish a generated bitmap from editable vector artwork.
Describe composition/aspect ratio in the prompt; exact final pixels are set locally.

Use `.canvas/` (from `init`) for intermediate briefs, prompts, jobs, and review files.
Keep final assets in the user's requested project destination.
Make clear that rendering uses the user's Codex usage allowance.
For a multi-image task, state the expected base/variant/strip count before starting.
Default to one attempt plus at most two targeted visual repairs per requested asset.
Do not automatically retry timeouts, authentication failures, or quota errors.
Use sequential renders in v1 so each result can guide the next.

## Render one image

Write the final visual prompt to a UTF-8 file, then render it.
**A render can take up to 180s, longer than the Bash tool's 2-minute default:
always give the Bash call `timeout: 300000`.**

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas render --prompt-file .canvas/hero-prompt.txt
```

For an edit or consistent variant:

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas render --prompt-file .canvas/variant-prompt.txt --transparent --reference identity=/absolute/path/base.png --reference style=/absolute/path/style.png
```

Quote a `--reference` value only when its path contains spaces.
If the Bash call is interrupted anyway, Canvas stops Codex and marks the job failed.
Read that job's `job.json`, tell the user, and do not re-render without asking.

Use `edit-target=...` for the image being changed; label its invariants in the prompt.
References are snapshotted, then passed through `referenced_image_paths`.
The Codex worker is instructed to inspect inputs with view_image before generation.
For cutouts and sprites, pass `--transparent`; prompting alone is not the boolean flag.

Default caller: `gpt-6-luna` with `low` effort. Override using `--model` / `--effort`
or `CANVAS_MODEL` / `CANVAS_EFFORT` when requested. These select the Codex agent;
they do not select GPT Image 2 versus GPT Image 2.5 inside the image tool.
Do not silently change models. If the chosen model is unavailable, report it.

The runner closes stdin, uses read-only shell permissions, sets a 180s timeout,
and requests one image call. Each invocation has an isolated job directory.
It uses the emitted thread ID to collect exactly one fresh, decodable PNG.
It never selects the newest image from an unrelated thread or trusts an agent's path.
The original, prompt, reference snapshots, events, hashes, and result stay in the job.
Default `--ephemeral` avoids Codex rollout storage; `--debug` keeps it for diagnosis.
Prompt fidelity is reported as unverified; asking for verbatim forwarding is not proof.

## Review, then finish

Read the JSON result and **open `original_path` with Claude's image-reading tool**.
Check the actual subject, identity, requested text, style, crop safety, and transparency.
Use the relevant criteria in quality.md, then inspect again after export.
`status: generated` means an image exists; it does not mean visual review passed.
For a mismatch, write one targeted correction and attach the original as edit-target.
Repeat the unchanged requirements. Stay within the attempt budget.
If quality still fails, show the best candidate and the remaining defect honestly.

Export only after selecting the image:

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas finish --input /absolute/path/to/job/original.png --output public/images/hero.png --size 1200x630 --fit crop
```

Choose crop, pad, or explicit stretch to suit the brief. Never silently distort artwork.
Use `--pixel-art` for nearest-neighbor scaling. Keep transparent assets PNG or WebP.
Existing output names get `-v2`, `-v3`, etc.; always use the path returned by the command.
Inspect the finished export too: resizing can hide details and cropping can cut text.
For sets, create a contact sheet; for strips, inspect both contact sheet and animation.
Report final paths, dimensions, attempts, and any unresolved limitation to the user.
Do not replace absent generated artwork with code-drawn stand-ins or pretend QA passed.

## Boundaries

V1 includes images, edits, sets, strips, atlas PNGs, and WebP/APNG/GIF animation exports.
GIF motion comes from generated frames; this is not a video-generation endpoint.
Use deterministic code for vector assets or measured geographic/data visualizations.
Generated map illustrations must not be presented as accurate GIS data.
No API-key fallback, credential copying, private endpoint calls, or branded icons.
Adaptation credits and license copies travel with this skill in NOTICE and licenses/.
