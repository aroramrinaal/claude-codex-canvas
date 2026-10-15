# Still-image recipes

Select the relevant recipe and substitute the user's actual content. Examples are
not permission to add their palette, props or copy to unrelated requests.

## Photo and product

**Natural/editorial photo:** describe an observable moment, viewpoint and real surfaces.
Use skin texture, worn fabric or material grain where appropriate; avoid automatic
beauty retouching, cinematic grading or glossy studio polish for a candid request.

```text
Create a candid editorial photograph of a bicycle mechanic adjusting a wheel.
Eye-level medium view; hands naturally contact the spokes and tool.
Soft workshop window light, believable fabric wear and metal texture.
Preserve ordinary proportions and the requested environment; no added signage.
```

**Product/mockup:** separate product identity from packaging design and mood references.
Lock shape, proportions, material finish, logo placement and exact label copy. Specify
whether the requested output is flat artwork or a perspective mockup.

```text
Image 1 is the product identity. Photograph that same ceramic cup for a catalog.
Preserve its handle, glaze pattern, silhouette and markings.
Three-quarter camera, large soft key light, warm neutral backdrop, room for a square crop.
One product only; no invented label text, branding or accessories.
```

## Website, campaign and interface imagery

**Hero/section illustration:** match the real page's aspect ratio and text placement.
Call out quiet copy space only when the page uses it. Keep important content clear of
responsive crop edges. HTML supplies headings and buttons unless raster text was requested.

```text
Create an editorial illustration for the supplied developer-tool landing page.
Use the page's existing palette and the reference's flat paper-textured treatment.
Keep the focal subject in the region shown by the layout reference and leave its
copy area quiet. No baked-in headline, button, watermark or extra interface panels.
```

**Advertising/social:** specify audience, actual brand inputs, focal message and exact
approved copy. Decide whether the logo is supplied artwork or merely a placeholder.
Generate artwork separately from long copy where editability matters; don't invent claims.

**UI mockup/wireframe:** specify fidelity first, then device, screen boundaries, hierarchy
and real controls. A low-fi wireframe needs grayscale blocks and concise labels; a polished
screen needs consistent spacing and usable contrast. Treat the output as a bitmap concept,
not a functioning interface. Implementing the interface itself belongs in native code.

```text
Make a low-fidelity mobile onboarding wireframe with three separate screens:
welcome, feature explanation, account form. Grayscale, clear screen boundaries,
readable supplied labels, realistic touch-target proportions. No photos or decoration.
```

## Logos, wordmarks and illustrated icons

Ask for a **flat raster concept** with a strong silhouette, balanced negative space,
generous padding and the requested palette. Keep mockup surfaces, embossed treatments,
3D lighting and slogans out unless requested. A request for "vector style" describes
appearance; it does not turn the PNG into an SVG.

```text
Design one flat geometric symbol for the supplied brand brief.
Make the silhouette readable at 32px and its interior negative space remain open.
Use the supplied two brand colors; centered with generous transparent padding.
Output the mark alone, without a wall mockup, lettering, gradient or 3D extrusion.
```

- **Monogram:** name the exact letters and how they should interlock; check ambiguous glyphs.
- **Wordmark:** quote the exact name; specify type character, case, spacing and baseline.
  Inspect letter-by-letter and at small size. Do not claim generated lettering is editable.
- **Icon set:** use a shared view angle, visual weight, padding, palette and light source.
  Render separate icons from the accepted style reference; review the set together.
- Export a small preview to reveal broken silhouettes and muddy details. Create alternate
  colorways from the approved design rather than independently redesigning each version.

## Story, stylized concept and historical scenes

**Story/panels:** specify concrete scene beats and panel reading order; attach the accepted
character image for each continuation. Keep costume, face and proportions stable while
action changes. A story panel grid is not an animation strip.

**Stylized concept:** state material, rendering treatment, camera and light. Distinguish
concept exploration from a production asset with fixed geometry, alpha and delivery size.
Choose clay, watercolor, flat cel shading, painterly or other treatment to match the request.

**Historical scene:** provide place, date/period and verified clothing, architecture and
props. Identify any intentional fiction. Inspect for anachronisms; a convincing rendering
does not establish historical accuracy.

## Diagrams, educational and business visuals

Specify audience, reading order, exact entities, relationships, labels and hierarchy.
Use verified content. Review arrows and connections as carefully as spelling. When numerical
positions or editable data are essential, use plotting/native diagram tools instead.

```text
Make an illustrated explainer of the supplied four-step process for new users.
Use four clearly separated stages left to right, with exactly the supplied labels.
Connect only the transitions in the reference specification. Strong contrast and
generous whitespace; no invented metrics, decorative arrows or tiny footnotes.
```

For science, identify the learning objective and constraints on anatomy/mechanisms.
For slide artwork, leave space for editable title and labels. Do not generate fictional
citations, chart values or authoritative-looking details to fill an empty area.

## Game art, textures and backgrounds

**Character seed:** generate one full-body neutral pose with clear silhouette, visible
limbs, requested view and enough padding for later actions. Accept it before animation.
**Inventory icon:** one object; consistent isometric/top-down/side view and outline weight;
readable at the intended UI size. Keep background scenery out of a transparent icon.
**Environment:** establish camera, focal point, traversal/readable play area and palette.
Keep busy detail away from gameplay or text regions that the actual layout reserves.
**Tileable texture:** orthographic surface, even lighting, matching opposite edges, no
unique focal object or baked-in directional shadow unless explicitly needed.

```text
Create a seamless top-down texture of the requested sandstone material.
Uniform scale and diffuse illumination across the tile; opposite edges must continue.
No perspective, isolated hero rock, text, border, gradient or cast shadow.
```

Test a 2×2 repeat of the returned texture using deterministic tiling of the finished
image. Inspect all seams and obvious repeating landmarks; "seamless" in the prompt
is not verification. Do not describe a generated color texture as a complete PBR set.
