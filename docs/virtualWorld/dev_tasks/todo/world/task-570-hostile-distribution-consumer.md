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

## Progress / blocker (2026-10-02)

**Chance model landed and tested** (`engine/world/spawner.py`, task-569's
module): `hostile_chance(biome, distance)` evaluates
`min(max_chance, base_chance + per_area_from_settlement * distance)` clamped to
`[0,1]`; `roll_hostiles(...)` returns the kinds that appear for a seeded roll;
`hostile_character_node(kind, ...)` builds a tagged, generation-stamped
character node. `HOSTILE_KINDS` is now consumed. Covered by
`tests/test_biome_spawner.py` (chance rises with distance and caps; deterministic
roll; tagged node).

**Why it is not wired to a live spawn (blocking, per "never infer runtime from
existence"):** a hostile must become a live simple NPC (a `Player` in the
manager), not a bare graph node — and there is **no hostile character content**
to build one from. `data/library/characters/` contains zero entries tagged
`predator`/`bandit`/`monster`/`hostile` (the only `monster`-tagged record is
`anne.json`, a child). Spawning generic hostiles from code would be inventing
content the taxonomy does not author, which is exactly what the resource path
avoids by reporting `unresolved_tags` instead of substituting.

**Needed to finish:** author hostile character definitions (predator / bandit /
monster) in `data/library/characters/`, then a runtime consumer that rolls at
area occupancy and registers a `simple_npc` `Player` via the existing character
spawn path. Distance-from-settlement from the grid is available (`world_compile`
knows the cells) and can be supplied per area.

Left in `todo`; not moved to review, because the behaviour is not demonstrated
live.
