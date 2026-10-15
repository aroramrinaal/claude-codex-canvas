# Visual acceptance and targeted repairs

Apply the checks relevant to the asset; do not run an unrelated universal checklist.

## Review three stages

1. **Original:** inspect the actual pixels returned by the image tool. Compare with
   the brief and canonical inputs, not the worker's description of what it generated.
2. **Export:** inspect the exact final file at its intended size and background.
   Resampling, crop, alpha flattening and palette reduction can introduce new defects.
3. **Context:** inspect related assets together, and animation in playback. For a UI
   or game, check the real placement when available; otherwise state that integration
   has not been verified. A contact sheet cannot prove timing or a seamless loop.

Claude's file reader may expose only a still frame of an animated file. Use a supported
viewer/browser when available, or inspect individual frames and timing data and clearly
report that playback remains unverified. Do not claim to have watched an unreadable GIF.

## Relevant acceptance criteria

| Asset | Acceptance questions |
| --- | --- |
| Photo/product | Correct subject/count, plausible anatomy/contact, stable product geometry, readable supplied labels, coherent light and reflections? |
| Hero/illustration | Intended hierarchy and style, crop-safe subject, actual copy space, no unintended objects or baked-in UI? |
| Logo/icon | Correct letters, clear silhouette at small size, balanced negative space, consistent visual weight and clean alpha? |
| Edit/composite | Requested change complete; preserved identity/layout; no unrelated changes, seams or mismatched perspective? |
| Diagram/text | Exact spelling and accents, correct relationships and values, readable hierarchy; no fabricated labels or citations? |
| Transparent cutout | Real transparent pixels, preserved holes and fine detail, no checkerboard, fringing or unintended shadow? |
| Set | Same identity/style/view/light, coherent relative scale and margins; no one asset much heavier or softer than others? |
| Sprite strip | Exact pose count; one complete pose per slot; identity and anatomy stable; direction, baseline and action correct? |
| Animation | Timing appropriate; no scale pop, unwanted sliding, duplicated endpoint pause, broken loop or clipped extrema? |
| Texture | Tiled repeat inspected; no seams or distracting repeating landmarks? |

Check transparency against both light and dark backgrounds. A PNG with an alpha channel
can still be entirely opaque; `inspect` reports actual alpha fractions. A checkerboard
painted inside the foreground will require visual detection even when other pixels are clear.

## Choose the smallest correction

| Failure | Next action |
| --- | --- |
| Wrong dimensions/format, good artwork | Use `finish` or `animate`; do not regenerate. |
| Good poses, poor rhythm | Change `--durations` and playback mode. |
| Jump height disappears | Normalize with `--anchor source` from the original strip. |
| Scale pop when locking frame 1 | Verify first generated pose matches the seed and all poses fit at seed scale. |
| Wrong character/face/prop side | Regenerate affected strip with canonical identity and explicit invariants. |
| Empty slot, merged bodies, clipped limbs | Regenerate affected strip with exact slot count and more safe space. |
| Bad loop seam | Repair transition poses or order/timing; do not claim a repeated still fixes the action. |
| Misspelled text | Target the affected text and repeat all preserved layout/product constraints. |
| Background/halo failure | Repair the cutout; use chroma key only for deliberately flat-background inputs. |
| Overall design wrong | Revise the seed/brief, then regenerate only dependent assets. |

The default allowance remains one generation plus two targeted visual repairs per asset.
If exhausted, show the best candidate and the remaining defect. A timeout, authentication
or quota failure is not a visual repair and must not trigger an automatic retry.

## Keep review evidence small

For a simple image, a concise chat review is enough. For a set, record asset ID, accepted
original, final path, prompt file, reference roles, attempts, and unresolved defects in the
brief. Record `accepted` only after actual inspection; tool output such as `normalized`
means mechanical processing succeeded. A known identity/text/pose defect remains visible
in the handoff rather than being hidden by a general "passed" label.

Preserve originals and use returned versioned paths. Deliver final project assets outside
the private jobs folder; do not point application code at a Codex cache or temporary preview.
