---
type: task
status: todo
area: world
priority: medium
---

# task-565: Migrate the goblin camp scope id off deep_woods_2

**Filed:** 2026-09-27
**Related:** task-560 task-496

## Goal

The scope's display name is already 'goblin camp'; the id is still deep_woods_2 because ids are minted once as a slug of the name at creation (routes/world_grid_ops.py:237) and the rename route only touches the display name. The project's rule is that ids change and display names do not, so the id is what is stale. Migrate deep_woods_2 -> goblin_camp: the world_scopes key, world_scope_id on all its areas, the parent's placements key, then regenerate the zone so area_deep_woods_2_x_y node ids follow. Check the OUTER deep_woods scope first - if it is genuinely a forest zone wrapping the camp, its id and name are correct as they are and only the interior changes. Scope ids are immutable by design, so this needs a one-off migration script, not a route.

## Acceptance

- TODO
