---
type: task
status: todo
area: world
priority: medium
---

# task-570: Hostile distribution consumer

**Filed:** 2026-09-27
**Related:** 

## What

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

## Browser UI and intended live verification

Intended UI home: load a scenario with a settlement and authored biomes → inspect the world map/area properties → run the hostile spawner or allow the scheduled simulation tick → inspect generated characters and encounter events.

Current availability: `biomes.json` declares and validates `hostile_distribution`, but this card records no runtime consumer; `HOSTILE_KINDS` is otherwise only referenced by its own module/tests. The distribution consumer is not claimed as implemented.

Live steps when available:
1. In a scratch world, choose two biome areas at different distances from a settlement and inspect their `hostile_distribution` values.
   - expected: the spawner reads the authored base chance, per-area settlement adjustment, and max chance for each biome.
2. Run the same seeded spawn pass in both areas and inspect generated hostile characters in the graph and `/api/state`.
   - expected: each spawned character uses a kind allowed by `HOSTILE_KINDS`; chance changes with biome and settlement distance and is capped at `max_chance`.
3. Repeat the same seed and fixture, then change only the settlement distance.
   - expected: the first run reproduces exactly; only the authored distance term changes the spawn decision in the second run.
4. Let a spawned hostile interact with a character and inspect the event stream.
   - expected: the spawned entity participates through the existing character behavior path; the distribution is not merely displayed as unused biome data.

This section is not a claim that hostile distribution is consumed by the simulation today.
