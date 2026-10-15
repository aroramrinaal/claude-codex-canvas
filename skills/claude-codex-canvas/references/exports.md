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
