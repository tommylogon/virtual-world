---
type: task
status: todo
area: world
priority: medium
---

# task-497: WorldPainter: biome/feature taxonomy and distribution layers

**Filed:** 2026-09-24
**Related:** task-496, task-398, task-9

## Goal

Define the tile taxonomy and its mapping to engine tags: roads (gravel/dirt/paved/cobblestone), forests (sparse/dense/leaf/mixed/pine), hills, mountains, cliffs, ravines, chasms, beach, lake, river, deep water, ocean, stream, spring, farmland; features (bridges, tunnels, towns, buildings, ruins). Provide per-biome description fragments and distribution layers for resources (tie to the engine/foraging.py tag->yield map, which already keys off road/forest/ruin tags) and hostiles (predators/bandits/monsters by biome and distance from settlement). Data-first so the vocabulary can grow.

## Acceptance

- A data file defines biomes and features with tags + description fragments; each biome maps to engine tags usable by `engine/foraging.py`.
- Resource distribution rules exist (biome → likely items), reusing the existing foraging tag→yield map.
- Hostile distribution rules exist (biome + distance from settlement → spawn likelihood).
- Adding a new biome requires data only, no code change.
