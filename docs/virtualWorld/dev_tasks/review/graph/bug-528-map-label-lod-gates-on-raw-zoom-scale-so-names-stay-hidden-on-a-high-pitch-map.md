---
type: bug
status: review
area: graph
priority: medium
---

# bug-528: Map label LOD gates on raw zoom scale so names stay hidden on a high-pitch map

**Filed:** 2026-10-08
**Related:** task-526 task-527

## Goal

GraphNetwork._nodeLabelPolicy (static/js/graph/network-manager.ts:958-972) hides every node name once the graph exceeds graphLabelMaxNodes (400) unless network.getScale() >= graphLabelMinScale (0.6). On a compiled scope at the auto pitch (e.g. deep woods: 404 areas, 1696 nodes, 240px/cell) the fitted scale is tiny, so names need roughly 12x zoom to appear even though a single cell is already over 100px on screen; measured live, the author zoomed in on image 4 and names never showed. Gate the decision on the on-screen cell size (mapSpacing x zoom) instead of the raw network scale, so names appear as soon as a cell is readable. Regression test: a high pitch shows names at an absolute scale far below 0.6.

## Acceptance

- [x] `_nodeLabelPolicy` gates on `pitch × zoom >= graphLabelMinCellPx` (default 14px); the `graphLabelMaxNodes` / `graphLabelMinScale` count gate is gone.
- [x] Unit coverage for the cell unit in the layout-engine suite (`markFontPx`, `markCardMax`, `autoMapSpacing`).
- [ ] **Live:** names appear on zoom at an absolute scale far below 0.6. Not yet observed — the map page blocked the Playwright `evaluate` (2737-node world + 2.5MB poll). Verify on a lighter scope before closing.

**Landed 2026-10-08:** `static/js/graph/network-manager.ts` `_nodeLabelPolicy`. `graphLabelMaxNodes` / `graphLabelMinScale` are now unused config keys (left in place).
