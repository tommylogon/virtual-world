---
type: task
status: todo
area: library
priority: medium
blocked_by: [task-446]
blocks: [task-578]
---

# task-577: Authorable docs field on library nodes

**Filed:** 2026-09-28
**Related:** task-446, task-492
**Blocked by:** task-446 (id-first node identity)
**Blocks:** task-578

## Goal

Let an authored area, item, way, trigger or condition point at the documentation page
that describes it, keyed by **node id** rather than display name.

## Why this is a separate axis from task-576

`@docs` is a **module → page** link, and a module is code. A library node is a *data
instance* — this specific area, this specific item. Those are different keys, and no
existing mechanism represents the second one. "The Doors & Connections page describes
`way_4f2a`" is a fact about content, not about code.

## Why it is blocked by task-446

The key must be the node id. Today a node can be addressed by display name, and names
resolve at the boundary (task-446 is in `inprogress` and touches
`engine/serialization.py` and `virtual_world_engine.py`). A `docs:` field keyed by name
would break the moment anything is renamed — which is exactly the failure mode task-446
exists to remove. Do not build this on names.

## Design

- Optional field on the node schema, alongside the existing optional properties:
  ```json
  { "id": "way_4f2a", "name": "Cellar Door", "docs": "docs/virtualWorld/World Building/Doors & Connections.md" }
  ```
- Repo-relative path, the same form as `@docs`. One value, not a list — if a node needs
  two pages, that is a sign it is two concerns.
- Absent means "no documentation linked", which is valid and common. Not every node
  deserves a page.
- Additive: no backfill of the 505 library items, no scenario migration. Authors attach
  docs where it matters.
- Schema lives with the other registry validation in `routes/library_ops.py` (~:118-141).
  **This is a hub file — coordinate with the spine lane before editing.**

## Acceptance

- `docs` is accepted and preserved on every registry type, and survives a save/load
  round trip (covered by a test, not by inspection).
- A `docs` value that is not a string is rejected with a clear error, not coerced.
- A `docs` value pointing at a nonexistent path is **accepted at write time** and
  surfaced as a warning — task-578 is what resolves it, and an author must not be blocked
  from linking a page they are about to write.
- Keyed by id: renaming a node's display name does not break its docs link.
- The library editor exposes the field, and the field is not required.
