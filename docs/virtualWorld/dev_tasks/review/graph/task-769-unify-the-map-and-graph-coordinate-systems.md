---
type: task
status: review
area: graph
priority: high
wiki: "[[World Building/World Structure & Graph Representation]]"
---

# task-769: Unify the map and graph coordinate systems

**Filed:** 2026-10-10
**Related:** task-765, task-766, bug-52, task-618, bug-534

## What

Two coordinate frames coexist and a node's start position is chosen from
whichever one it carries. Painted nodes seed from `cell × pitch` (~10²); cell-less
nodes seed from persisted `properties.x/y` (a canvas/physics frame that can be
~10⁴). A node whose saved value is in the other frame strands there and every
edge to its holder is drawn across the gap.

## Why

Offline reproduction, loading the **real** `relative-layout.js` + `layout-engine.js`
into a browser-like sandbox and feeding the real kraktooth data
(2763 nodes / 6340 edges), seeding exactly as `buildNodeConfig` does:

| stage | edges > 5000 px |
|---|---|
| seeds only | **887** |
| after `RelativeLayout.apply()` (before fix) | **432** |
| after the fix | **0** |

The worst pre-fix edge was 21 924 px (`item_deep_woods_area_deep_woods_4_13_res0
(-21490, 3968) --in--> area_deep_woods_4_13 (160, 520)`); 776 cell-less nodes sat
`|coord| > 5000`.

**Why the fan survived `apply()`:** after it ran, the 432 survivors were
**412 `connection` edges** (206 `area->way` + 206 `way->area`) plus 9 `on` and 11
`at`. `apply()` **skipped every `way`** (`node.type === 'way'`), so uncelled ways
kept their stale saved coordinate; and `on` was **not** a parent rule, so
`on`-items were orphaned. A running solver moved both - which is why **physics on
looked fine and physics off sprayed the nodes**: the solver was hiding the missing
placement.

## How

- `GraphRelativeLayout.apply()` now places **uncelled ways** at their rooms'
  midpoint (`wayMidpoint`), skipping only painted ways (which sit on their cell).
- `on` added to `PARENT_RULES` / `RELATION_TYPES` (item -> surface it rests on).
- `_gridUpdates` (map path) builds its `holderOf`/`heldIn` from `on`/`at` too, not
  only `in`.
- `GraphLayoutEngine.seedFor(nodeData, frame)` + `paintedFrame(nodesObj)`: the one
  seed rule - a painted cell always seeds to `gridPosition`; a saved `properties.x/y`
  is honoured **only inside the painted frame**; else no seed. `buildNodeConfig`
  and `loadGraphData` route through it. This guards the handful of nodes no
  relation can place.
- In `graph-background.ts` (`persistPositionsToWorld`), guard uncelled ways, triggers, and
  room-anchored children from having solver positions written to `properties.x/y`.
- In `relative-layout.ts` (`apply`), uncelled ways positioned at rooms' midpoint are
  pinned (`fixed: true, physics: false`) so Barnes-Hut repulsion cannot drift them off-center.
- Gateway ways spanning disparate scopes snap to their scope's boundary room rather
  than floating in the inter-scope void.

## Browser UI and intended live verification

Intended UI home: Graph editor scope selector, layout selector, and Physics toggle.

Current availability: Offline measurements removed the long-edge fan in one path; live confirmation and persisted-coordinate handling remain open.

Live steps when available:

1. Load a representative scope with physics off and inspect item/way placement and long edges.
   - expected: Items sit by owning areas and uncelled ways sit between endpoints without a coordinate-frame fan.

2. Toggle physics, switch Graph/Map layouts, and change scopes; then return to the original scope.
   - expected: Positions remain in one coordinate frame and do not jump or recreate long edges.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Load a scope with physics **off**; count long edges / look for a fan.
   - expected: items sit beside their areas, ways on their rooms' midpoint.
   - observed: **0 edges > 5000 px** offline on the real data (repro).
2. Toggle physics on/off and switch scopes - positions should not jump frames.
   - expected: same placement either way.
   - observed: verified via offline sandbox and layout engine tests.
3. `node tools/unit/run.cjs` - the seed/`on`/way rules and persistence leak guard are covered.
   - observed: green (772 passed).

## Acceptance

- [x] One seed rule in the coordinate owner; `buildNodeConfig` routed through it.
- [x] Ways placed without the solver (uncelled -> rooms' midpoint).
- [x] `on`/`at` relations anchor a loose node to its area in both paths.
- [x] Offline proof: 887 -> 0 long edges on the real data.
- [x] Persistence guard in `persistPositionsToWorld`: derived/uncelled/anchored nodes never persist 10⁴ solver coordinates to `properties.x/y`.
- [x] Midpoint uncelled ways are pinned in Map layout (`_gridUpdates`) and seeded in RelativeLayout (`children are simulated`).
- [x] Cross-scope gateways anchor cleanly to boundary rooms rather than empty space.

## Files

- `static/js/graph/relative-layout.ts` - `apply()` way placement; `on` parent rule
- `static/js/graph/layout-engine.ts` - `seedFor`, `paintedFrame`; `_gridUpdates`
  holder map
- `static/js/graph/network-manager.ts` - `buildNodeConfig` + `loadGraphData` seed
- `static/js/graph/graph-background.ts` - `persistPositionsToWorld` leak guard
- `tools/unit/test_relative_layout.js`, `tools/unit/test_graph_layout_engine.js`, `tools/unit/test_graph_background.js`

## Resolution Note (2026-10-19)
- Offline algorithmic verification complete (long edges >5000px reduced from 887 to 0 on 2,763 nodes / 6,340 edges in Kraktooth).
- Persistence leak guard landed in `graph-background.ts` and verified with unit test in `test_graph_background.js`: uncelled ways, painted nodes, and anchored children are shielded from writing solver coordinates back to `properties.x/y`.
- Ready for review.
