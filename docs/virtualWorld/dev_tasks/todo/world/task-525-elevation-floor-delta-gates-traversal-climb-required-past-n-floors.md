---
type: task
status: todo
area: world
priority: low
---

# task-525: Storey delta gates traversal (climb required past N storeys)

**Filed:** 2026-09-26
**Related:** task-496 task-498

## Goal

Exterior grid steps stay compass moves. When the **storey** delta between two
adjacent exterior cells exceeds a threshold (suggested >3 storeys), the step is no
longer a plain walk: it needs a climb (a narrative feature-entry direction), and
steep drops/climbs may be blocked unless a feature (ledge, cave, rockface)
provides the move. Decide the threshold source (per-scope? per-biome? global
config), whether it blocks or just costs extra time, and how the area description
phrases it. Depends on the observer-view/narrative-direction description work
(task-496 rewrite) and the floor layer already stored on areas
(`properties.floor`).

**Terminology (corrected with the author, 2026-09-27):** the unit is *storeys*,
not heights and not floor materials. `properties.floor` is the storey index — 0 is
the ground plane, 1 one up, -1 one down, and it is **unbounded** (three stacked
rooms, a lake bottom at -2, an 80-storey tower, a hole to hell at -900). Ground
*material* is `properties.surface`. The old `elevation` layer / `properties.elevation`
is gone, and `CLIFF_FLOOR_DELTA = 2` is a *storey* delta — which is why the prose
promotion is restricted to `world` scopes: a storey step inside a town or interior
is a staircase, not a rockface. The gate should follow suit and only apply where a
storey step really is terrain (outdoors), so an interior can stack rooms freely.

## Acceptance

- TODO
