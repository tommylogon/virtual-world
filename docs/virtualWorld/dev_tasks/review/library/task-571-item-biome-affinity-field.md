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

## Why

Wilderness area planning matched zero items because wilderness tags did not intersect with item general tags. Adding an explicit ffinity list to item schemas and population indexing allows natural resource distribution into wilderness biomes without polluting item role tags.

## How

Added optional ffinity list on the item schema in engine/library_nodes.py, threaded through 
outes/library_ops.py and 
outes/graph_ops.py. Updated engine/population.py to union ffinity and 	ags when indexing domains for area population. Authored 	ools/backfill_item_affinity.py deriving affinities for 361 raw natural resource item templates from their existing tags.

## Acceptance

- [x] Item schema accepts optional ffinity array of biome tags.
- [x] engine/population.py considers ffinity when matching items to areas.
- [x] Wilderness natural resources (herbs, ore, wood, fish, berries) carry appropriate wilderness affinity tags.
- [x] Population planner populates wilderness cells from matching affinity pool.

## Steps to verify

1. Run population tests targeting item affinity
   - expected: pytest tests/test_population.py passes all tests including affinity matching
   - observed: 5 passed in tests/test_population.py
2. Verify backfill script stability
   - expected: python tools/backfill_item_affinity.py --check reports zero missing affinities
   - observed: 361 natural resource items verified

## Files

- engine/library_nodes.py
- engine/population.py
- 
outes/graph_ops.py
- 
outes/library_ops.py
- 	ools/backfill_item_affinity.py
- 	ests/test_population.py
