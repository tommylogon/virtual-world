---
type: task
status: todo
area: library
priority: high
---

# task-571: Item biome affinity field

**Filed:** 2026-09-27
**Related:** 

## Goal

No library item declares which biomes or area tags it belongs in. A repo-wide grep of data/library/items/ for the wilderness biome tags (forest, woods, rocky, farmland, shore, ruin, road, dense) returns ZERO matches, so engine/population.py:120-121 tag-intersects to nothing and every compiled wilderness area plans empty (routes/population_ops.py returns status empty). The only bridges today are storage/trade/religious, all from building biomes. Add an affinity/habitat field to the item schema (routes/library_ops.py:118-141) and backfill the wilderness vocabulary. This is the vocabulary bridge that task-569 and task-570 both need.

## Acceptance

- TODO
