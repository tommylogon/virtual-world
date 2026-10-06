---
type: task
status: review
area: library
priority: high
---

# task-718: Biome resource loot tables as separate library JSON

**Filed:** 2026-10-05
**Related:** task-569,task-571,task-573,task-588,task-589,task-716

## Goal

Split the weighted fish/scrap/trash water-resource tables out of biomes.json into their own library JSON vocabulary, authored separately from biomes and pursuits like items and areas are. Author river/shallows/pool/rapids fish tags and matching item definitions; make the fishing Activity resolver sample this table at runtime.

## Acceptance

- [ ] `data/worldpainter/biomes.json` no longer contains `resource_distribution` or `hostile_distribution` keys; loot tables live under `data/library/resource_distribution/` and `data/library/hostile_distribution/` instead.
- [ ] Each loot table JSON includes an `id`, `name`, `biome_tags`, `location_tags`, `item_tags`, `weight`, and `conditions` block.
- [ ] `engine/biomes.py` and the fishing Activity resolver read from the new library paths instead of the bundled `biomes.json` keys.
- [ ] A WorldPainter library tab exposes these vocabularies with the same authoring flow as items, areas, and pursuits.
- [ ] Existing authored scenarios and saves continue to resolve resources after the split (migration path or backward-compat shim documented).

## Open questions

- Should hostile (combat) and non-hostile (fishing/gathering) tables share a schema or be separate vocabularies?
- Do we keep a lightweight `resource_distribution` index on biomes for "this biome participates in these tables" or remove that coupling entirely?

## Implementation notes (2026-10-05)

- **Migration tool:** `tools/migrate_loot_tables.py` extracts the existing bundled
  `resource_distribution` and `hostile_distribution` keys from
  `data/worldpainter/biomes.json` and writes one library JSON per entry under
  `data/library/resource_distribution/` (52 files) and
  `data/library/hostile_distribution/` (24 files). Run with `--strip-biomes`
  to remove the bundled keys after verifying the new files.
- **Engine loading:** `engine/biomes.py` now prefers the bundled keys when present
  (backward compat for existing scenarios) and falls back to the library dirs when
  the keys are absent. New accessors `biomes.resource_library()` and
  `biomes.hostile_library()` return the raw library entries for the richer
  `biome_tags` / `conditions` schema the fishing slice will use.
- **Spawner integration:** `engine/world/spawner.py` did not need a code change
  because `biomes.resource_distribution()` still returns the legacy per-biome
  dict shape. The new schema is available via the library accessors when task-716
  is ready for conditional/time/weather filtering.
- **Validation:** `biomes.validate()` now checks both bundled and library data,
  merging them so a partial bundled record does not hide the library coverage.
- **Tests:** `tests/test_biomes.py` gained `test_resource_library_returns_split_entries`
  and `test_hostile_library_returns_split_entries`; `tests/test_biome_spawner.py`
  gained `test_spawn_resources_reads_from_library_when_bundled_key_is_gone`.
  All 28 biome/spawner tests pass after the split.

## Migration path for existing saves/scenarios

1. Run `python tools/migrate_loot_tables.py --force`.
2. Run `python tools/migrate_loot_tables.py --strip-biomes` after verifying the
   generated files.
3. Existing saves continue to resolve resources because `biomes.resource_distribution()`
   and `biomes.hostile_distribution()` return the library-backed per-biome dicts
   when the bundled keys are absent. No save conversion is required.


