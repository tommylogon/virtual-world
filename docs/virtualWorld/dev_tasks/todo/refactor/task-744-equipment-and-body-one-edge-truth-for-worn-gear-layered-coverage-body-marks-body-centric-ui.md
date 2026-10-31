---
type: task
status: todo
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
- **Slices 4 and 5 are completed**: Landed via `task-847`, `task-848`, and `task-852` P3 (`appearance.body.modifications` schema, body marks prose compilation in `engine/character_appearance.py:1024`, and the Persona tab embedded body paperdoll navigator).
- **Naming collision resolved**: `EDGE_UNDER = "under"` in `graph.py:926` remains strictly for spatial containment (item hidden beneath furniture). Garment layering does not use an `under` edge; it is modeled via a `layer: int` property on the `EDGE_EQUIPPED` edge (or explicit slot depth).

Remaining scope: Slices 1, 2, and 3 (one writer, explicit garment layers on equipment edges, and derived body effects/coverage).

## Survey and Current Architecture

1. **Equipped state**: `player.equipped` is a runtime view derived from `EDGE_EQUIPPED` edges. Serialization strips it on save (`serialization.py:781`), and `_sync_equipped_from_graph` rebuilds it from the graph.
2. **Layering**: Currently, `body_parts.is_exposed` reads `player.equipped` and infers layers from array order (`outer = last`, `body_parts.py:250`). Stack order must be explicit on the equipment edge (`properties.layer` or slot priority), not dependent on insertion order.
3. **Derived body effects**: Combat damage and body part exposure currently read boolean exposure. They should read derived `effective_coverage(region)`.

## Slices Breakdown

- [x] **Slice 0 - stop persisting derived equipment state.** Completed by task-654. `player.equipped` is stripped on scenario save; `EDGE_EQUIPPED` is the single source of truth.
- [ ] **Slice 1 - one writer.** Equip, unequip, import, and API endpoints all write to `EDGE_EQUIPPED` edges. `set_equipped_payload` ceases dual writing.
- [ ] **Slice 2 - declared layers.** Order is explicit and reorder-proof (an edge `layer: int` property on `EDGE_EQUIPPED`). `body_parts.is_exposed` composes the stack from declared layer integers instead of array index.
- [ ] **Slice 3 - derive body effects from coverage.** Damage, effective sensitivity, and pleasure read `effective_coverage(region)` instead of a flat scalar plus boolean exposure.
- [x] **Slice 4 - body marks.** Completed by task-847 and task-848 (`appearance.body.modifications` array, compiled into prose by `character_appearance.py:1024`).
- [x] **Slice 5 - body-centric UI.** Completed by task-847 and task-848 (embedded paperdoll navigator with visual body region selection and baseline editing).

## Acceptance (Remaining Slices)

- [ ] All equipment mutations (equip, unequip, swap) route through a single writer modifying `EDGE_EQUIPPED` edges.
- [ ] Garment layer order is explicit on `EDGE_EQUIPPED` edge properties (`layer: int`).
- [ ] `body_parts.is_exposed` correctly calculates coverage based on edge `layer` properties.
- [ ] Targeted tests pass (`tests/test_character_loadout_refresh.py`, `tests/test_body_parts.py`).

## Why

Dual-store representations of character equipment create drift between graph edges, player runtime memory, and serialized files. Slice 0 and Slices 4-5 are already accomplished; finishing Slices 1-3 completes the single-source-of-truth model for equipment, making garment layering deterministic and physically grounded.

## Steps to verify

1. Inspect serialization:
   - expected: `pdata.pop("equipped", None)` in `engine/serialization.py:781` keeps saved files free of duplicate equipped state.
   - observed: Verified; already active in production.
2. Layered equipment test:
   - expected: Equip an undergarment (layer 1) and an overcoat (layer 2) on the torso; `is_exposed('torso')` returns false; removing the overcoat leaves undergarment exposed.
   - observed: Pending Slice 2 implementation.
3. Single writer verification:
   - expected: API equip actions only update graph edges, with `player.equipped` refreshed from the graph.
   - observed: Pending Slice 1 completion.

## Files

- `engine/body_parts.py` - update exposure calculation to use edge layer properties
- `engine/equipment_bonuses.py` - ensure edge-driven reads
- `engine/items/use_actions.py` - unify equipment writers
- `graph.py` - ensure `EDGE_UNDER` remains spatial; document `layer` property on `EDGE_EQUIPPED`
- `tests/test_body_parts.py` - tests for layered coverage

## Browser UI and intended live verification

Intended UI home: Character Inspector -> Persona / Body / Equipment view.

Current availability: Persona paperdoll navigator is implemented (tasks 847/848). Equipment edge derivation is active in `world-state.ts`.

Live steps when available:
1. Open a character in the Character Inspector and view equipped items.
2. Add multiple items to the same slot with different layers (e.g., shirt at layer 1, jacket at layer 2).
3. Verify that removing the jacket exposes the shirt without corrupting slot state.

## Reconnaissance (2026-10-31)
- Measured: Slice 0 landed in `task-654` (`engine/serialization.py:781`). Slices 4-5 landed in `task-847`/`task-848` (`appearance.body.modifications`, paperdoll navigator). `EDGE_UNDER` is confirmed as a spatial edge in `graph.py:926`.
- Verdict: STILL_VALID. Slices 1-3 remain open. Status remains todo.
