# How Claude Codex Canvas works

Canvas is an Agent Skill installed in Claude Code.
Claude owns the brief, reference choices, prompts and visual review.
An authenticated local Codex CLI invokes its built-in image generation tool.
Python and Pillow prepare exact final files from the generated originals.

## Package

- `skills/claude-codex-canvas/SKILL.md` is the skill entrypoint.
- `references/` holds prompting, still/edit recipes, sets, motion, sprites, QA and exports.
- `scripts/canvas` is the launcher; `canvas.py` is the command interface.
- Codex side: `discovery.py` finds a compatible CLI, `handoff.py` builds its instruction
  and command, `runner.py` runs one job, and `collector.py` accepts its image.
- Local side: `images.py` holds shared decoding and inspection, `exports.py` exact stills
  and animations, `animation.py` shared timing/palettes, `alpha.py` chroma keys,
  `review.py` contact sheets, `sprites.py` strips.
- `common.py` holds errors, hashing, collision-safe saves and git-ignored workspaces.
- `assets/brief.json` is an optional reusable set brief.
- `NOTICE`, `LICENSE` and `licenses/` accompany the standalone skill.

## Preflight

Run `canvas doctor`; it generates no image and spends no generation quota.
Run `canvas init`; it creates `.canvas/` with a `.gitignore`, so private job data stays local.
Discovery checks PATH, common app installation paths, and nvm/Volta/Bun installs,
since apps launched from the Dock may not inherit a shell's PATH.
It checks CLI flags, image_generation availability and ChatGPT login status.
Old or incompatible candidates are skipped, with their reasons retained.
An explicit `--codex` or `CANVAS_CODEX` is authoritative and does not silently fall back.
Canvas never reads auth.json; Codex manages authentication itself.
API-key environment overrides are removed from the child process.

## Rendering

Claude writes a UTF-8 prompt file and assigns roles to reference images.
Run `canvas render --prompt-file prompt.txt` with any `--reference ROLE=PATH` inputs.
Add `--transparent` when the image needs actual alpha.
The runner creates a unique job directory and snapshots every reference.
It passes a JSON visual request to Codex as a subprocess argument, without a shell.
Codex is instructed to inspect references and forward the visual prompt unchanged.
The default caller is gpt-6-luna at low effort; both settings are overridable.
The caller model is separate from the GPT Image backend; Canvas does not pin the latter.
The subprocess uses closed stdin, a read-only shell sandbox and a bounded timeout.
SIGTERM or SIGHUP, as sent when Claude's Bash tool times out, stops Codex and fails the job.
The skill tells Claude to give `render` a 5-minute Bash timeout, above the 180s render limit.
Its working directory is isolated from the user's project instructions.
By default, --ephemeral avoids Codex rollout persistence.
Use --debug when a retained Codex session is needed for diagnosis.
Canvas retains its own small event log, prompt, reference snapshots and original.

## Collection

The JSON stream identifies the new thread; an image event is not required.
Canvas accepts only a successful completed turn with exactly one thread ID.
It checks `$CODEX_HOME/generated_images/<thread_id>/`, defaulting to `~/.codex`.
This storage convention is an adapter boundary and may change in future Codex versions.
Exactly one fresh PNG is required; unrelated threads and ambiguous outputs are rejected.
The collector decodes the PNG, validates transparency when requested and hashes it.
The original is copied unchanged into the job directory.
`job.json` records paths, references, caller settings, usage and review status.
The image backend and actual forwarded prompt are not inferred from an agent's reply.
Successful collection still requires Claude's visual review.

## Review and exports

Claude opens the original and checks subject, identity, text, style and composition.
A targeted correction uses the existing image as an edit reference.
The default budget is one attempt plus up to two visual repairs per asset.
Timeouts and quota failures never trigger automatic re-rendering.
`finish` makes exact dimensions using an explicitly chosen crop, pad or stretch operation.
PNG and lossless WebP preserve transparency; JPEG requires an opaque flattening choice.
ICO exports are square and at most 256px; pixel-art resizing uses nearest-neighbor.
Exports reserve filenames atomically and create versioned siblings on collisions.
The generated original is always retained separately.

## Sets and sprites

Sets begin with an accepted base image reused as an identity or style reference.
Render sequentially, review each result, then inspect a contact sheet of final exports.
For sprites, generate an entire strip grounded in an accepted seed frame.
Normalize all frames with one shared scale and explicit anchor.
Bottom anchors stabilize walks; source anchors retain jump height and displacement.
Locking the first frame anchors the sequence to its seed's scale and position, with clipping checks.
Empty slots, edge-touching content and entirely identical frames are rejected.
Outputs include frame PNGs, an atlas, a manifest, a contact sheet and a preview GIF.
The GIF uses a checkerboard for review; frame PNGs and the atlas retain true alpha.
`animate` exports accepted frames as transparent WebP/APNG, or GIF with an opaque background.
Per-frame `--durations` and `--play-once` encode holds and reactions; GIF uses a shared palette.
Claude must inspect identity, motion, framing and loop continuity before delivery.
Geometry checks cannot identify every wrong character or incorrect pose.

## Scope and verification

V1 targets Claude Code CLI and desktop local sessions on macOS/Linux.
It has no API fallback, video endpoint or remote execution bridge.
The test suite uses a fake Codex executable and synthetic images without generation spend.
It exercises process failures, artifact validation, exact exports and sprite geometry.
The doctor command checks the real installation without rendering.
