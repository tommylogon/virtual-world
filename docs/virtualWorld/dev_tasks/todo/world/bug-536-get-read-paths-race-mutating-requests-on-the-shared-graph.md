---
type: bug
status: todo
area: world
priority: medium
---

# bug-536: GET read paths race mutating requests on the shared graph

**Filed:** 2026-10-10
**Related:** 

## What

The dev server runs threaded=True and app._vw_write_lock serializes MUTATING /api/ calls only; GETs read the live WorldGraph unlocked, so a read iterating graph.nodes / graph.edges raises 'dictionary changed size during iteration' when a concurrent write adds or removes a node or edge. Observed: /api/triggers/validate 500 in engine/trigger_validator.py (all graph iterations now snapshot to list(...)), and /api/state's to_dict rebuilds unlocked on a cache miss (now snapshotted), plus get_edges_by_type. Remaining exposure: graph.get_edges_for_source/target index rebuilds, world_scopes.project_subgraph, and other GET read paths. Decide the systemic fix: synchronize reads with writes (read lock / RW lock / a snapshot-on-read helper) or copy-on-write the world per request.

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

Intended UI home: open the same world in two browser tabs → repeatedly fetch state/validate triggers in one tab while adding/removing graph nodes in the other → inspect Network results and the visible graph.

Current availability: the card records threaded GET routes iterating the shared graph unlocked while mutating requests use the write lock, including observed 500s during mutation. A read-consistency fix is not claimed as implemented.

Live steps when available:
1. Open two tabs to one scenario. In tab A, repeatedly request `/api/state` and `/api/triggers/validate`; in tab B, repeatedly add and remove a scratch node/edge through the graph editor.
   - expected: GET responses remain successful and return internally consistent graph snapshots; no “dictionary changed size during iteration” 500 appears.
2. Inspect the browser Network panel for both read routes throughout the write loop.
   - expected: every request has a valid response; a read sees either the state before or after a complete write, not a partially-mutated graph.
3. Stop writes and refresh both tabs.
   - expected: both views converge on the same node/edge set and the server remains responsive.

This section is not a claim that the concurrent read fix is implemented today.
