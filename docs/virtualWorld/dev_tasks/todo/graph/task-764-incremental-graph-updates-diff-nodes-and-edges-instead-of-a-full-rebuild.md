---
type: task
status: todo
area: graph
priority: high
---

# task-764: Incremental graph updates: diff nodes and edges instead of a full rebuild

**Filed:** 2026-10-10
**Related:** 

## What

When a node or edge is added, removed, or retargeted (a character moving area changes its IN edge target), update the vis.js DataSet via nodes.update/edges.update and DataSet add/remove instead of nodes.clear() plus network.setData() rebuilding every node and edge. The structural diff feeds incremental updates so the solver eases the change instead of re-simulating the whole graph.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Graph canvas during a live state update, such as a character crossing a way or an area/edge being added or removed. The graph updates in place; the existing scope and camera remain stable.

Current availability: the current implementation is described as rebuilding the vis.js DataSet for structural changes. Incremental node/edge add, remove, and retarget operations are planned; no improvement is claimed as shipped by this card.

Live steps when available:
1. Load a scoped graph, note the loaded node count, camera position, and a pinned node position. Move one character across a way and watch the graph update.
   - expected: only the character's `in` edge target changes; the scoped node count stays fixed, the camera and pin stay in place, and the graph does not widen to the whole world.
2. Add an area and its way through the existing authoring flow, then remove them.
   - expected: the new node/edge appear and disappear in place without clearing and resetting the entire graph.
3. Compare the event/state update with the visible graph after each change.
   - expected: every graph node/edge matches `worldState.graph`; no stale edge or duplicate node remains after repeated updates.
4. Observe the browser during the structural update and inspect the graph layout.
   - expected: unaffected nodes do not visibly re-layout or jump as a side effect of the update.

This section is not a claim that planned UI exists or works today.
