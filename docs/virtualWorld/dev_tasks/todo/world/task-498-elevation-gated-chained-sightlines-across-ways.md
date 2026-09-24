---
type: task
status: todo
area: world
priority: low
---

# task-498: Elevation-gated chained sightlines across ways

**Filed:** 2026-09-24
**Related:** task-496, task-418, task-421

## Goal

Extend beyond-visibility from per-adjacent-way to a chained line of sight: an observer sees along a run of open/see_through ways as long as the floor property does not change; a floor step (or the run turning) breaks the chain. Build on see_through and visible_in_direction and floor (engine/lighting.py, engine/area_description.py, engine/movement.py, engine/room_perception.py). Decide the range/depth cap and whether a sighted cell reveals room contents or only the area name/description. Must not regress tests/test_beyond_visibility.py.

## Acceptance

- An observer sees along a run of open/`see_through` ways whose `floor` is unchanged; a floor delta or a direction change breaks the chain (tests).
- The range/depth cap is configurable and documented.
- The "contents vs name/description only" question is decided and recorded.
- `tests/test_beyond_visibility.py` and the lighting tests still pass.
