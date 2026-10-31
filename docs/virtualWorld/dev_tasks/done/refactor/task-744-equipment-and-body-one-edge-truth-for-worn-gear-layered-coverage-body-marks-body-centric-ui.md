---
type: task
status: done
area: refactor
priority: medium
related: ['task-654', 'task-675', 'task-847', 'task-848', 'task-852']
wiki: "[[Feature Map]]"
---

# task-744: Equipment and body: one edge truth for worn gear, layered coverage, body marks, body-centric UI

**Filed:** 2026-10-08
**Updated:** 2026-10-31
**Related:** task-654, task-450, task-161, task-660, task-724, task-457, task-619, task-847, task-848, task-852

<!-- deps:start -->
**Related:** [[task-654-single-writer-equipment-edges]], [[task-675-character-editor-three-column-body-with-section-nav-rail]], [[task-847-persona-tab-embedded-body-paperdoll-navigator-for-appearance-schema]], [[task-848-persona-tab-visual-paperdoll-with-inline-body-baseline-editing]]
<!-- deps:end -->

## What

Unify equipment and the body into one edge-backed model and eliminate duplicate stores.

STATUS UPDATE (2026-10-31):
- **Slice 0 is completed**: Landed via `task-654` (`engine/serialization.py:781` pops `equipped` during scenario serialization; worn gear is authoritative on `EDGE_EQUIPPED` edges).
- **Slice 1 is completed**: `engine/equipment.py` sets explicit `EDGE_EQUIPPED` edges and derives `player.equipped` via `_sync_equipped_from_graph(player, player_id)`. `set_equipped_payload` ceases dual writing.
- **Slice 2 is completed**: Order is explicit on `EDGE_EQUIPPED` edge properties (`layer: int`). `_sync_equipped_from_graph` sorts items by edge `layer`. Client-side layer reordering in `paperdoll-view.ts` persists via `ApiClient.updateCharacter`.
- **Slice 3 is completed**: Implemented `effective_coverage(player, region_id, graph)` in `engine/body_parts.py` composing layered clothing coverage `1.0 - product(1.0 - item_coverage)`. `is_exposed` delegates directly to `effective_coverage`.
- **Slices 4 and 5 are completed**: Landed via `task-847`, `task-848`, and `task-852` P3 (`appearance.body.modifications` schema, body marks prose compilation in `engine/character_appearance.py:1024`, and the Persona tab embedded body paperdoll navigator).
- **Naming collision resolved**: `EDGE_UNDER = "under"` in `graph.py:926` remains strictly for spatial containment (item hidden beneath furniture). Garment layering does not use an `under` edge; it is modeled via a `layer: int` property on the `EDGE_EQUIPPED` edge.

## Survey and Current Architecture

1. **Equipped state**: `player.equipped` is a runtime view derived from `EDGE_EQUIPPED` edges. Serialization strips it on save (`serialization.py:781`), and `_sync_equipped_from_graph` rebuilds it from the graph.
2. **Layering**: `EDGE_EQUIPPED` carries `layer: int`. `_sync_equipped_from_graph` orders slot stacks by edge layer. `body_parts.effective_coverage` iterates covering slots in explicit layer order.
3. **Derived body effects**: Combat damage and body part exposure read derived `effective_coverage(player, region_id, graph)`.

## Slices Breakdown

- [x] **Slice 0 - stop persisting derived equipment state.** Completed by task-654. `player.equipped` is stripped on scenario save; `EDGE_EQUIPPED` is the single source of truth.
- [x] **Slice 1 - one writer.** Equip, unequip, import, and API endpoints all write to `EDGE_EQUIPPED` edges. `set_equipped_payload` ceases dual writing.
- [x] **Slice 2 - declared layers.** Order is explicit and reorder-proof (an edge `layer: int` property on `EDGE_EQUIPPED`). `body_parts.is_exposed` and `effective_coverage` compose the stack from declared layer integers instead of array index.
- [x] **Slice 3 - derive body effects from coverage.** Damage, effective sensitivity, and pleasure read `effective_coverage(region)` instead of a flat scalar plus boolean exposure.
- [x] **Slice 4 - body marks.** Completed by task-847 and task-848 (`appearance.body.modifications` array, compiled into prose by `character_appearance.py:1024`).
- [x] **Slice 5 - body-centric UI.** Completed by task-847 and task-848 (embedded paperdoll navigator with visual body region selection and baseline editing).

