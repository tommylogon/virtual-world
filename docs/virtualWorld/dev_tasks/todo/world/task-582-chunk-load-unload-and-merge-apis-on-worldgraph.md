---
type: task
status: todo
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
