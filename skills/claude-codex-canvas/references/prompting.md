# Art direction and prompt recipes

Adapted from OpenAI imagegen's prompting.md and sample-prompts.md (Apache-2.0).
Changed for Claude-led art direction, a Codex CLI handoff, and separate local exports.
See ../NOTICE. These are prompt recipes, not image-tool API parameters.

## Shared structure

Use only fields that improve the request. Detailed user prompts need normalization,
not extra creative requirements. A short clear prompt is often sufficient.

```text
Purpose: where this image will appear and who sees it.
Subject and setting: concrete objects, action, environment.
Style: medium, material, palette, lighting, camera.
Composition: shape, framing, safe space, relative positions.
Reference roles: image 1 = identity; image 2 = layout; etc.
Text verbatim: "exact words", placement and typography.
Keep fixed: identity, markings, product edges, camera, palette.
Change: the one requested edit, if any.
Avoid: specific unwanted objects, artifacts, lettering, effects.
```

Order scene → subject → important details → constraints. State intended use.
Use concrete camera and light language for photographs.
Quote required text exactly; spell unusually important words if needed.
Keep text short and review every character. Raster lettering is not editable type.
For multiple inputs, refer to their order and role, not an ambiguous “this image”.
For revisions, repeat invariants and change one thing at a time.
Request actual alpha with `--transparent`; do not request a painted checkerboard.

## Website hero / illustration

```text
Create a wide editorial illustration for a developer tools landing page.
Subject: a compact workshop desk with a laptop and a single small plant.
Medium: flat shapes, subtle paper texture, navy and warm cream.
Composition: subject in the right half; quiet negative space on the left for HTML copy.
Lighting: soft daylight. Preserve a generous safe margin around the subject.
No text, watermark, floating interface panels, or additional props.
```

Only specify left/right layout when the actual page supports it. Finish to exact
pixels afterward. Layout text belongs in HTML unless in-image text was requested.

## Photographic / product

```text
Create a product catalog photograph of the supplied ceramic cup.
Image 1 is the product identity reference: preserve its shape, glaze, handle and markings.
Three-quarter camera view, soft large studio key light, neutral warm backdrop.
Realistic ceramic texture; product fully visible with room for a square crop.
No new branding, no extra products, no invented lettering.
```

For natural photography, describe an ordinary moment and believable texture.
For mockups, explicitly distinguish the product/design reference from a mood reference.

## Icon / cutout

```text
One compact isometric lantern icon for a game's inventory.
Chunky readable silhouette, dark outline, amber glass, muted iron frame.
Centered, fully visible, generous transparent padding; readable at 64px.
No cast shadow, scenery, lettering, glow outside the silhouette, or checkerboard.
```

Use raster generation for illustrated icons. Extend existing SVG systems in vector code.
Generate the silhouette at a useful size, then test readability at its delivery size.

## Diagrams / infographics / marketing

Specify the exact elements, hierarchy, connectors, labels, and intended audience.
For factual diagrams, verify the content before prompting; review every label afterward.
For marketing, give actual approved copy and brand inputs; don't invent claims.
For a map illustration, distinguish decorative geography from measured GIS output.
Use code/native formats when numeric precision or editable labels are essential.

## Image edit / compositing

```text
Image 1 is the edit target. Replace only the background with a warm pale-blue wall.
Keep the foreground product, all label text, camera perspective, scale and edges identical.
Match existing lighting at the boundary. Add no new objects or decorative effects.
```

For insertion, identify source object, destination, scale, occlusion, light and perspective.
For style transfer, preserve subject identity while naming which stylistic features change.
For extraction, retain fine edges without halos; preserve alpha in the final export.

## Efficient iteration

Start with the smallest meaningful asset, not a full suite of unreviewed variants.
Inspect the returned original, then repair the smallest failed scope.
Record the prompt file and original for every attempt; do not overwrite your evidence.
Use accepted imagery as reference for the next asset rather than rewriting its identity.
Never call a result faithful just because the Codex reply says it is.
