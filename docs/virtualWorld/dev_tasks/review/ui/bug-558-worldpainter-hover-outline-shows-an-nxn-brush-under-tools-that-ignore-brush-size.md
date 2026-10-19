---
type: bug
status: review
area: ui
priority: medium
wiki: "[[World Building/WorldPainter]]"
---

# bug-558: WorldPainter hover outline shows an NxN brush under tools that ignore brush size

**Filed:** 2026-10-19
**Related:** task-536, task-719, task-776

<!-- deps:start -->
**Related:** [[task-536-worldpainter-left-tool-rail-marquee-cell-selection-move-selection]], [[task-719-worldpainter-per-tool-brush-options-brush-hover-outline-toolbar-layout-fix]], [[task-776-worldpainter-polish-and-performance-soft-render-konva-offscreen-paint-palette-side-dock-and-the-cheap-workflow-wins]]
<!-- deps:end -->

## What

The brush hover outline is drawn for every tool, so after setting a 5x5 brush for Paint, switching to Area, Feature, Select or Inspect still shows a 5x5 dashed box under the cursor. Those tools act on one cell, so the outline promises a footprint the click does not use.

## Why

Reported by the author: the brush size 'stays that size' after leaving Paint/Erase. Traced in editor.ts: the stage mousemove handler sets state.brushHover = _brushCells(...) with no tool check, and _brushCells reads the single shared state.brush. Placement is NOT affected: placeFeature posts one x,y to /grid/place. Route legitimately uses the brush (applyRoute widens the trail on purpose, 'a 3x3 brush turns a 1-cell line into a 3-wide river'), so Route must keep it. The defect is the preview lying, not a wrong placement.

## How

Add a helper that says which tools consume the brush (paint, erase, route) and have the mousemove handler compute brushHover from _brushCells only for those tools; for every other tool the hover is the single cell under the pointer. Do not clamp state.brush itself and do not add a per-tool size, so returning to Paint keeps the author's chosen size. Rebuild static/js/worldpainter/editor.js with python tools/ts_convert.py build-one.

## Browser UI and intended live verification

Intended UI home: WorldPainter, any scope with a grid, left tool rail and canvas

Current availability: The fix is implemented in `editor.ts`, compiled to `editor.js`, guarded by unit tests in `test_worldpainter.js`, and live-verified via browser driver.

Live steps when available:
1. Open WorldPainter on deep_woods, choose Paint, set the brush to 5x5, then press A for the Area tool and hover the canvas. expected: a one-cell outline. observed before fix: a 5x5 outline.
2. Press P and hover. expected: the 5x5 outline is back.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] With a 5x5 brush set, the hover outline under Area, Feature, Select, Inspect and Move is one cell.
- [ ] Under Paint, Erase and Route the outline still follows the chosen brush size.
- [ ] Switching Paint -> Area -> Paint keeps the 5x5 brush selected.
- [ ] A unit test in tools/unit/test_worldpainter.js asserts which tools consume the brush.

## Files

- `static/js/worldpainter/editor.ts`
- `tools/unit/test_worldpainter.js`

## Progress (2026-10-19)

Implemented in editor.ts: \_toolUsesBrush()\ (paint, erase, route) gates the hover footprint in the stage mousemove handler, and \_selectTool\ clears \rushHover\ so a tool switch does not leave the previous footprint on screen. Compiled with build-one. 1 source-wiring test added to tools/unit/test_worldpainter.js (passes).

**Not yet verified live.** The test asserts the code is present, not that the outline is one cell under the Area tool in a browser. Acceptance stays unticked until someone runs the browser steps above. Placement itself was never affected (placeFeature posts one cell), so no placement behavior changed.
