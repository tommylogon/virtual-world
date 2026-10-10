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
