---
type: task
status: inprogress
area: graph
priority: high
---

# task-766: Pin painted areas and ways in every layout (honor the coordinate)

**Filed:** 2026-10-10
**Related:** 

## What

A node placed by WorldPainter on a cell has a coordinate; honor it in Graph mode too, not only Map. Painted areas and ways should be physics false and seeded at their cell coordinate in every layout, so the solver never drags an authored placement.

## Why

TODO

## How

`GraphNetwork.buildNodeConfig` seeds a painted `cell` to a canvas position and
sets `physics: !(isNodePinned || seededFromCell)`. Extend it so the cell seed and
the pin apply in **every** layout, not only Map (`inMap`), so a WorldPainter
coordinate is honored in Graph mode too.

## Progress (2026-10-10)

Implemented and measured on a 2763-node camp: **1915 nodes pinned** (629 areas +
1286 culled/uncelled ways + 1 authored), 848 still simulating (471 items, 245
triggers, 27 characters, **105 uncelled ways**). Areas and painted ways are now
physics-off in Graph mode. Remaining: the 105 compiler-minted ways carry no
`cell`, so there is no coordinate to pin — they need a derived position
(`layout-engine` way midpoints) before they can be honored too. Visual result
needs the user's eye.

## Steps to verify

1. Open the graph on a painted world in Graph mode.
   - expected: painted areas/ways sit still at their map coordinates; only
     characters/items/triggers move.
   - observed: 1915/2763 pinned (mechanical check); visual TBC by user.

## Acceptance

- [ ] Painted areas/ways are physics-off in Graph, Map and Hierarchical.
- [ ] A pinned painted node sits at its cell coordinate, no drift.
- [ ] Characters and items still simulate.

## Files

- `static/js/graph/network-manager.ts` (`buildNodeConfig`, `isNodePinned`)
- `static/js/graph/layout-engine.ts` (`gridPosition`, `hasPaintedCoords`)

