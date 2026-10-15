# Sprite strips and animated previews

Adapted from OpenAI Game Studio sprite-pipeline (MIT), and Hatch Pet identity,
spacing, effects, and review guidance (Apache-2.0). See ../NOTICE.
Canvas uses configurable cells and state names; it does not impose the Codex pet atlas.

## Generate

Start with one accepted character frame. If absent, render and inspect that first.
Lock silhouette, face, markings, palette, outfit, prop side, outline weight and proportions.
Create a reference canvas from the approved seed:

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas sprite-guide --seed /absolute/path/seed.png --frames 6 --output .canvas/run-guide.png
```

Generate a whole horizontal strip in one image call. Independent per-frame generations
tend to drift. Attach both seed (`identity`) and canvas (`layout`) to the render.
The canvas is an invisible construction reference, not finished artwork to copy.

```text
Create a six-frame right-facing walk cycle in one horizontal strip.
Image 1 defines the exact character; image 2 defines six equal invisible frame slots.
Each slot contains one complete, distinct pose. Keep the same identity and scale.
Sequence: right contact, down, passing, left contact, down, passing. Loop naturally.
Fixed side-on camera, same baseline, equal slot spacing, 12% safe padding in every slot.
Transparent background. No guides, numbers, labels, floor, shadow, scenery or checkerboard.
No detached effects, motion streaks, dust, glow or slot-crossing limbs.
```

For a different action, write concrete poses and timing suitable for that action.
For jumping, the character's vertical movement matters: preserve it during normalization.
Use `--transparent` on render. If transparency fails, correct the generation first.
Chroma key is an explicit cleanup option for intentionally flat-background assets,
not a silent replacement for genuine transparency. Never key out a color in the character.

## Normalize and inspect

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas sprites --input /absolute/path/to/job/original.png --frames 6 --frame-size 64x64 --padding 2 --anchor bottom --duration 120 --output-dir public/sprites/walk
```

- `bottom`: shared scale, bottom-center baseline for locomotion.
- `center`: shared scale and centered content for UI animation.
- `source`: preserve raw-slot offsets, including jump height and intentional displacement.
- `--smooth`: use Lanczos for non-pixel art; default is nearest-neighbor.
- `--lock-first /path/seed.png`: use an approved first frame already at the final cell size.

Outputs: individual transparent PNGs, atlas.png, manifest.json, contact-sheet.png,
and preview.gif. The review GIF uses a checkerboard; the atlas and frames retain alpha.
Inspect the raw strip before slicing, then inspect the contact sheet and animation.
Blank slots, content touching slot edges, and entirely repeated frames cause errors.
These checks cannot prove that a slot contains exactly one correct character.
Verify identity, correct pose count, motion, readable detail, baseline, and loop seam visually.
Export accepted frames as a final animation in playback order:

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas animate --frames public/sprites/walk/frames/*.png --output public/sprites/walk.webp --duration 120
```

WebP and `.png` (APNG) retain alpha. GIF requires an explicit opaque `--background`
when the frames contain transparency; it cannot preserve soft alpha.
Do not describe the checkerboard review GIF as a transparent final asset.
Repair the failed strip with seed and original as references. Never fabricate missing poses.
