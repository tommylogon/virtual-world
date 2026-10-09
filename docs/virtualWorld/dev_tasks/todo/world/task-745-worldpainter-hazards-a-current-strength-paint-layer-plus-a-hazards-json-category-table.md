---
type: task
status: todo
area: world
priority: medium
---

# task-745: WorldPainter hazards: a current/strength paint layer plus a hazards.json category table

**Filed:** 2026-10-09
**Related:** task-557 task-520 task-496

## Goal

Turn painted terrain into consequences, not just DCs. Two halves. (1) A current paint layer beside biome/road/floor/climate: a per-cell flow direction and a strength 1-20, following task-557's precedent for adding a layer (whitelist in engine/world_grid.PAINT_LAYERS, editor tool, compiler read). Storey gradient may supply the direction/speed default when the author paints no current. (2) data/worldpainter/hazards.json, a category registry like biomes.json: river/rapids, cliff/fall, thorns, pit, bridge-jump, each {skill, dc ladder by strength, on_fail effects, success/fail message templates}. A --check gate validates it the way way_property_index does. Policy is data: the 5/20 ladder is author-tunable, not code.

## Acceptance

- TODO