## Acceptance (Remaining Slices)

- [x] All equipment mutations (equip, unequip, swap) route through a single writer modifying `EDGE_EQUIPPED` edges.
- [x] Garment layer order is explicit on `EDGE_EQUIPPED` edge properties (`layer: int`).
- [x] `body_parts.is_exposed` correctly calculates coverage based on edge `layer` properties.
- [x] Targeted tests pass (`tests/test_character_loadout_refresh.py`, `tests/test_body_parts.py`, `tests/test_equipment_api_edges.py`, `tests/test_equipment_payload.py`).

## Why

Dual-store representations of character equipment create drift between graph edges, player runtime memory, and serialized files. Finishing Slices 1-3 completes the single-source-of-truth model for equipment, making garment layering deterministic and physically grounded.

## Steps to verify

1. Inspect serialization:
   - expected: `pdata.pop("equipped", None)` in `engine/serialization.py:781` keeps saved files free of duplicate equipped state.
   - observed: Verified; active in production.
2. Layered equipment test:
   - expected: Equip an undergarment (layer 1) and an overcoat (layer 2) on the torso; `is_exposed('torso')` returns false; removing the overcoat leaves undergarment exposed.
   - observed: Verified in `tests/test_body_parts.py:test_effective_coverage_layered_clothing`.
3. Single writer verification:
   - expected: API equip actions only update graph edges, with `player.equipped` refreshed from the graph.
   - observed: Verified across `tests/test_equipment_api_edges.py` and `tests/test_equipment_payload.py`.

## Files

- `engine/body_parts.py` - implemented `effective_coverage` composing multi-layer garment coverage; re-routed `is_exposed`
- `engine/equipment.py` - unified equipment writer to manage `EDGE_EQUIPPED` edges and explicit `layer` property; sync runtime `player.equipped` projection from graph
- `engine/serialization.py` - assign default `layer: idx + 1` to `EDGE_EQUIPPED` on legacy scenario load
- `graph.py` - documented `layer` property on `EDGE_EQUIPPED`
- `static/js/inspector/paperdoll-view.ts` - persist layer reorder via `ApiClient.updateCharacter`
- `tests/test_body_parts.py` - tests for layered coverage and edge layer order preservation

## Browser UI and intended live verification

Intended UI home: Character Inspector -> Persona / Body / Equipment view.

Current availability: Persona paperdoll navigator is implemented (tasks 847/848). Equipment edge derivation is active in `world-state.ts`.

Live steps:
1. Open a character in the Character Inspector and view equipped items.
2. Add multiple items to the same slot with different layers (e.g., shirt at layer 1, jacket at layer 2).
3. Verify that removing the jacket exposes the shirt without corrupting slot state.

## Completion notes (2026-10-31)
- Landed Slices 1, 2, and 3:
  1. `EDGE_EQUIPPED` is the single writer destination in `engine/equipment.py`. Dual writing in `set_equipped_payload` was eliminated in favor of `_sync_equipped_from_graph(player, player_id)`.
  2. Garments carry explicit `layer: int` edge property on `EDGE_EQUIPPED`. `_sync_equipped_from_graph` sorts items by layer index. Client-side reordering in `paperdoll-view.ts` calls `ApiClient.updateCharacter`.
  3. `effective_coverage(player, region_id, graph)` calculates compounded coverage across layered garments: `1.0 - product(1.0 - cov)`. `is_exposed` checks `effective_coverage < threshold`.
  4. 37 tests in `tests/test_body_parts.py` and 28 tests in `tests/test_character_loadout_refresh.py`, `tests/test_equipment_api_edges.py`, `tests/test_equipment_payload.py` pass cleanly.
