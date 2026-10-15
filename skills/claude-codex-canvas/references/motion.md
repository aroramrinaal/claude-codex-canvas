# Motion recipes and timing

Choose only the actions the user needs. Frame counts, durations and styles below are
starting points to adjust for the action and delivery requirements.

## Plan before generating

Define the action, viewpoint, facing, number of unique poses, playback order, timing,
loop versus one-shot, and what stays fixed. Use one accepted character image across
states. A clean idle and a clear locomotion strip are useful early checks for a large set;
a single requested wave does not need unrelated idle/run jobs.

Keep body volume, head shape, costume and prop attachment consistent. Change joints,
expression and body position to express motion; do not merely translate a still frame
and call it a generated walk. Allow intentional squash/stretch without changing identity.
For small sprites, prefer a restrained readable motion over busy detail or morphing.

## Pose library

| Action | Suggested poses in playback order | Timing in milliseconds | Playback / anchor |
| --- | --- | --- | --- |
| Idle, 6 | Rest; inhale; half blink; closed blink; open eyes; exhale toward rest. | 280,140,80,80,140,280 | Loop / bottom or source |
| Wave, 4 | Neutral; arm raised; hand tilts outward; arm returns toward neutral. | 180,120,180,240 | One-shot, or loop if seam works / bottom |
| Jump, 5 | Crouch/anticipation; push-off/lift; airborne apex; descent; landing/settle. | 140,90,140,90,200 | One-shot / source |
| Walk, 8 | Right contact; down; passing; up; left contact; down; passing; up. | 100 each | Loop / bottom; source if body bob matters |
| Run, 8 | Right contact; compression; passing; flight; left contact; compression; passing; flight. | 80 each | Loop / source for flight height |
| Waiting, 6 | Rest; glance; hold glance; slight head tilt; return; rest variation. | 260,120,200,140,140,260 | Loop / bottom or source |
| Thinking, 6 | Neutral focus; lean; narrow eyes; head tilt; blink; return. | 200,140,220,180,80,220 | Loop / bottom or source |
| Reaction, 5 | Neutral; recoil; strongest expression; recovery; settle. | 100,70,180,120,260 | One-shot / source if displaced |
| Celebrate, 6 | Anticipate; lift arms; peak expression; small follow-through; arms lower; settle. | 120,100,240,100,120,240 | One-shot / bottom or source |

Use an appropriate anatomy: a wheel, tail, wings or tentacles need their own motion beats.
For a looping cycle, the final pose should lead naturally into the first, not duplicate it
solely to hide a seam. A duplicate endpoint can create an unintended pause. Use durations
for holds instead of asking for several identical generated cells.
For a one-shot that starts/ends at neutral, explicitly include those poses or reserve
existing accepted neutral frames in the playback sequence. Do not force a neutral seed
over an anticipation pose with `--lock-first`.

## Prompt fragments

Use after the identity/layout block in sprites.md. Replace timing/counts to match the brief.
Timing is encoded locally; the image model produces poses, not timed animation files.

```text
Action: five-frame jump, left to right: crouch, push-off, apex, descent, landing.
The head and torso rise within each fixed slot; the feet are highest at the apex.
Keep the same camera and body proportions. Show lift through body position only.
Leave room above the head. No floor shadow, dust, landing ring, streaks or extra props.
```

```text
Action: a four-frame friendly wave: neutral, arm raised, hand tilts, arm returns.
Use the character's existing arm and hand; the other hand keeps its original prop.
Show the gesture through poses only. No wave marks, floating symbols or arm duplicates.
```

```text
Action: an eight-frame in-place run facing right. Alternate foot contact,
compression, passing and flight phases for each leg. The hands counter-swing.
Keep the character centered in each slot, with intentional vertical lift during flight.
No camera travel, floor, dust, motion blur, speed lines or detached effects.
```

## Mirroring and asymmetric identity

Do not automatically mirror a right-facing strip to obtain the left-facing strip.
A flip swaps handed props, side-specific markings, text, emblems, accessories and lighting.
If those matter, generate the opposite view with the canonical identity and accepted gait
as references, explaining how anatomical sides project into the new view.
Avoid ambiguous "left hand": distinguish the character's left from screen-left.
Only use deterministic mirroring when the design and lighting are symmetric enough and
the requested action permits it; inspect and disclose the derivation. Never mirror text.

## Effects and secondary motion

For ordinary character strips, keep effects attached to the silhouette, inside the slot,
and readable at final size. A tear touching a cheek or an attached smoke puff can convey
a reaction; floating punctuation and dust can be mistaken for separate sprite fragments.
Keep hair, cloth, tails and props attached as they follow through. Check occlusion order.
If the user explicitly requests a separate effect animation, give it its own strip and
consistent origin; a detached effect is intentional there. Preserve soft alpha for glows,
and export WebP/APNG rather than forcing hard pixel edges or chroma-key cleanup.

## Timing and delivery

Apply the chosen list using `--durations`; it must contain one value per frame.
Use `--play-once` for reactions and non-looping actions. Defaults are 120ms and an infinite loop.
Do not automatically append a long final hold to continuous locomotion; it can hitch.
If motion needs refinement, first adjust playback timing without generating again.
Timing cannot repair incorrect anatomy, skipped gait phases or frame-to-frame morphing.
Retain an accepted still as a reduced-motion fallback for UI animation when useful.
