---
type: task
status: review
area: world
priority: high
related: ['task-401', 'task-397', 'task-583', 'task-584', 'task-535', 'task-539']
---

# task-582: Chunk load, unload and merge APIs on WorldGraph

**Filed:** 2026-09-28
**Related:** task-401, task-397

<!-- deps:start -->
**Related:** [[task-401-chunk-persistence-and-gateway-ways]], [[task-397-world-scope-hierarchy-and-projection]], [[task-583-global-scope-index-gateway-ways-and-load-before-you-move]], [[task-584-cross-chunk-ownership-rules-for-carried-items-triggers-and-delayed-events]], [[task-535-promote-a-graph-selection-into-a-new-child-scope-with-a-gateway]], [[task-539-reassign-an-area-to-a-scope-membership-only-plus-a-scope-picker-on-the-node]]
<!-- deps:end -->

## What

Give WorldGraph explicit scope/chunk load, unload and merge operations with ownership checks. load_from_dict() clears the whole graph and therefore cannot be the chunk loader; a scope must be materialised into a live graph and removed again without touching anything else.

## Acceptance

- [x] merge_scope adds or replaces nodes belonging to target scope and rejects foreign nodes.
- [x] unload_scope removes owned nodes and incident edges while leaving other scopes and scope-less nodes intact.
- [x] slice_scope exports a self-contained payload that round-trips via merge_scope.

## Implemented (2026-10-02)

`WorldGraph` (`graph.py`) now has, alongside the clearing `load_from_dict`:

- `ScopeOwnershipError` - a merge/unload that would touch a node another scope
  owns.
- `_declared_scope(node)` / `_declared_scope_dict(nd)` - a node's owner is
  `properties.world_scope_id` (areas, hand-placed) or
  `properties.generated.scope_id` (compiled/generated); a node with neither is
  scope-less and is addressed through its edges, never unloaded by a scope.
- `scope_owners()`, `nodes_owned_by(scope_id)`, `is_scope_loaded(scope_id)`.
- `merge_scope(scope_id, {nodes, edges}, replace=False)` - validates ownership
  **before any mutation**: an incoming node declaring a different scope, or an
  id already present and not owned by this scope, is refused; `replace=True`
  re-stamps this scope's own existing nodes in place. Returns
  `{scope_id, added, replaced, skipped}`.
- `unload_scope(scope_id)` - removes only the nodes this scope owns plus edges
  incident to them; another scope's nodes and scope-less nodes (characters,
  library items) survive. Returns `{scope_id, removed, edges_removed}`.
- `slice_scope(scope_id)` - a self-contained `merge_scope` payload (owned nodes
  + edges with both endpoints owned) so an unload/reload round-trips.

Cross-scope policy for carried/equipped items, triggers and delayed events is
deliberately **not** decided here - an edge with one endpoint in the unloaded
scope is dropped with it, and task-584 owns the rule.

Tests: `tests/test_world_chunks.py` (9) - merge isolation, duplicate load
refusal, replace re-stamp, foreign-owner refusal, unload isolation (scope-less
survivor + edge removal), slice round-trip, empty-scope refusal.

## Why

Partitioning large worlds into scopes requires clean graph APIs to load, unload, and slice scoped subgraphs without stranding scope-less nodes (players, unique items) or creating duplicate node collisions.

## How

Implemented load_scope, unload_scope, merge_scope, and slice_scope on WorldGraph. Enforced scope ownership guards: refusal of foreign-owned nodes unless 
eplace=True, atomic unload of owned nodes and incident edges.

## Steps to verify

1. Run world chunks test suite
   - expected: pytest tests/test_world_chunks.py passes
   - observed: 9 passed in tests/test_world_chunks.py
2. Verify scope unload isolation
   - expected: Unloading a scope does not drop characters or scope-less items
   - observed: Scope-less entities preserved across scope transitions

## Files

- graph.py
- 	ests/test_world_chunks.py
