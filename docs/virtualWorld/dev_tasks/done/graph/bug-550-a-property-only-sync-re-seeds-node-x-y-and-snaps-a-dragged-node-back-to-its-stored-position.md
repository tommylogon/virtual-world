---
type: bug
status: done
area: graph
priority: high
wiki: "[[Graph System]]"
---

# bug-550: A property-only sync re-seeds node x/y and snaps a dragged node back to its stored position

**Filed:** 2026-10-12
**Related:** 

## What

On every worldState.fetch() the graph syncs in place through syncGraphData -> buildNodeConfig, which sets x/y from GraphLayoutEngine.seedFor (the node saved properties.x/y, or its painted cell x pitch). So a property-only change (a way opening, an item lighting up, an emotion) carried every changed node back to its SEED and reset a live drag. Loose-node positions are otherwise ephemeral: they are written to properties.x/y only on the dragEnd of a FROZEN node (relative-layout.ts frozenDropOps, which skips non-static and painted nodes) or by the background panel explicit Save. Landed fix: syncGraphData now deletes x/y from the update unless the node painted cell actually changed (new GraphNetwork._cellSig), so a property change can no longer move a node; a genuine cell move still repositions. Needs live verification.

## Why

TODO

## How

TODO

## Steps to verify

1. Load a map-mode scope. Drag a loose node (an item or a character) somewhere new and let it settle.
   - expected: it stays where you dropped it
   - observed: operator 2026-10-12 — it stays put
2. Cause a property change for that same node so a sync update is pushed (e.g. toggle a nearby way open/closed, light an item, or change a character emotion / state).
   - expected (fixed): the node does NOT jump back to its stored properties.x/y or its cell; only its label/colour changes in place
   - observed: operator 2026-10-12 — no snap back. The reported defect is fixed.
3. Move a painted area to a different cell (WorldPainter).
   - expected: that node DOES relocate (a real cell change must still reposition it)
   - observed: TODO — code path guarantees it (x/y are kept when _cellSig changes) and is unit-adjacent, but not clicked live
4. Sanity check the persistence path this card describes.
   - expected: dragging a frozen (physics-off) node survives a reload; dragging a physics-on node does not persist
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
