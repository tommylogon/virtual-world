---
type: task
status: inprogress
area: graph
priority: high
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

## Why — measured

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
**412 `connection` edges** (206 `area→way` + 206 `way→area`) plus 9 `on` and 11
`at`. `apply()` **skipped every `way`** (`node.type === 'way'`), so uncelled ways
kept their stale saved coordinate; and `on` was **not** a parent rule, so
`on`-items were orphaned. A running solver moved both — which is why **physics on
looked fine and physics off sprayed the nodes**: the solver was hiding the missing
placement.

## How

- `GraphRelativeLayout.apply()` now places **uncelled ways** at their rooms'
  midpoint (`wayMidpoint`), skipping only painted ways (which sit on their cell).
- `on` added to `PARENT_RULES` / `RELATION_TYPES` (item → surface it rests on).
- `_gridUpdates` (map path) builds its `holderOf`/`heldIn` from `on`/`at` too, not
  only `in`.
- `GraphLayoutEngine.seedFor(nodeData, frame)` + `paintedFrame(nodesObj)`: the one
  seed rule — a painted cell always seeds to `gridPosition`; a saved `properties.x/y`
  is honoured **only inside the painted frame**; else no seed. `buildNodeConfig`
  and `loadGraphData` route through it. This guards the handful of nodes no
  relation can place.

## Steps to verify

1. Load a scope with physics **off**; count long edges / look for a fan.
   - expected: items sit beside their areas, ways on their rooms' midpoint.
   - observed: **0 edges > 5000 px** offline on the real data (repro). Live load
     not yet driven (page blocks `browser_evaluate`).
2. Toggle physics on/off and switch scopes — positions should not jump frames.
   - expected: same placement either way.
   - observed: pending live.
3. `node tools/unit/run.cjs` — the seed/`on`/way rules are covered.
   - observed: green (666 passed).

## Acceptance

- [x] One seed rule in the coordinate owner; `buildNodeConfig` routed through it.
- [x] Ways placed without the solver (uncelled → rooms' midpoint).
- [x] `on`/`at` relations anchor a loose node to its area in both paths.
- [x] Offline proof: 887 → 0 long edges on the real data.
- [ ] Live confirmation (reload a scope with physics off, no fan).
- [ ] The **persistence** side is still open: something writes 10⁴-scale physics
      coordinates into `properties.x/y` (bug-52's creep). Seeding no longer trusts
      an out-of-frame value, but the write should stop too.

## Files

- `static/js/graph/relative-layout.ts` — `apply()` way placement; `on` parent rule
- `static/js/graph/layout-engine.ts` — `seedFor`, `paintedFrame`; `_gridUpdates`
  holder map
- `static/js/graph/network-manager.ts` — `buildNodeConfig` + `loadGraphData` seed
- `tools/unit/test_relative_layout.js`, `tools/unit/test_graph_layout_engine.js`

## Repro

`C:\Users\Tommy\AppData\Local\Temp\kilo\repro2.js` (temporary) — loads the real
modules, seeds from `data`, runs `apply()`, prints long-edge counts. Delete when
the fix is confirmed live.

## Why

TODO
