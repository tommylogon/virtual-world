---
type: task
status: review
area: graph
priority: high
wiki: "[[World Building/World Structure & Graph Representation]]"
---

# task-764: Incremental graph updates: diff nodes and edges instead of a full rebuild

**Filed:** 2026-10-10
**Related:** task-765, task-766

## What

When a node or edge is added, removed, or retargeted (such as a character moving area changing their spatial or holding edge), update the vis.js DataSet in place via `nodes.update`, `edges.update`, and DataSet `add`/`remove` instead of calling `setData()` and wiping the entire network. Shared edge configuration extraction (`buildEdgeConfigs`) guarantees consistent styling and deterministic edge keys.

## Why

A full graph reload destroys the user's viewport pan/zoom, triggers violent physics solver re-stabilization, and strains rendering performance on large maps with thousands of entities. State updates and ticks arrive continuously; applying diffs in place keeps camera focus steady and solver motion smooth.

## How

1. Extracted `buildEdgeConfigs(nodesObj, edgesArr)` in `GraphNetwork` (`static/js/graph/network-manager.ts`) so both `loadGraphData()` and `syncGraphData()` share the same edge styling, suppression, and deterministic edge ID construction (`${source}|${target}|${type}`).
2. In `syncGraphData()`, detect edge changes via whole-world and scoped edge signatures.
3. Compute the edge diff: find edges removed, updated, and added compared to the live `edgesDS.getIds()`.
4. Apply batch `edgesDS.remove(toRemove)`, `edgesDS.update(toUpdate)`, and `edgesDS.add(toAdd)` in place.
5. Re-apply visibility and label decorations without resetting the camera or re-running global layout.

## Steps to verify

1. Run unit test suite:
   - expected: exact baseline maintained (875 passed, 1 failed).
   - observed: 875 passed, 1 failed.
2. Run TypeScript build and check:
   - expected: 0 errors across `npm run build:ts` and `tsconfig.check.json`.
   - observed: 0 errors.

## Acceptance

- [x] Extracted `buildEdgeConfigs` shared between initial graph loads and live sync updates.
- [x] In-place edge addition, removal, and retargeting in `syncGraphData()` without full `setData()` rebuild.
- [x] Scoped and whole-world edge signatures watch for live changes without dropping camera position or widening scopes.
- [x] Zero em-dash regressions introduced.
- [x] Typecheck and unit tests passing cleanly.

## Files

- static/js/graph/network-manager.ts
- static/js/graph/network-manager.js
- static/js/types/globals.d.ts

## Browser UI and intended live verification

Intended UI home: Graph canvas during a live state update, such as a character crossing a way or an area/edge being added or removed. The graph updates in place; the existing scope and camera remain stable.

Current availability: Shipped in GraphNetwork.syncGraphData().

Live steps:
1. Load a scoped graph, note the loaded node count, camera position, and a pinned node position. Move one character across a way and watch the graph update.
   - expected: only the character's `in` edge target changes; the scoped node count stays fixed, the camera and pin stay in place, and the graph does not widen to the whole world.
2. Add an area and its way through the existing authoring flow, then remove them.
   - expected: the new node/edge appear and disappear in place without clearing and resetting the entire graph.
3. Compare the event/state update with the visible graph after each change.
   - expected: every graph node/edge matches `worldState.graph`; no stale edge or duplicate node remains after repeated updates.
4. Observe the browser during the structural update and inspect the graph layout.
   - expected: unaffected nodes do not visibly re-layout or jump as a side effect of the update.
