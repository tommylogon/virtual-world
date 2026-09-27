---
type: task
status: todo
area: world
priority: medium
---

# task-535: Promote a graph selection into a new child scope with a gateway

**Filed:** 2026-09-27
**Related:** task-528 task-495 task-397

## Goal

The deferred half of task-528: take a selection of area nodes and make them a NEW child scope, placed on a cell of a parent scope's painted grid, with a gateway way and an entry area so it is walkable. Needs (a) a public helper to create a child scope record from existing area nodes (nothing in engine/ does this today - handle_create_scope only makes an empty record), (b) a gateway whose provenance is NOT the parent scope's, because world_compile._gateway is private and stamps properties.generated.scope_id = parent, which would make ungenerate(parent) delete the hand-authored gateway, and (c) entry_area_id/entry_area_name bookkeeping so the scope has an entry point. Placement of an EXISTING area onto a cell (task-528) is done; this is about creating a new scope out of a selection.

## Acceptance

- TODO
