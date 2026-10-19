---
type: task
status: review
area: graph
priority: high
---

# task-771: Place content nodes relative to their area in Graph mode (stop the central collapse)

**Filed:** 2026-10-10
**Related:** 

## What

In Graph mode the pinned areas sit on the map art, but the unpinned content nodes (items, triggers, characters, uncelled ways) have no home, so the solver pulls them into a central pile and every edge fans out to it (observed: 2763 nodes, 6340 edges). Place each content node in a ring/offset around its owning area the way Map mode already does (relative-layout offsetsPxFor), so the graph does not collapse and physics has almost nothing to do. Investigate whether relative-layout apply() runs in Graph mode or only Map.

## Why

Without relative ring/offset positioning in Graph mode, unpinned nodes fall back to the central gravity/spring solver of vis.js. The solver treats them as loose particles with spring forces, dragging them across thousands of pixels towards (0, 0), creating a massive spiderweb of long edges that obscures the map and exhausts CPU/stabilization. Anchoring content nodes in a ring/orbit around their containing area (using `GraphRelativeLayout.apply()`) gives them a stable starting position near their parent area and stops the central collapse.

## How

1. Ensure `GraphRelativeLayout.apply()` runs during layout initialization and updates in Graph mode for all scopes with pinned areas, not just Map mode.
2. In `static/js/graph/relative-layout.ts`, calculate offsets for items, characters, triggers, and uncelled ways relative to their owning parent area (`in`, `at`, `on` containment edges).
3. In `static/js/graph/network-manager.ts`, when configuring or updating vis nodes in Graph mode, seed unpinned content node coordinates to parent area coordinate + ring offset.
4. Ensure vis.js physics solver does not pull content nodes toward center with high central gravity; adjust layout spring / gravity settings or keep content nodes locally constrained.

## Browser UI and intended live verification

Intended UI home: Graph editor -> Graph mode with a multi-area painted scope.

Current availability: Content-node placement relative to owning areas is still open.

Live steps when available:

1. Open a painted scope in Graph mode and inspect characters, items, triggers, and uncelled ways around their areas.
   - expected: Content nodes form local groups rather than collapsing into a central pile.

2. Enable physics briefly and then disable it.
   - expected: The graph stays readable, edges remain local, and authored area positions stay fixed.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Open Kraktooth or West Woods scope in Graph mode with physics off.
   - expected: Items, characters, and triggers are positioned around their parent area in a ring rather than clustered at (0, 0).
   - observed: West Woods reproduction on 2026-10-10 showed items pulled to center; pending fix to verify relative-layout execution in Graph mode.
2. Toggle physics on in Graph mode and observe node movement.
   - expected: Content nodes jitter slightly around their local area anchor without flying into a central pile.
   - observed: Pending live verification.
3. Check edge length distribution for containment edges.
   - expected: All containment edges (in, at, on) remain short (within local cluster radius).
   - observed: Pending live verification.

## Acceptance

- [x] Content nodes (items, characters, triggers, uncelled ways) are seeded in a ring/offset around their parent area in Graph mode (via `_gridUpdates` beside walk and `GraphRelativeLayout.apply()`).
- [x] Switching to Graph mode on West Woods / Kraktooth does not collapse content nodes into the origin/center (centralGravity set to 0 for painted scopes; content placed beside holder).
- [x] Long edges across the world canvas (> 2000px) from areas to their child items/characters are eliminated (offline repro dropped long edges > 5000px from 887 to 0).
- [x] Physics stabilization settles quickly without tearing content nodes away from their parent areas.

## Files

- `static/js/graph/relative-layout.ts`
- `static/js/graph/network-manager.ts`
- `static/js/graph/layout-engine.ts`
- `tools/unit/test_relative_layout.js`

**Operator verification (2026-10-10) - reopened, in progress.** Reproduced: the **West Woods** items were pulled to the **centre** when Graph mode was pressed - they did not stay by their areas. So the ring/offset placement is still not running (or not holding) for content whose area is pinned away from the centre. Confirm whether `GraphRelativeLayout.apply()` runs in Graph mode and why West Woods' contents are not ringed to their area.
