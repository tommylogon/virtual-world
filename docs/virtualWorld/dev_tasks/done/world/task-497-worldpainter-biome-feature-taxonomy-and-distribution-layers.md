---
type: task
status: done
area: world
priority: medium
---

# task-497: WorldPainter: biome/feature taxonomy and distribution layers

**Filed:** 2026-09-24
**Related:** task-496, task-398, task-9
**Design:** `docs/design/world-environment-taxonomy.md` — the expanded 170-category
vocabulary and per-entry record shape this data file should grow toward.

## Goal

Define the tile taxonomy and its mapping to engine tags: roads (gravel/dirt/paved/cobblestone), forests (sparse/dense/leaf/mixed/pine), hills, mountains, cliffs, ravines, chasms, beach, lake, river, deep water, ocean, stream, spring, farmland; features (bridges, tunnels, towns, buildings, ruins). Provide per-biome description fragments and distribution layers for resources (tie to the engine/foraging.py tag->yield map, which already keys off road/forest/ruin tags) and hostiles (predators/bandits/monsters by biome and distance from settlement). Data-first so the vocabulary can grow.

## Acceptance

- A data file defines biomes and features with tags + description fragments; each biome maps to engine tags usable by `engine/foraging.py`.
- Resource distribution rules exist (biome → likely items), reusing the existing foraging tag→yield map.
- Hostile distribution rules exist (biome + distance from settlement → spawn likelihood).
- Adding a new biome requires data only, no code change.
- The 16 shipped biomes are the seed of the 170-category vocabulary in
  `docs/design/world-environment-taxonomy.md`; each shipped biome validates and
  the vocabulary can be grown as data under the same record shape.

## Progress — 2026-09-24

Delivered as a data file plus a generic loader/validator; no engine behaviour
change beyond extending the foraging tag vocabulary.

- **`data/worldpainter/biomes.json`** (new) — 16 biomes (forest/rock/water/farm
  families) with `terrain`, engine `tags`, `forage_skills`, `floor` and
  description fragments; 9 features (road, bridge, ford, tunnel, town, village,
  building, ruin, gate) with tags and the biomes they appear in; per-biome
  `resource_distribution` (foraging type tags + weight) and
  `hostile_distribution` (predator/bandit/monster with base chance, per-area
  growth away from settlement, and a cap).
- **`engine/biomes.py`** (new) — `load` / `biomes` / `features` /
  `resource_distribution` / `hostile_distribution` / `biome` / `area_tags` /
  `forage_skill_bonus` / `validate`. `forage_skill_bonus` merges
  `foraging.AREA_SKILL_BONUS` over a biome's tags, so a painted area forages with
  the existing machinery. `validate` is generic: it checks every biome has a
  foraging-recognised area tag, known forage skills, floor and descriptions;
  resource tags come from the `foraging.SKILL_TABLES` vocabulary; feature biome
  refs resolve; hostile kinds/bands are sane; and every biome has both rule sets.
- **`engine/foraging.py`** — `AREA_SKILL_BONUS` gained the natural-biome tags
  (hill, hills, mountain(s), rocky, cliff, ravine, chasm, beach, lake, river,
  stream, spring, ocean, deep_water, farmland, field). None are placed by the
  existing scenarios, so behaviour is unchanged until a painted world uses them;
  "water" was deliberately **not** added so a water source is not turned into a
  forage spot.
- **Tests** — `tests/test_biomes.py` (12): shipped taxonomy validates clean,
  every biome carries a foraging tag, resource tags are in the foraging
  vocabulary, the derived skill bonus is non-zero, features resolve, hostile
  bands sane, a new biome added as **data only** validates, a deliberately bad
  biome is rejected, and missing rule sets are flagged. 1508 tests across
  biomes + foraging + data-mojibake pass.
