---
type: task
status: review
area: world
priority: high
---

# task-582: Chunk load, unload and merge APIs on WorldGraph

**Filed:** 2026-09-28
**Related:** task-401, task-397

## Goal

Give WorldGraph explicit scope/chunk load, unload and merge operations with ownership checks. load_from_dict() clears the whole graph and therefore cannot be the chunk loader; a scope must be materialised into a live graph and removed again without touching anything else.

## Acceptance

- TODO

## Implemented (2026-10-02)

`WorldGraph` (`graph.py`) now has, alongside the clearing `load_from_dict`:

- `ScopeOwnershipError` — a merge/unload that would touch a node another scope
  owns.
- `_declared_scope(node)` / `_declared_scope_dict(nd)` — a node's owner is
  `properties.world_scope_id` (areas, hand-placed) or
  `properties.generated.scope_id` (compiled/generated); a node with neither is
  scope-less and is addressed through its edges, never unloaded by a scope.
- `scope_owners()`, `nodes_owned_by(scope_id)`, `is_scope_loaded(scope_id)`.
- `merge_scope(scope_id, {nodes, edges}, replace=False)` — validates ownership
  **before any mutation**: an incoming node declaring a different scope, or an
  id already present and not owned by this scope, is refused; `replace=True`
  re-stamps this scope's own existing nodes in place. Returns
  `{scope_id, added, replaced, skipped}`.
- `unload_scope(scope_id)` — removes only the nodes this scope owns plus edges
  incident to them; another scope's nodes and scope-less nodes (characters,
  library items) survive. Returns `{scope_id, removed, edges_removed}`.
- `slice_scope(scope_id)` — a self-contained `merge_scope` payload (owned nodes
  + edges with both endpoints owned) so an unload/reload round-trips.

Cross-scope policy for carried/equipped items, triggers and delayed events is
deliberately **not** decided here — an edge with one endpoint in the unloaded
scope is dropped with it, and task-584 owns the rule.

Tests: `tests/test_world_chunks.py` (9) — merge isolation, duplicate load
refusal, replace re-stamp, foreign-owner refusal, unload isolation (scope-less
survivor + edge removal), slice round-trip, empty-scope refusal.
