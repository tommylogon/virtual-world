---
type: task
status: todo
area: refactor
priority: high
---

# task-581: Stable area ids and one authoritative location for characters and items

**Filed:** 2026-09-28
**Related:** task-401, task-446

## Goal

Replace the display-name current_area convention with stable area ids, and name exactly one authoritative location record per character and per unique item, so a duplicated human-readable area name can never split an entity's location. This is the precondition for chunk unload: a chunk cannot own a stale copy of a character.

## Acceptance

- TODO
