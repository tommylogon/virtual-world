---
type: task
status: todo
area: ui
priority: high
wiki: "[[World Building/World Painter & Scope Editor]]"
related: [task-540, bug-572, bug-573]
---

# task-931: WorldPainter origin-anchored grid resolution scaling, 4-way expansion, and live preview

**Filed:** 2026-11-09
**Related:** task-540, bug-572, bug-573

<!-- deps:start -->
**Related:** [[task-540-worldpainter-cell-inspector-hover-or-click-a-cell-to-read-what-is-on-it]], [[bug-572-worldpainter-area-picker-lost-placed-on-grid-grouping]], [[bug-573-worldpainter-paint-and-erase-stale-canvas-cache]]
<!-- deps:end -->

## What

Overhaul the WorldPainter grid adjustment architecture to replace rigid top-left bounding box truncation with an **origin-anchored resolution scaling system**, 4-way margin expansion, and a live grid overlay preview before committing:

1. **Origin-Anchored Resolution Scaling**:
   - The author selects an anchor landmark cell `(x0, y0)` (or defaults to grid center/top-left).
   - Adjusting cell size or grid density scales all placed area cells proportionally:
     `x' = x0 + round((x - x0) * s)`
     `y' = y0 + round((y - y0) * s)`
   - Relative spatial distances between placed areas are preserved, keeping them visually aligned with landmarks on the underlying reference map image instead of sliding across the art.
2. **4-Way Margin Expansion (West and North Handles)**:
   - Add West (`w`) and North (`n`) edge handles to `gridHandlePoints()` in `static/js/worldpainter/grid-model.ts`.
   - Dragging the West or North handle adds columns or rows on the left/top by `+dx` or `+dy`.
   - Placed cells and painted layers offset by `(x + dx, y + dy)` so their visual screen positions relative to the background map image do not move.
3. **Restore the Cell-Size Handle on Materialized Scopes**:
   - In `editor-handles.ts: _cellCornerHandlePoint()`, remove the check `if (p.scope.state === 'materialized') return null;`.
   - Keep the green cell-size adjust handle available for tuning cell density even after the scope has been compiled once.
4. **Live Grid Ghost Preview**:
   - When adjusting grid dimensions via dialog inputs or handle dragging, display a live semi-transparent grid overlay preview showing the new cell density, boundary, and projected cell positions before the author commits the change.

## Why

Currently, adjusting grid size in WorldPainter only pulls the East and South edges, locking `(0, 0)` to the top-left corner. Changing grid dimensions leaves cell coordinates static while scaling the reference image, causing placed areas to desynchronize from their map landmarks or get pushed into the dark void outside the border. Furthermore, authors have no live preview of the new grid before committing, making resolution calibration guesswork.

## How

1. In `static/js/worldpainter/grid-model.ts`:
   - Extend `gridHandlePoints()` to provide `nw`, `n`, `ne`, `w`, `e`, `sw`, `s`, `se` handle coordinates.
   - Implement `scaleGridWithAnchor(payload, anchorCell, scaleFactor)` to re-index placed areas, features, and layer cells relative to the anchor.
   - Implement `expandGridMargins(payload, { north, south, east, west })` to adjust dimensions and offset cell coordinates.
2. In `static/js/worldpainter/editor-handles.ts`:
   - Remove `if (p.scope.state === 'materialized') return null;` in `_cellCornerHandlePoint()`.
   - Update `_gridMouseDown`, `_gridDragTo`, and `_gridMouseUp` to handle West and North drag operations.
   - Render a live ghost grid preview during handle dragging and dialog input tuning.
3. In `static/js/worldpainter/editor-dialogs.ts`:
   - In `openGridDialog()`, add resolution scaling controls with anchor selection and a live canvas preview.
4. In `routes/world_grid_ops.py` and `engine/world_grid.py`:
   - Add support in `POST /grid` for margin expansion offsets (`offset_x`, `offset_y`) and anchor scaling so the server preserves cell data correctly.

## Browser UI and intended live verification

Intended UI home: WorldPainter editor canvas -> Adjust Grid handles (`Adjust` toggle in toolbar) and Grid Dimensions Dialog (`Dimensions` button in HUD).

Current availability: Prototype simulated in `grid_resolution_simulator.html` and architecture analyzed in `worldpainter_grid_resolution_and_anchoring.md`. Live editor currently supports only South/East resizing and has no live preview or anchor scaling.

Live steps when available:
1. Open WorldPainter on a scenario with placed areas (e.g. `valerious_case` outdoor map or `millwood_high_1f`).
   - expected: Canvas loads with reference image and grid overlay.
2. Toggle the **Adjust** button in the toolbar.
   - expected: Resize handles appear around all 4 edges (North, South, East, West) and corners, including the green cell-corner handle even on materialized scopes.
3. Click an area cell (e.g. The House) to designate it as the Origin Anchor.
   - expected: Visual anchor badge or crosshair highlights the selected anchor cell.
4. Drag the green cell-size handle or adjust resolution density slider.
   - expected: A live ghost grid preview overlays the canvas; placed areas scale outward/inward from the anchor, maintaining their visual alignment over map landmarks.
5. Drag the West handle to the left by 3 cells and commit.
   - expected: 3 new columns appear on the left; all placed areas stay on their exact visual map landmarks with coordinates shifted by `x + 3`.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In WorldPainter, test West and North handle availability in Adjust mode.
   - expected: Handles exist on all 4 borders and allow pulling margins in all directions.
   - observed: TODO
2. Scale grid density with an anchor cell selected and confirm area positions relative to reference image.
   - expected: Areas stay pinned to map art; no areas pushed into dark void.
   - observed: TODO
3. Open a materialized scope and check the green cell-corner handle.
   - expected: Green handle is visible and interactive.
   - observed: TODO
4. Run targeted unit tests: `node tools/unit/run.cjs` and `pytest tests/test_world_grid.py`.
   - expected: All tests pass.
   - observed: TODO

## Acceptance

- [ ] WorldPainter Adjust mode provides 4-way resize handles (North, South, East, West) allowing margin expansion in any direction.
- [ ] Origin-anchored resolution scaling keeps placed areas aligned with reference image landmarks when cell density changes.
- [ ] Green cell-size handle remains accessible on materialized scopes.
- [ ] Live ghost grid preview renders during handle drag or dialog adjustment before commit.
- [ ] Expanding margins westward or northward automatically offsets cell coordinates without moving them visually.

## Files

- `static/js/worldpainter/grid-model.ts`
- `static/js/worldpainter/editor-handles.ts`
- `static/js/worldpainter/editor-dialogs.ts`
- `engine/world_grid.py`
- `routes/world_grid_ops.py`
- `tools/unit/test_worldpainter_grid.js`
