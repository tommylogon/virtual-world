---
type: task
status: todo
area: world
priority: medium
---

# task-528: Assign selected areas to a scope / promote a selection to a placed feature

**Filed:** 2026-09-26
**Related:** task-496 task-397 task-378

## Goal

From the graph canvas bulk selection (task-378), let the author say what a set of area nodes belongs to: (a) assign them to an existing scope (set world_scope_id + fix the scope area_ids), or (b) promote the selection into a new child scope and place it as a feature on a parent cell (so it becomes a walkable sub-level with a gateway). This is the reverse of the compiler's cell->area mapping and closes the 'I placed these by hand, now make them a zone' gap. Must decide: hand-authored-only vs generated areas (moving a generated area's scope means the source scope's regenerate would re-create it - mark the source baked, or forbid it); how placements/gateways/entry areas update; and that it is one undoable op. Compiler ownership of world_scope_id stays single-source (engine/world_scopes.py, no name keys).

## Acceptance

- TODO
