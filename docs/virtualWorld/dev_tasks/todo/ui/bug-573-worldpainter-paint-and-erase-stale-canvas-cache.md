---
type: bug
status: todo
area: ui
priority: high
wiki: "[[World Building/World Painter & Scope Editor]]"
related: [task-540, bug-572]
---

# bug-573: WorldPainter paint and erase do not update canvas until scope is reopened

**Filed:** 2026-11-09
**Related:** task-540, bug-572

<!-- deps:start -->
**Related:** [[task-540-worldpainter-cell-inspector-hover-or-click-a-cell-to-read-what-is-on-it]], [[bug-572-worldpainter-area-picker-lost-placed-on-grid-grouping]]
<!-- deps:end -->

## What

Painting or erasing cells in WorldPainter does not visually update on the canvas. The newly painted or cleared colors only become visible after closing and reopening WorldPainter for that scope.

The underlying paint edits succeed on the server (`POST /grid/paint` or `POST /grid/paint_batch`), and the returned payload updates `ctx.state.payload.layers`. However, the rendering pipeline relies on an offscreen canvas cache:

1. `_ensurePaintCache(p)` in `static/js/worldpainter/editor.ts` renders layers onto `state.paintCache` and sets `state.paintCacheValid = true`.
2. `_drawPaint(ctx, p)` checks `_ensurePaintCache(p)`. If `state.paintCacheValid` is true, `_ensurePaintCache` returns immediately and `_drawPaint` draws `state.paintCache` onto the Konva canvas.
3. Neither `paintAt()` nor `_commitStroke()` in `static/js/worldpainter/editor-canvas.ts` ever invalidates the cache (`state.paintCacheValid = false`) or calls the existing `_patchPaintCache(p, cells)` helper (which was passed into canvas context but never invoked).
4. As a result, subsequent `softRender()` and `_redrawGrid()` calls continuously blit the stale cached canvas. Only `load(scopeId)` resets `state.paintCache = null; state.paintCacheValid = false;`, which explains why closing and reopening the scope is the only way painted or erased cells show up.

## Why

An author painting biomes, roads, or floors, or erasing unwanted cells, needs immediate visual feedback on the canvas during single clicks and drag strokes. Delaying updates until scope reopen destroys the authoring workflow.

## How

1. In `static/js/worldpainter/editor-canvas.ts`:
   - In `paintAt()`: after receiving the updated payload, call `ctx.patchPaintCache(ctx.state.payload, cells)` (or invalidate via `ctx.state.paintCacheValid = false`) before `ctx.render()`.
   - In `_commitStroke()`: call `ctx.patchPaintCache(ctx.state.payload, edits)` (or invalidate `ctx.state.paintCacheValid = false`) before `ctx.softRender()`.
   - In `_applyToSelection()`, `_nudge()`, and other cell edit handlers: ensure the cache is patched or invalidated.
2. In `static/js/worldpainter/editor.ts`:
   - Ensure `clearCell()` and any other cell-mutating helpers invalidate `state.paintCacheValid = false` or call `_patchPaintCache(p, [{x, y}])`.
   - Ensure `_patchPaintCache` handles clearing pixels on erase (`ctx.clearRect(pos.x, pos.y, 1, 1)` or redrawing the cell across remaining layers).
3. Recompile TypeScript: `python tools/ts_convert.py build`.

## Browser UI and intended live verification

Intended UI home: WorldPainter canvas tool palette -> Paint and Erase tools.

Current availability: Reproducible on `localhost:4444`. Painting or erasing cells persists to the server payload but the canvas continues to draw the stale `paintCache` until scope reload.

Live steps when available:
1. Open WorldPainter for any scope with a grid (e.g. `valerious_case` or `millwood_high_1f`).
   - expected: WorldPainter canvas loads with grid lines and existing painted layers.
2. Select the **Paint** tool in the left tool rail, pick a biome or road layer value (e.g. `Dense Forest` or `Cobblestone`), and click an unpainted cell.
   - expected: The clicked cell immediately renders with the chosen layer color on the canvas without reloading the scope.
3. Drag across several cells with the Paint tool.
   - expected: The stroke commits and all painted cells immediately display their colors upon mouse release.
4. Select the **Erase** tool and click one of the painted cells.
   - expected: The cell color immediately clears from the canvas without requiring WorldPainter to be closed and reopened.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In WorldPainter, paint a cell with a distinct biome and observe the canvas immediately.
   - expected: The cell displays the new layer color immediately.
   - observed: Canvas does not update. The cell remains visually unchanged until the editor is closed and reopened.
2. Erase the cell and observe the canvas immediately.
   - expected: The cell visually clears immediately.
   - observed: Canvas does not clear until scope reload.
3. Run the targeted tests for WorldPainter canvas rendering: `node tools/unit/run.cjs`.
   - expected: All unit tests pass.

## Acceptance

- [ ] Single cell paint immediately updates the canvas in real time.
- [ ] Stroke paint batch immediately updates the canvas on mouse release.
- [ ] Erase immediately clears cells from the canvas in real time.
- [ ] Cell modifications do not require closing and reopening the scope to become visible.

## Files

- `static/js/worldpainter/editor-canvas.ts`
- `static/js/worldpainter/editor.ts`
- `tools/unit/test_worldpainter_grid.js`
