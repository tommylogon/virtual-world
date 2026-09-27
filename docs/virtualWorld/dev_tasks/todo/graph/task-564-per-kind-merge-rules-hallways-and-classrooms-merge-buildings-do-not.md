---
type: task
status: todo
area: graph
priority: medium
---

# task-564: Per-kind merge rules: hallways and classrooms merge, buildings do not

**Filed:** 2026-09-27
**Related:** task-561 task-562 task-496

## Goal

Region merging is one global switch per scope, but a high-school plan needs different rules per kind in the same grid: a run of hallway cells merges into one corridor, 4 classroom cells merge into one room, and adjacent building cells never merge (a terrace of houses is several buildings, not one). The machinery already exists (world_compile._regions with an identity function); it needs the identity to carry a per-kind merge rule instead of the whole scope sharing one toggle. Also decide what the 'merge' control means once this lands - a default per mode, with the toggle as an override.

## Acceptance

- TODO
