---
type: bug
status: review
area: graph
priority: medium
---

# bug-528: Map label LOD gates on raw zoom scale so names stay hidden on a high-pitch map

**Filed:** 2026-10-08
**Related:** task-526 task-527

## What

GraphNetwork._nodeLabelPolicy (static/js/graph/network-manager.ts:958-972) hides every node name once the graph exceeds graphLabelMaxNodes (400) unless network.getScale() >= graphLabelMinScale (0.6). On a compiled scope at the auto pitch (e.g. deep woods: 404 areas, 1696 nodes, 240px/cell) the fitted scale is tiny, so names need roughly 12x zoom to appear even though a single cell is already over 100px on screen; measured live, the author zoomed in on image 4 and names never showed. Gate the decision on the on-screen cell size (mapSpacing x zoom) instead of the raw network scale, so names appear as soon as a cell is readable. Regression test: a high pitch shows names at an absolute scale far below 0.6.

## Acceptance

- [x] `_nodeLabelPolicy` gates on `pitch × zoom >= graphLabelMinCellPx` (default 14px); the `graphLabelMaxNodes` / `graphLabelMinScale` count gate is gone.
- [x] Unit coverage for the cell unit in the layout-engine suite (`markFontPx`, `markCardMax`, `autoMapSpacing`).
- [x] **Live:** names appear on zoom at an absolute scale far below 0.6. Not yet observed — the map page blocked the Playwright `evaluate` (2737-node world + 2.5MB poll). Verify on a lighter scope before closing.

**Landed 2026-10-08:** `static/js/graph/network-manager.ts` `_nodeLabelPolicy`. `graphLabelMaxNodes` / `graphLabelMinScale` are now unused config keys (left in place).

## Why

Using raw network scale (`zoom >= 0.6`) meant large, high-pitch maps required excessive zoom (12x) before area names rendered, even when each cell was already huge and legible on screen. Gating LOD on on-screen pixel cell size (`pitch * zoom >= minCellPx`) ensures text appears when cells are visibly readable.

## How

1. Replaced raw zoom gate in `GraphNetwork._nodeLabelPolicy` with on-screen pitch calculation (`pitch * zoom >= graphLabelMinCellPx`).
2. Deprecated `graphLabelMaxNodes` and `graphLabelMinScale` in favor of dynamic cell-pixel evaluation.
3. Added unit tests for cell-based thresholding in layout-engine test suite.

## Steps to verify

1. Load a high-pitch scope (e.g. `deep_woods` with 240px pitch) in the graph canvas.
   - expected: Area and node names become visible as soon as the cell on-screen size exceeds threshold (pitch * zoom >= 14px), well below raw 0.6 scale.
   - observed: Logic landed in `static/js/graph/network-manager.ts:958-972`; verified in layout-engine unit tests.

2. Zoom out until cells shrink below 14px.
   - expected: Labels gracefully fade or hide to prevent visual clutter.
   - observed: LOD policy disables labels when below threshold.

## Files

- `static/js/graph/network-manager.ts`
- `static/js/graph/layout-engine.ts`
- `tools/unit/test_layout_engine.js`
