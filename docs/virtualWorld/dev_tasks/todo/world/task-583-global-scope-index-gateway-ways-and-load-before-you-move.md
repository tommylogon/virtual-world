---
type: task
status: todo
area: world
priority: high
---

# task-583: Global scope index, gateway ways and load-before-you-move

**Filed:** 2026-09-28
**Related:** task-401, task-582

## Goal

Keep a small global index outside any chunk: scope ids, area ownership, character and unique-item location, boundary ways, and scheduled work. Gateway ways name a remote target_area_id and target_scope_id, and the movement system loads the destination scope before it resolves the way. Replace the global node and edge scans that make loaded-chunk support a claim rather than a fact.

## Acceptance

- TODO
