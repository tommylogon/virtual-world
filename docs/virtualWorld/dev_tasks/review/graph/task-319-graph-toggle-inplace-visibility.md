# Task 319 — Graph toggles/filters apply visibility in place (no full reload)

**Status**: In Review — implemented 2026-08-20

## Problem

Two related graph editor bugs:

1. **Revealed items lost their edges.** When items were hidden and you clicked a
   character, the item nodes appeared but the edges connecting them to the character
   did not. The old code only built edges whose endpoints passed the filter *at load
   time*, so edges to items that were later revealed on click never existed in the
   dataset.

2. **Every toggle/filter triggered a full graph reload.** `toggleItems`,
   `toggleInhabitedAreas`, `toggleTriggers`, `setFloorFilter`, `revealAreasForWay`,
   `hideRevealedAreas`, and search all cleared `_lastSig` and called `loadGraphData()`,
   which rebuilt the entire vis.js dataset via `network.setData()`. That caused zoom/pan
   loss, physics restart, jitter, and lag — especially bad in large worlds.

## Fix

Separate **data loading** from **visibility filtering**:

- `loadGraphData()` now builds **every** node and **every** edge into the vis.js dataset
  once (only on actual graph-structure changes). Filtering no longer drops nodes/edges at
  build time.
- A new `applyVisibility()` method computes the set of currently-visible node ids
  (`_computeVisibleNodeIds()`) and applies `hidden: true/false` to nodes and edges in
  place via `dataset.update()`. An edge is visible only when **both** its endpoints are
  visible — which automatically makes edges to revealed items appear once the item is
  revealed.
- Toggles, the floor filter, area/way reveal, and search now just update state and call
  `applyVisibility()` — no `setData()`, so zoom/pan and physics are preserved.
- Search now **hides** (via `hidden: true`) non-matching nodes and the edges whose
  endpoints don't match, instead of just fading them with `opacity: 0.0`.
- Search now **reveals matches** even when they'd otherwise be hidden by a spatial
  filter — a matching node is surfaced regardless of whether its area is inhabited or
  its item type is hidden. Its direct connections (nodes one hop away over any edge)
  come into view too, so the matching node's **edges show** ("edges if applicable").
  Search overrides the inhabited/floor/items/trigger filters while the query is active;
  clearing the query restores the normal filter view.
- Search now **fits the camera to the match cluster** (`_fitToSearchMatches`). Hidden
  nodes keep their stale baked positions (they're excluded from the physics solver
  while hidden), so without this the revealed results could appear scattered and far
  from center. The fit frames the matched nodes + their one-hop neighbors so the
  results are visible and centered.
- Revealed search nodes now **pull together** via `_kickClusterPhysics()`: after a
  search reveal, the solver gets a bounded `stabilize(80)` kick so the freshly-unhidden
  nodes re-join the simulation and pull toward their connections. Because only the
  visible match cluster is non-hidden, only those nodes participate — no restructuring
  of the whole world. Physics state is preserved (re-disabled if it was off).

Also fixed: `loadGraphData()` was resetting `_revealedItemIds` to `new Set()` while the
rest of the code expects a `Map` (reveal/cleanup iterated `.values()` as child sets).

## Files changed

- `static/js/graph/projector.js` (new): the pure visibility projection —
  `computeVisibleNodeIds()`, `edgeVisible()`, `applyVisibility()`, `_viewState()`.
  Everything below that had to do with "what should be visible" now lives here
  (unit-testable, no vis.js).
- `static/js/graph/overlays.js` (new): the 5 ambient overlays + color maps +
  change-cached `computeAmbientLight()`. Extracted as part of the wider modularization
  (see task-314); `network-manager.js` delegates the leaf apply fns to it.
- `static/js/graph/network-manager.js`:
  - `loadGraphData()` — build all nodes+edges; call `applyVisibility()` after `setData()`.
  - `_computeVisibleNodeIds()` / `applyVisibility()` — thin delegates to `GraphProjector`.
  - `revealItemsForNode` / `hideRevealedItems` — mutate `_revealedItemIds` + call
    `applyVisibility()` instead of `dataset.add()/remove()`.
  - `toggleItems` / `toggleInhabitedAreas` / `toggleTriggers` / `revealAreasForWay` /
    `hideRevealedAreas` — call `applyVisibility()` instead of `loadGraphData()`.
  - `applyFilter(query)` — store query + `applyVisibility()` (hides non-matches);
    debounced settle (fit + physics kick) via `_fitToSearchMatches` / `_kickClusterPhysics`.
- `static/js/graph-manager.js`: `setFloorFilter()` calls `applyVisibility()`.
- `templates/index.html`: added `<script>` tags for `projector.js` + `overlays.js`
  before `network-manager.js`.
- `graph/event-handlers.js`: unchanged (already wires way/empty-click reveal).

## Verification

- `node --check static/js/graph/network-manager.js` — OK
- `node --check static/js/graph/projector.js` — OK
- `node --check static/js/graph/overlays.js` — OK
- `node --check static/js/graph-manager.js` — OK
- `node tools/test_inspector.cjs` — all pass (incl. "Graph canvas responds to click",
  "Inspecting an item node works", "Trigger nodes can be found and inspected")
- `node tools/test_ui.cjs` — 24/25; the 1 failure is "Toggle physics on/off:
  document is not defined", which is a pre-existing test-harness issue in `togglePhysics`
  (untouched by this refactor). Graph canvas, context menu, node click, and item inspect
  all pass.
- Search-reveal behaviour re-checked after adding the match-reveal change — inspector
  tests still pass.
- Re-verified after the modular split (projector/overlays extraction) — same results.
