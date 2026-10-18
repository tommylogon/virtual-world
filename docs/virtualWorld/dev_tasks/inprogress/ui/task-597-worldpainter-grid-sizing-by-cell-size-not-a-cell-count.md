---
type: task
status: inprogress
area: ui
priority: medium
---

# task-597: WorldPainter grid sizing by cell size (px/cell), not by cell count

**Filed:** 2026-09-30
**Reworked:** 2026-10-11 - sizing moves from a cell *count* to a cell *size* (`px / cell`).
**Reworked:** 2026-10-18 - continuous image-bounded cell-size preview (`px / cell` slider + draggable cell-corner handle) with snap-to-closest-grid on drop.
**Related:** task-523, task-596, task-774

## What

Frame a scope's grid by the **size of a cell**, not by a `width × height` count.
A per-scope cell-size control (the `px / cell` slider in the reference HUD, plus a
draggable **cell-corner handle** on cell `(1,1)` in `✥ grid` adjust mode) lets the
author continuously grow or shrink cells **inside the fixed borders of the
background reference image**, and when released (dropped), snaps to the closest
valid `w × h` grid (`w = round(imgW / pxPerCell)`, `h = round(imgH / pxPerCell)`).

The count becomes an **output**, not an input: `20×13 · 1 cell ≈ 77px`.

This reworks the first pass on this card:
1. **Background image stays stationary on screen:** pulling the slider or dragging
   the cell-corner handle never resizes or jumps the background reference image in
   the viewport.
2. **Cells grow/shrink continuously inside the background image borders:** while
   dragging, cells are drawn at exact `pxPerCell × pxPerCell` image-pixel scale,
   strictly clipped and bounded by the four edges of the reference image (never
   overhanging into empty space outside the image when `round(imgW / px)` and
   `round(imgH / px)` have a slightly different aspect ratio).
3. **Snap on drop:** releasing the slider or the cell-corner handle commits the
   closest whole-cell grid `{w, h}` and preserves the reference image's screen
   position.

## Why

The grid is the scope's coordinate space, and one painted cell compiles to one
area (task-496). Previously:

- **Typing `w` / `h`** - the number you enter is a *count*, the **inverse** of
  cell size: bigger cells mean a *smaller* number. You guess, hit `▦ match`,
  look, and re-guess.
- **Dragging E/S/SE frame handles** - the origin is pinned at `(0,0)`, so resizing
  the outer frame moves the grid borders away from the background image instead of
  subdividing the image itself.
- **First pass of the `px / cell` slider** - drew `preview.w * CELL` by
  `preview.h * CELL` while leaving the reference image at `p.grid.w * CELL` (so
  the grid detached from the art), and when integer rounding produced a `4×1`
  grid on a `3:1` image (`400px/cell` on `1536×513`), the grid frame stuck out
  past the left and right borders of the background image.

What an author actually wants when sizing a grid over a map image is to **keep the
background image fixed**, grab a cell corner (or pull the `px / cell` slider) to
watch the square cells grow or shrink inside the image's borders until a cell
matches the zones on the art ("one cell is about a clearing"), and let go to snap
to the closest grid count.

## How

- **Controls:**
  1. Per-scope `px / cell` slider in the reference HUD (`imgW / w`).
  2. Draggable **cell-corner handle** at the bottom-right corner of cell `(0,0)`
     (i.e. `(1,1)` in cell coordinates) when `✥ grid` adjust mode is active on a
     scope with a reference image: dragging that corner toward or away from
     `(0,0)` sizes that cell directly under the cursor (`pxPerCell`), previews the
     continuous cell lattice across the whole reference image, and snaps to the
     closest `{w, h}` grid on mouse-up.
- **Continuous image-bounded preview while dragging:**
  - The reference image screen rect stays anchored in place (`_anchorStageToRefScreen`).
  - While `state.cellSizePreview` is active (`{w, h, pxPerCell}`), the reference
    image occupies `(0, 0, imgW / pxPerCell, imgH / pxPerCell)` in cell units (or
    its scaled custom `reference.rect`), and the preview lattice draws square
    `CELL × CELL` cells across that reference rect, **clipped to the reference
    image borders** so the grid never overhangs outside the background image.
  - On release (`change` / `mouseup`), the preview snaps to the integer `{w, h}`
    from `gridForCellSize(imgW, imgH, pxPerCell)` and commits via `_commitGridSize`.
