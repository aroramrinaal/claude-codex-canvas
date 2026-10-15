# Exact dimensions and transparency

Codex image generation receives a visual shape request. `finish` controls actual final pixels.
Always keep the generated original. The tool creates versioned siblings instead of overwriting.

| Asset | Example size | Fit | Notes |
| --- | --- | --- | --- |
| Social/OG image | 1200x630 | crop | Keep text and subject inside crop-safe margins. |
| Square illustration | 1024x1024 | pad | Preserve the full silhouette. |
| App illustration | 512x512 | pad | Review at real display size. |
| Favicon ICO | 32x32 | pad | Use simple art, `--pixel-art` only if intended. |
| Sprite cell | 64x64 | sprites | Shared scale and anchor across the strip. |

`crop` fills the target while removing excess edges; `--anchor` controls the retained area.
`pad` preserves aspect ratio and fills remaining space with transparency or `--background`.
`stretch` distorts aspect ratio and should be used only when explicitly appropriate.
PNG/WebP retain alpha; WebP exports are lossless. JPEG needs an explicit opaque
background when source alpha is present. ICO supports square sizes up to 256x256.

Check an artifact with `${CLAUDE_SKILL_DIR}/scripts/canvas inspect /path/to/image.png`.
It decodes pixels and reports dimensions, alpha fractions, and SHA-256.
An alpha channel alone is not proof of transparency; fully transparent pixels must exist.
Visual review still needs to catch painted checkerboards, unwanted halos or missing details.

For intentional solid-background inputs only:

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas alpha --input flat.png --output cutout.png --chroma '#00ff00' --tolerance 24
```

This removes matching color connected to the image boundary and preserves enclosed colors.
It is not semantic background removal and does not repair soft color spill or internal holes.
Choose the key from the actual image, inspect edges, and never erase a subject's own color.

## Animation timing and playback

`animate` accepts still frames in playback order with equal dimensions. Use `--duration`
for uniform milliseconds or `--durations` for one comma-separated value per frame; values
must be 20–10,000ms. These options are mutually exclusive. Use `--play-once` for a one-shot;
otherwise animation loops indefinitely. The same options apply to `sprites` previews and
manifests. Reuse the manifest's durations when exporting final frames with `animate`.

```bash
${CLAUDE_SKILL_DIR}/scripts/canvas animate --frames public/wave/frames/01.png public/wave/frames/02.png public/wave/frames/03.png public/wave/frames/04.png --durations 180,120,180,240 --play-once --output public/wave.webp
```

| Format | Alpha / palette | Use |
| --- | --- | --- |
| Animated WebP | Soft alpha, lossless encoding | Compact web animation when the consumer supports it. |
| APNG (`.png`) | Soft alpha, full-color | Full-color transparent animation; verify consumer support. |
| GIF | Canvas flattens to an explicit opaque background; 256-color palette | Compatibility deliverable on a known background. |
| PNG frames + atlas | Full alpha, no baked-in timing | Game-engine input; timing and atlas rectangles are in manifest.json. |

GIF exports share a sequence-wide palette to reduce color flicker. GIF stores timing
in 10ms units, so Canvas rounds explicitly and returns `encoded_durations_ms`; choose
multiples of 10 when exact timing matters. The encoder can merge identical neighboring
frames while preserving their hold duration. `saved_frames` reports the encoded count;
it need not equal the number of input files. Viewer behavior still needs inspection.
One-shot encoding differs by format; `--play-once` handles that distinction.

Inspect animation with a playback-capable viewer and review constituent PNGs separately.
`inspect` is intentionally a still-image command; it rejects animated files.
Do not flatten a soft-alpha asset just to make an intermediate GIF. Keep transparent
PNG/WebP/APNG masters and use the checkerboard GIF only as a review derivative.
