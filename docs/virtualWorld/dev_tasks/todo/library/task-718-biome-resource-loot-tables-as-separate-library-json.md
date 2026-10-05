---
type: task
status: todo
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

## Notes

- Pursuits already proved the separate-library-JSON pattern works; reuse that loader path.
- task-589 owns the WorldPainter library tab and must ship before or concurrently with this split.
- task-716 owns wiring the fishing Activity resolver to the new table.

