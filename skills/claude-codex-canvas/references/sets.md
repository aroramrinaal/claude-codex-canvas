# Consistent asset sets

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
