---
type: task
status: review
area: ui
priority: low
wiki: "[[World Building/WorldPainter]]"
---

# task-879: WorldPainter: Alt+click samples the layer value under the cursor into the brush

**Filed:** 2026-10-19
**Related:** task-776

<!-- deps:start -->
**Related:** [[task-776-worldpainter-polish-and-performance-soft-render-konva-offscreen-paint-palette-side-dock-and-the-cheap-workflow-wins]]
<!-- deps:end -->

## What

Holding Alt and clicking a painted cell sets the active layer's value to whatever is on that cell, so the author can keep painting with a tile they see without hunting for it in the palette.

## Why

Searched editor.ts for altKey, eyedrop and sample: 0 matches, so no sampler exists. The Inspect tool (I) reads a cell but never feeds the brush. The palette has 106 biome tiles across up to 26 categories, so finding a tile you can already see is the slow part of extending a region.

## How

In the canvas pointer handler, when altKey is held on mousedown over a painted cell, read the value from the payload layer map for state.layer using GM().cellValue, set state.value, and render. Do not start a stroke. If the cell has no value on the active layer, say so in the status line. Add a line to the Paint tool hint.

## Browser UI and intended live verification

Intended UI home: WorldPainter canvas, Paint tool

Current availability: Not built; no sampler exists today.

Live steps when available:
1. Paint two different biomes, select one, then Alt+click a cell of the other. expected: the value picker swatch changes to that biome and no cell changes.

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

- [ ] Alt+click on a cell painted dense_forest on the biome layer makes dense_forest the active value.
- [ ] Alt+click on an empty cell leaves the value unchanged and says why in the status line.
- [ ] No paint request is sent by an Alt+click.

## Files

- `static/js/worldpainter/editor.ts`
- `tools/unit/test_worldpainter.js`
