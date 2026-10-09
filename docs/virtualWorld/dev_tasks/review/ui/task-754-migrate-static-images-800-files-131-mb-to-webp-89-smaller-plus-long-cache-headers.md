---
type: task
status: review
area: ui
priority: high
---

# task-754: Migrate static images (800 files, 131 MB) to WebP: 89% smaller, plus long-cache headers

**Filed:** 2026-10-09
**Related:** bug-531 (image decode stalls the UI), task-753 (/api/state build time)

## Goal

`static/images` is 131.5 MB across 800 files, dominated by PNGs that compress
poorly: character expression portraits (~90–300 KB each at 384×335, 30–40 per
character) and photographic backgrounds (up to 4.3 MB at 1536×1024). Moving to
WebP cuts this by 89% and, because smaller images decode faster, also reduces
the main-thread stall in bug-531.

Measured with `tools/optimize_images.py` (dry run, quality 82):

```
800 image(s): 134,691 KB -> 14,686 KB  (89% smaller)
```

- Portrait `player_Lyrie-profile-happy-*.png`: 304 KB → 25 KB.
- Background `raven river.webp` (1536×1024): 4359 KB → 617 KB; at half-size, 194 KB.
- PNG-only re-encoding barely helps (223 KB) — the format is the problem, not the
  settings.

Two parts. **Cache headers are already done** (see below); the conversion is not.

### Done (2026-10-09)

- `app.py` `after_request` now sets `Cache-Control: public, max-age=31536000,
  immutable` for `/static/images/*`. Previously Flask's default `no-cache` made
  the browser revalidate all ~780 node images on every refresh. JS/CSS keep
  `no-cache` so dev edits still pick up. Needs a server restart to take effect.

### Not done — the conversion

`tools/optimize_images.py` (added, dry-run by default) converts and can rewrite
references. To apply: `python tools/optimize_images.py --apply --update-refs
--delete-originals`. It rewrites the ~808 literal `images/nodes/<name>.<ext>`
paths in `data/**/*.json` + `engine/**` + `static/js/**` to the `.webp` names.

## Resolution (2026-10-09)

- **Conversion applied:** `python tools/optimize_images.py --apply --update-refs --delete-originals`.
  `static/images` is now **800 WebP, 0 raster, 14.3 MB** (was 800 files / 131.5 MB).
  References rewritten across `data/**`, `saves/**`, `world_template.json`,
  `.live_state.json`, `engine/**`, `static/js/**`, `tests/**`, `docs/**`.
- **Cache headers** in `app.py` `after_request`; reloaded and verified live.
- **Generated images go forward as WebP:** the sprite-sheet slicer now encodes
  `image/webp` (PNG fallback), so expression packs stop regressing to PNG.

## Acceptance

- [x] `static/images` reduced to ~14.3 MB (was 131.5 MB), recorded before/after.
- [x] All image references resolve after conversion; save + library load cleanly.
- [x] Running server reloaded so in-memory paths match disk.
- [x] Cache headers verified live; JS/CSS still revalidate (`no-cache`).
- [x] Generated images (sprite-sheet expression packs) are written as WebP going forward.
- [ ] Direct user uploads (`InspectorHelpers` upload paths) are stored as uploaded — a PNG
      stays a PNG. Re-encoding arbitrary uploads is a deliberate follow-up, not done here.
- [x] `tools/optimize_images.py` stays dry-run by default.
