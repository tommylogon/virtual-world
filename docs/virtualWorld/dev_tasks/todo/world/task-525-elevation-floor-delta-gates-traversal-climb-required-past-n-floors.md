---
type: task
status: todo
area: world
priority: low
---

# task-525: Elevation/floor delta gates traversal (climb required past N floors)

**Filed:** 2026-09-26
**Related:** task-496 task-498

## Goal

Exterior grid steps stay compass moves. When the floor/elevation delta between two adjacent exterior cells exceeds a threshold (suggested >3 floors), the step is no longer a plain walk: it needs a climb (a narrative feature-entry direction), and steep drops/climbs may be blocked unless a feature (ledge, cave, rockface) provides the move. Decide the threshold source (per-scope? per-biome? global config), whether it blocks or just costs extra time, and how the area description phrases it. Depends on the observer-view/narrative-direction description work (task-496 rewrite) and the elevation layer already stored on areas (properties.elevation).

## Acceptance

- TODO
