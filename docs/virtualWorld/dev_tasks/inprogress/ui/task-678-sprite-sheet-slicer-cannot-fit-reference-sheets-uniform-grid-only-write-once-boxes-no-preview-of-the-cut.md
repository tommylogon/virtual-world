---
type: task
status: inprogress
area: ui
priority: high
---

# task-678: Sprite sheet slicer cannot fit reference sheets: uniform grid only, write-once boxes, no preview of the cut

**Filed:** 2026-10-04
**Related:** task-445
**Status:** Implemented (in `inspector/sprite-sheet.ts`); live browser check still owed.

## What

Let the character-art sheet slicer handle real reference and expression sheets without one hand-drawn box per panel: a grid whose frame and interior dividers are draggable (frame shrinks off a title banner, dividers give mixed panel sizes), auto-detection of whitespace gutters to propose that grid, and a live thumbnail strip of the actual crops so a miscut is visible before upload.

## Why

The old slicer was a uniform rows × cols grid with write-once boxes and no
preview. Real sheets are a title banner, an outer margin, and panels of mixed
sizes (a wide full-body pose beside a column of small detail panels), and a
count describes none of that. A miscut was only visible after upload — the
"guess-then-check" dialog this card replaces.

## How

- `inspector/sprite-sheet.ts` — the frame + interior-divider model (not a
  rows/cols count): draggable frame edges (to fit the grid onto the art and off a
  banner/footer), draggable interior dividers (uneven rows/cols), "✨ Auto-fit"
  proposing the whole grid from the sheet's whitespace gutters (detection
  proposes, every value stays draggable), a live crop strip as the second view,
  and move/resize of an existing box instead of delete + redraw. "Draw boxes"
  remains the escape hatch for genuinely irregular layouts.
- `inspector/sprite-sheet-geometry.ts` — the pure slice geometry, split out
  because the canvas half cannot run in the Node unit sandbox.
- Cropping is client-side via canvas; each tile uploads through the existing
  single-image endpoint (`ApiClient.uploadNodeImage`). No server change, no
  base64 in the scenario.
- The crop strip is rebuilt on release (not on every mousemove) so re-cropping
  every tile cannot stall the tab.

## Steps to verify

1. Character inspector → Expression Pack → ✂️ Split sheet → upload a sheet with a
   title banner.
   - expected: drag the frame off the banner; interior dividers make uneven rows/cols; the crop strip updates.
   - observed: TODO
2. Click ✨ Auto-fit.
   - expected: it proposes a grid from the whitespace gutters; every proposed value stays draggable.
   - observed: TODO
3. Move / resize an existing box.
   - expected: it moves / resizes instead of needing delete + redraw.
   - observed: TODO
4. Upload the crops.
   - expected: each tile lands in its expression slot.
   - observed: TODO

## Acceptance

- [ ] Frame edges and interior dividers are draggable; Auto-fit proposes a grid from whitespace gutters and stays editable.
- [ ] A live strip previews the actual crops before upload.
- [ ] An existing box can be moved / resized (no delete + redraw).
- [ ] Slice geometry is unit-tested (`tools/unit/test_sprite_sheet_geometry.js`).
- [ ] Cropping is client-side through the existing single-image endpoint; no server change, no base64 in the scenario.
- [ ] Live browser check on a real reference sheet.

## Files

- `static/js/inspector/sprite-sheet.ts` (+ emitted `.js`)
- `static/js/inspector/sprite-sheet-geometry.ts`
- `tools/unit/test_sprite_sheet_geometry.js`
- `docs/virtualWorld/Characters/Character Images & Expression Packs.md`
