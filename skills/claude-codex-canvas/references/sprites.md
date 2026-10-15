# Sprite strips and animated previews

Canvas uses configurable frame sizes, counts and action names.

Plan the action and timing with motion.md. Use pixel, painted, clay or other requested
style consistently. Generate only the requested states. Keep each state as a separate strip so a failure is repairable.

## Generate

Start with one accepted character frame. If absent, render and inspect that first.
Lock silhouette, face, markings, palette, outfit, prop side, outline weight and proportions.
Create a reference canvas from the approved seed:

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas sprite-guide --seed /absolute/path/seed.png --frames 6 --show-guides --output .canvas/run-guide.png
```

Generate a whole horizontal strip in one image call. Independent per-frame generations
tend to drift. Attach both seed (`identity`) and canvas (`layout`) to the render.
The canvas is an invisible construction reference, not finished artwork to copy.
`--show-guides` draws slot boundaries and inner safe areas for the model. Without it,
the guide has only the seed in the first slot, with the remaining slots transparent.
Always attach the original seed separately: lines on the guide must not define its style.
Prefer a short readable cycle (often 4–8 poses) over an extremely wide strip full of tiny
characters. The CLI accepts 2–32 frames, but that is not a promise of generation quality.
Never generate a giant multi-state atlas in one call merely to save calls.

```text
Create a six-frame right-facing walk cycle in one horizontal strip.
Image 1 defines the exact character; image 2 defines six equal invisible frame slots.
Each slot contains one complete, distinct pose. Keep the same identity and scale.
Sequence: right contact, passing, right push-off, left contact, passing, left push-off.
Each leg alternates its support phase. The last pose flows into the first without a pause.
Fixed side-on camera, same baseline, equal slot spacing, 12% safe padding in every slot.
Transparent background. No guides, numbers, labels, floor, shadow, scenery or checkerboard.
No detached effects, motion streaks, dust, glow or slot-crossing limbs.
```

Keep shape, ear/horn count, eye spacing, markings, clothing fastenings and anatomical
prop side explicit when they define the character. Do not copy the seed unchanged into
every cell. Favor simpler motion if preserving identity and readability requires it.
Run the strip request with references in the same order as the prompt:

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas render --prompt-file .canvas/walk-prompt.txt --transparent --reference identity=/absolute/path/seed.png --reference layout=/absolute/path/run-guide.png
```

Give the Bash call `timeout: 300000`, as for every render. Use the actual path returned
by `sprite-guide`; collision-safe saves may have added a version suffix.

For a different action, write concrete poses and timing suitable for that action.
For jumping, the character's vertical movement matters: preserve it during normalization.
Use `--transparent` on render. If transparency fails, correct the generation first.
Chroma key is an explicit cleanup option for intentionally flat-background assets,
not a silent replacement for genuine transparency. Never key out a color in the character.

## Normalize and inspect

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas sprites --input /absolute/path/to/job/original.png --frames 6 --frame-size 64x64 --padding 2 --anchor bottom --duration 120 --output-dir public/sprites/walk
```

- `bottom`: shared scale, bottom-center baseline for planted locomotion. This removes
  vertical bob from the source; choose `source` when that motion is intentional.
- `center`: shared scale and centered content for UI animation.
- `source`: preserve raw-slot offsets, including jump height and intentional displacement.
- `--smooth`: use Lanczos for non-pixel art; default is nearest-neighbor.
- `--lock-first /path/seed.png`: use an approved first frame already at the final cell size.
  The raw first pose must match this seed's neutral pose. Normalization matches its scale
  and position before replacing frame 1 exactly. If later poses would clip at that scale,
  it fails; use a seed with more room or repair the strip. Do not lock a neutral frame
  over a jump's crouch or a run's contact pose just to reuse a file.
- `--durations 280,140,80,80,140,280`: encode individual holds instead of a uniform duration.
- `--play-once`: for one-shot reactions; also applies to the review GIF.

Keep frame dimensions, style and intended character size consistent across states.
Normalizing every state to fill its cell independently can make the character grow/shrink.
For states that start in the same approved pose, `--lock-first` anchors their scale;
otherwise compare their exported size and repair framing instead of forcing a mismatched seed.

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

Carry timing from the manifest into the final export; `animate` does not read the manifest
automatically. For example, a five-frame one-shot jump:

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas animate --frames public/sprites/jump/frames/01.png public/sprites/jump/frames/02.png public/sprites/jump/frames/03.png public/sprites/jump/frames/04.png public/sprites/jump/frames/05.png --durations 140,90,140,90,200 --play-once --output public/sprites/jump.webp
```

Pass frames in playback order. The generated manifest records each frame's atlas rectangle,
duration and the sequence's playback mode. Atlas packing is one horizontal row per state;
Use the consuming application’s requirements when planning any further atlas packing.
