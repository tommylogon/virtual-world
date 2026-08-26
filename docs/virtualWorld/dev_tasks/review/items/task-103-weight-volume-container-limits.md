---
group: Equipment & Inventory
wiki: "[[Items & Inventory/Inventory]]"
---

# Task 103: Weight/Volume Limits for Containers

**Filed**: 2026-07-24  
**Priority**: Low  
**Status**: In Review — Phase 3 implemented 2026-08-13, pending browser verify  
**Updated**: 2026-08-13  

---

## Summary

Currently items can be freely put into any container regardless of size/weight. Add weight and volume limits to containers, with the simple rule: if an item weighs more than the container's capacity, it can't go in. More advanced physics (volume, shape) can come later.

## What Already Exists

- Items have a `weight` field (numeric)
- Items have a `container` property (boolean)
- Items have a `contents` array (what's inside)
- Container contents can be edited in the item library UI
- Container items can be opened/closed via triggers

## What's Done (Phase 1 — UI)

- `max_weight_capacity` editable field shows in item inspector when the `container` tag is present (same pattern as weapon damage fields)
- `current_weight` computed read-only display sums weight of all items inside the container via `EDGE_IN` edges in the graph
- Fill progress bar (green / yellow / red at 50% / 80%) when `max_weight_capacity` is set
- Both fields hidden when item doesn't have the `container` tag

### Files changed
- `static/js/inspector/item-view.js` — container capacity section, `_containerCurrentWeight`, `_containerFillBar`

## What's Done (Phase 2 — Validation)

- `_check_container_capacity` helper in `ItemActions`: sums contents weight via `EDGE_IN` edges, compares against `max_weight_capacity`
- Called from `put_item_in_container` — rejects with message before moving the item
- Called from `move_item_node` API route (`/api/graph/item/<node_id>/move`) — inline check, returns 400 with error message
- Message format: `"The backpack can't hold that — it's too heavy (capacity: 3.5/10.0 kg)."`
- `BASE_CARRY_CAPACITY = 100.0` (kg) with trait `carry_capacity_mod` scaling (e.g. `strong_backed` = 2.0x), via `_check_player_capacity` in `ItemActions`

### Files changed
- `engine/item_actions.py` — added `_check_player_capacity`, `_check_container_capacity`, called in `put_item_in_container`, `take_item`, and `move_item`
- `engine/traits.py` — `CARRY_CAPACITY_MOD` effect key + `strong_backed` trait
- `routes/graph.py` — inline capacity check in `move_item_node`

### Verified (via pytest — task-205 encumbrance tests)
- [x] Heavily loaded character loses more energy per move (`TestEncumbranceMovement`)
- [x] Empty-handed character matches current cost (no regression — light load test)
- [x] Weight thresholds are sensible (light load no penalty at 20 kg / 100 kg cap)
- [x] Container contents count toward carried weight (`TestCarryCapacity`)

## What's Done (Phase 3 — Polish)

- `engine/effects.py` — `give_item` capacity checks (existing); `spawn_item` with `into: "container"` checks `max_weight_capacity` before `EDGE_IN` placement
- Progress bar / weight meter color change near limit — container fill bar in item inspector; player carry bar in paperdoll (task-205)
- Weight display in item library contents editor — per-item badges + total row (`item-library/contents-editor.js`)
- Capacity UI in inspector paperdoll — carry load meter (task-205)
- Encumbrance interaction with task-156/202 documented under task-205; movement tiers wired in `engine/movement.py`

### Files changed (Phase 3, 2026-08-13)
- `engine/effects.py` — `_check_container_capacity`, `spawn_item` `into: "container"` path
- `static/js/inspector/item-view.js` — container fill bar
- `tests/test_trigger_system.py` — spawn-into-container + give_item capacity tests

### Simple Examples
- Small pouch: `max_weight_capacity: 2` — can hold a key (0.1 kg) but not a sword (3 kg)
- Backpack: `max_weight_capacity: 15` — can hold several items
- Chest: `max_weight_capacity: 50` — can hold heavy items
- Barrel: `max_weight_capacity: 100` — can hold liquids, ore, etc.

## Related

- task-155: Item uses affect weight
- task-156: Weight affects energy decay
- task-202: Over-encumbrance counts as one size larger
- task-205: Player carry capacity system (displays, trait interactions)
