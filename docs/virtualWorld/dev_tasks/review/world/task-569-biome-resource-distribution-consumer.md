---
type: task
status: review
area: world
priority: high
---

# task-569: Biome resource distribution consumer

**Filed:** 2026-09-27
**Related:** 

## Goal

Wire data/worldpainter/biomes.json resource_distribution (line 1818) into a spawner that places items into compiled areas. The data is authored and validated (engine/biomes.py:397-416) but has ZERO runtime consumers -- a repo-wide grep finds only the data, the loader, the validator and the tests. Blocked by the item-affinity vocabulary task and by task-504 (quantity/pooled nodes). Populate GenerationReport.unresolved_tags (generation.py:48) when a tag resolves to nothing. task-497 is filed done but its acceptance criteria read as behaviour; its own note admits no engine behaviour change. Trust the code, not the folder.

## Acceptance

- TODO

## Implemented (2026-10-02)

- New `engine/world/spawner.py::spawn_resources(area_nodes, index, ...)`:
  for each area whose `properties.biome` declares a `resource_distribution`,
  picks `per_area` weighted entries, resolves each entry's tags to library
  items carrying **all** of them (`LibraryIndex.candidates(require_all=...)`),
  and stages the item subtree (via `engine.library_nodes.build_item_subtree`)
  plus a normal `in` edge, stamped with `generated` provenance so it unloads
  with its scope (task-584). Deterministic for a seed. A tag (or missing
  container content) that resolves to nothing places **no** item and is counted
  in the returned `unresolved_tags` — never substituted.
- `world_compile.compile_grid` gained `spawn_index` / `resources_per_area`:
  when an index is supplied it invokes the spawner and feeds `unresolved_tags`
  into `GenerationReport` (and a note).
- `routes/world_grid_ops.handle_generate_scope` builds the item `LibraryIndex`
  and passes it, so the production Generate button now composes resources.
  `{resources_per_area: N}` is accepted; default 1 per area.

Tests: `tests/test_biome_spawner.py` (9) — resolved placement + provenance,
seed determinism, a dead tag reported not substituted, no-biome no-op, the
compile-integration path populating `unresolved_tags`, and compile-without-index
unchanged.

**Not done / blocked:** task-569's own note also mentions task-504
(quantity/pooled nodes). Pooled resources are placed as normal item nodes; if
the resource should be a pool (`quantity` + `harvest`), the library entry's own
shape decides and `build_item_node` does not carry `quantity`/`harvest` today.
Filed as a follow-up rather than guessed.
