# Reference-guided edits

Read for object changes, cutouts, compositing, recolors, localization or identity-sensitive work.

## Establish the edit contract

Inspect the target. State **change**, **preserve**, and **acceptance check** before rendering.
Number inputs in attachment order. Supply the target as `edit-target`, plus only references
that constrain the change. A mask-like diagram is a visual guide, not a hard pixel mask.
Canvas does not guarantee pixel-identical untouched regions; compare them after every edit.
When exact unchanged pixels are essential and a deterministic/native edit can achieve the
task, use that method rather than promising a generative preservation guarantee.

```text
Image 1 is the edit target. Image 2 supplies the replacement object only.
Change: replace the cup on the table with the cup from Image 2.
Preserve: table, other objects, camera, crop, subject positions and overall lighting.
Match: perspective, relative size, contact shadow and reflections at the insertion.
No extra objects, copy or redesign of the replacement cup.
```

## Recipes and acceptance checks

| Edit | What to specify | What to inspect |
| --- | --- | --- |
| Object replacement/removal | Identify by position and appearance; reconstruct the revealed surface; preserve nearby objects. | Old-object remnants, repeated textures, warped boundaries, contact/shadow plausibility. |
| Identity/clothing | Lock face, body proportions, hair, pose, expression; name only changed garments/accessories. | Face drift, hands, fit, garment logos, unrequested jewelry or retouching. |
| Background/lighting/weather | Lock subject, geometry, camera, crop; state whether light on the subject may change to match. | Unchanged geometry, coherent light/shadow, preserved fine edges and requested weather. |
| Text localization | Quote each old → new string; preserve type hierarchy, design and imagery; permit reflow only when required. | Every letter/accent, overflow, spacing, accidental extra words, unchanged logos. |
| Cutout | Request genuine alpha; preserve fine edges, internal holes and requested product/label details. | Alpha exists, holes are clear, no fringe/halo, lost hair or checkerboard pixels. |
| Style transfer | State what transfers: palette, brushwork, texture, line quality; lock target subject/layout as appropriate. | Imported reference objects, changed identity, lost structure, unwanted styling. |
| Compositing | Source/destination, placement, scale, perspective, occlusion order and lighting. | Object contact, reflections, shadows, depth and relative size. |
| Sketch to render | Lock arrangement, proportions, camera and silhouette; specify materials and illumination. | Invented parts, moved objects, changed perspective, broken geometry. |

## Targeted prompt examples

```text
Image 1 is the existing poster. Replace only "Welcome" with "Bienvenue".
Keep the headline's position, color, typographic character and hierarchy.
Preserve all imagery and other text. Adjust this headline's size only if needed to fit.
Render the replacement exactly once, including correct spelling; no added words.
```

```text
Image 1 is the subject to extract. Produce that same object on true transparency.
Preserve its silhouette, fine openings, surface detail and printed label.
Remove the background without restyling the object. No halo, floor, shadow or checkerboard.
```

```text
Image 1 defines the layout and character identity; Image 2 defines watercolor texture only.
Apply Image 2's soft pigment edges and paper treatment to Image 1.
Preserve the character's face, outfit, pose, composition and object count.
Do not import Image 2's subject, scenery or lettering.
```

## Multi-step edits and repair

Separate independent changes when doing them together would make failures hard to diagnose.
Keep the accepted original and final prompt for each step. Use the last accepted image as
the edit target; attach the canonical identity reference when needed to prevent accumulated
drift. Mark failed candidates as defect references, not new identity/style authorities.
If a request only needs a new crop, export size, alpha-preserving format conversion or frame
timing, use local commands without another generation. A pixel resize cannot repair anatomy,
misspelled text or a missing animation pose.