- **Viewport fit (`_fitGrid`):**
  - Raise `MAX_SCALE` from `6` to `20` and fit to `0.88` of the stage viewport
    instead of capping `_fitGrid` at `1.5`, so coarse world grids (`6×2`, `4×1`)
    fill the canvas instead of rendering as a tiny 198px postage stamp.
- **Lock once generated:** disabled when `p.scope.state === 'materialized'`.
- **Stranded-cell warning and highlight:** kept via `strandedCells` /
  `strandedCount` and `_commitGridSize`.

## Browser UI and intended live verification

Intended UI home: Build -> WorldPainter -> grid controls for a scope with a reference image.

Current availability: in progress; being live-verified in a headed Playwright browser on `world` (`kraktooth world map.webp`, `1536×513`) and `raven_river` (`1536×1024`).

Live steps when available:

1. Open a scope with a reference image (`world`) and pull the `px / cell` slider across its range (`35px` to `400px`).
   - expected: The background image stays fixed in size and position on screen; cells grow and shrink continuously inside the borders of the background image without overhanging past the image edges; releasing snaps to the closest `w × h` grid.
2. Enable `✥ grid` adjust mode and drag the cell-corner handle on cell `(0,0)`.
   - expected: Dragging the corner of the cell grows or shrinks the cell under the cursor, scales the whole cell lattice inside the background image borders live, and snaps to the closest `w × h` grid on mouse-up.

## Steps to verify

1. Open an ungenerated scope with a reference image (`world`, `1536×513`); move the `px / cell` slider.
   - expected: the background image stays stationary on screen; the cells grow or shrink inside the borders of the background image with zero overhang outside the image; releasing commits the closest `w × h` grid.
   - observed: pending final headed browser verification after continuous image-bounded clipping + cell-corner handle land.
2. Toggle `✥ grid` adjust mode and drag the cell `(1,1)` corner handle.
   - expected: dragging the cell corner resizes cells live inside the background image borders and commits the closest `{w, h}` grid on release.
   - observed: pending live verification.
3. Paint a few cells, then shrink the grid via slider or cell-corner handle.
   - expected: `strandedCount` warning is shown before anything is lost; confirming drops out-of-bounds cells, declining restores the grid and view cleanly.
   - observed: verified on `raven_river` (declining restores original grid and view).
4. Generate the scope, then return to the control.
   - expected: the cell-size control is disabled once materialized.
   - observed: verified on materialized scope (`disabled: true`).

## Acceptance

- [x] A per-scope `px / cell` control sizes the grid; `w` / `h` are derived from the reference image's natural size, aspect locked, the count shown as a readout.
- [ ] Pulling the `px / cell` slider keeps the background image stationary on screen and grows/shrinks cells continuously inside the borders of the background image (no overhang outside the image), snapping to `{w, h}` on release.
- [ ] In `✥ grid` adjust mode, dragging the cell-corner handle at `(1,1)` grows/shrinks the cell under the cursor and snaps to the closest `{w, h}` grid on drop.
- [x] The control is available while the scope is ungenerated and disabled once generated.
- [x] If the grid is painted, a resize shows the prune count first and highlights the cells a shrink would drop, before commit.
- [x] Screen view zoom remains independent and unaffected (`_fitGrid` fills the viewport without the old `1.5` scale ceiling).
- [ ] The unit -> `w/h` maths and cell-corner drag are unit-tested; live headed browser check on `world` (`kraktooth world map.webp`).

## Files

- `static/js/worldpainter/editor.ts` - the HUD slider, `_anchorStageToRefScreen`, continuous image-bounded preview in `_drawGridLines`, cell-corner handle in `_drawGridHandles` / `_gridHit` / `_gridDragTo` / `_gridMouseUp`, `_fitGrid`.
- `static/js/worldpainter/grid-model.ts` - `gridForCellSize`, `cellSizeForGrid`, `cellSizeRange`, `gridHandlePoints`.
- `tools/unit/test_worldpainter.js` - unit tests for `px / cell` derivation and stage anchoring.
- `engine/world_grid.py`, `routes/world_grid_ops.py` - the grid-set route keeps its `{w, h}` shape (the px unit is derived client-side).

