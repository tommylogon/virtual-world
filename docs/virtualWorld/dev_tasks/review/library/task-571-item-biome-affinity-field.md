---
type: task
status: review
area: library
priority: high
related: ['task-573', 'task-569', 'task-570', 'task-588']
---

# task-571: Item biome affinity field

**Filed:** 2026-09-27
**Related:** 

<!-- deps:start -->
**Related:** [[task-573-lint-biome-coverage-from-biomes-json]], [[task-569-biome-resource-distribution-consumer]], [[task-570-hostile-distribution-consumer]], [[task-588-investigate-where-worldpainter-vocabularies-live]]
<!-- deps:end -->

## What

No library item declares which biomes or area tags it belongs in. A repo-wide grep of data/library/items/ for the wilderness biome tags (forest, woods, rocky, farmland, shore, ruin, road, dense) returns ZERO matches, so engine/population.py:120-121 tag-intersects to nothing and every compiled wilderness area plans empty (routes/population_ops.py returns status empty). The only bridges today are storage/trade/religious, all from building biomes. Add an affinity/habitat field to the item schema (routes/library_ops.py:118-141) and backfill the wilderness vocabulary. This is the vocabulary bridge that task-569 and task-570 both need.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
