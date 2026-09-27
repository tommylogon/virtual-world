---
type: task
status: todo
area: world
priority: medium
---

# task-570: Hostile distribution consumer

**Filed:** 2026-09-27
**Related:** 

## Goal

biomes.json hostile_distribution (line 2195) declares base_chance / per_area_from_settlement / max_chance per biome. It is loaded (engine/biomes.py:135) and validated (:418-439) but has no runtime consumer; HOSTILE_KINDS (engine/biomes.py:41) appears nowhere outside biomes.py and its tests. Needs task-569's spawner and the item-affinity vocabulary. Distance-from-settlement is already computable from the world grid.

## Acceptance

- TODO
