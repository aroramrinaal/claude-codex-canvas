# Consistent asset sets

## Lock what the set shares

Separate **identity** (who/what it is), **style** (how it is rendered), and **layout**
(where/how large it appears). A new character can share style without copying the
base character's face. One character in several scenes must preserve identity even
when its pose, environment or composition changes.
Write fixed traits once: silhouette, proportions, face, markings, material, palette,
outline weight, light direction, view angle, costume, prop side and relative scale.
State per-asset variations separately. Do not let each prompt invent a new style.

## Produce and compare

1. Fill `assets/brief.json` into `.canvas/brief.json` with the user's actual requirements.
2. Identify the asset list and expected render count; keep a maximum of three attempts per asset.
3. Render the representative asset first. Inspect it before spending on the rest.
4. Use the accepted image as `identity` or `style` reference for each subsequent asset.
5. Preserve camera, palette, material, outline and relative scale in every prompt.
6. Change only the content/action required by the current asset.
7. Use one render per asset; v1 does not start background parallel batches.
8. Finish each accepted image to its own required dimensions and format.
9. Create and inspect a contact sheet of all exports:

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas contact-sheet --inputs public/images/asset-a.png public/images/asset-b.png --output .canvas/set-review.png --columns 4
```

Review the set for consistent visual weight, identity, palette and crop.
A shared prompt is insufficient when the actual images drift.
Regenerate only the failing item with the accepted base and a precise correction.
Record accepted original and final paths in the brief's assets list.
If there is no accepted base yet, do not mark dependent assets accepted.
Keep all generated assets in the project; a path in the Codex cache alone is not delivery.

For each asset, keep a compact record in the brief's `assets` list: `id`, `request`,
`prompt_file`, `references` (ordered role/path pairs), `original_path`, `final_path`,
`attempts`, `review_status`, and any `defects`. Include intended size/format and, for
animation, frame count, durations, anchor and playback mode. The brief is a working
record for Claude, not an automatically executed job manifest.

Use the accepted canonical asset as reference throughout the set. If a user changes
the canonical design, mark dependent assets for re-review; don't quietly mix versions.
For website/icon families, check optical weight at actual display size, not just equal
file dimensions. For character states, check the transition between states as well as
each internal loop. A contact sheet's thumbnails are for comparison, not proof of final scale.
