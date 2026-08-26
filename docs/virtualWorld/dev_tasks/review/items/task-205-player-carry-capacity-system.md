---
id: 205
title: Player Carry Capacity System
group: Equipment & Inventory
wiki: "[[Items & Inventory/Inventory]]"
priority: medium
created: 2026-08-08  # back-filled from implementation in 42ca0b14
tags: [items, weight, traits, ui, vitals, movement]
---

# Player Carry Capacity System

**Status**: In Review — implemented 2026-08-11  
**Priority**: Medium  
**Updated**: 2026-08-11  

---

## Implementation Summary

- **Backend helpers** (`engine/item_actions.py`): added module-level `get_carry_load_ratio`, `sum_carry_weight`, `_sum_container_contents`, `_node_effective_weight`. `_check_player_capacity` now uses recursive weight sum including nested containers.
- **Weight modifiers**: `equipped_weight_mod` on items (default 1.0), `container_weight_mod` on containers (default 1.0). Mods multiply when stacked (equipped + inside container).
- **Movement encumbrance** (`engine/movement.py`): `_get_encumbrance_energy_cost` returns +1 energy at 50-80% load, +2 at 80-100%, blocks movement entirely at ≥100%, and blocks dash at ≥80%.
- **Serialization** (`engine/serialization.py`): player dict now includes `current_carry_weight` and `max_carry_capacity`.
- **UI** (`static/js/inspector/paperdoll-view.js`): carry load meter with progress bar and color thresholds in Equipment tab. `item-view.js` exposes `equipped_weight_mod` and `container_weight_mod` editable fields.
- **Tests**: added `TestCarryCapacity` (8 tests) and `TestEncumbranceMovement` (5 tests). All 149 related tests pass.

---

## Summary

The player has a hard carrying capacity limit (`BASE_CARRY_CAPACITY = 100 kg`, scaled by
trait `carry_capacity_mod`), enforced via `_check_player_capacity` in `engine/item_actions.py`.
It blocks `take` when the character is at/over capacity. But the feature is half-built:
there are no weight limit **displays** showing how loaded the character is, no encumbrance
**penalties** that scale with how close to the limit the character is, and no integration
with the energy-decay (task-156) or size-gating (task-202) systems that the design calls for.

This task owns the player-facing carry capacity design: displays, encumbrance tiers, and
the hooks into energy/movement/traits. Container-specific limits remain under task-103.

## What Already Exists (committed in `42ca0b14` — trait schema v2)

- `engine/item_actions.py:18` — `BASE_CARRY_CAPACITY = 100.0`
- `engine/item_actions.py:1176` — `_check_player_capacity(player_manager, item_weight)`
  - Sums `EDGE_CARRYING` edges to the player node
  - Multiplies `BASE_CARRY_CAPACITY` by `TraitSystem.get_carry_capacity_mod(player)`
  - Hard block: `current + item_weight > capacity` → raises `ValueError` (take fails)
- `engine/traits.py:83-84` — `CARRY_CAPACITY_MOD = "carry_capacity_mod"` effect key
- `engine/traits.py:345-351` — `strong_backed` trait: `{"carry_capacity_mod": 2.0}`
- Called at `item_actions.py:732` in `take_item` (before edge rewire)

## What's Missing

### 1. Weight Limit Displays (UI)
- Total carried weight vs capacity shown in the paperdoll/inventory panel
  (e.g. `12.3 / 100.0 kg` with a progress bar)
- Color thresholds: green (<50%), yellow (50-80%), red (>80%)
- Inspector should show `current_carry_weight` computed read-only (analogous to
  `max_weight_capacity` in the container UI from task-103)
- `static/js/inspector/paperdoll-view.js` / inventory grid need a weight meter

### 2. Encumbrance Tiers (Backend)
- Light load: <50% capacity — no penalty
- Moderate load: 50-80% — movement costs +1 energy (task-156 hook)
- Heavy load: 80-100% — movement costs +2 energy, dash blocked
- Over capacity: already hard-blocked at `take`, but should also gate movement
  (can't move while overencumbered? or forced crawl?)

### 3. Worn / Embedded Weight Modifiers
- **Equipped items are lighter**: an item's *effective* weight for encumbrance should
  get a modifier when `EDGE_EQUIPPED` (vs raw `EDGE_CARRYING`). E.g. worn armor
  might count at 75% (distributed weight) or 125% (cumbersome gear). Add an optional
  `equipped_weight_mod` property on items (default 1.0 = no change).
- **Container-packed items are lighter**: items nested inside a container the player
  carries should get a further modifier. A well-packed backpack might reduce
  effective weight (good distribution, `container_weight_mod < 1.0`) or increase it
  (`> 1.0`, inefficient packing). Add `container_weight_mod` to container items.
- **Container capacity modifiers**: when an item has the `container` tag, the inspector
  should show `max_weight_capacity` (from task-103) **and** an editable
  `capacity_modifier` (a multiplier on how much *effective* weight the container's
  contents contribute to the carrier — e.g. a `0.75` backpack means its 5 kg of contents
  count as 3.75 kg toward encumbrance). Default 1.0.

### 4. Trait Interactions
- `strong_backed` doubles capacity — verified
- Consider: does `strong_backed` also raise the encumbrance tier thresholds proportionally?
  (i.e. a strong character hits "heavy" later, not just later "over capacity")
- Consider: are there traits that affect the energy penalty rather than raw capacity?
  (e.g. `enduring` halves encumbrance energy costs)

### 5. Integration Points
- **task-156** (weight → energy decay): `_check_player_capacity` already computes total
  weight; expose a `get_carry_load_ratio(player)` helper that task-156 can call instead
  of re-summing edges. Tie encumbrance tier to move energy cost.
- **task-202** (over-encumbrance → size): when at/over capacity threshold, bump character
  size class for passage gating. Reuse the same load ratio.
- **`engine/movement.py`**: pass carry-load ratio into `apply_action("move", ...)` cost
  adjustment.
- **`engine/effects.py` / `consume_item`**: `adjust_uses`/`drain` should recompute weight
  (task-155) so encumbrance reflects partial consumption.

## Design Decisions to Make

1. **Linear vs tiered penalties**: Do energy costs scale linearly with weight ratio, or
   jump at 50% / 80% thresholds? (Tiers feel more D&D-like; linear is simpler.)
2. **Over-capacity as a condition**: Should being at 100%+ trigger a `heavy_load` or
   `overburdened` condition (task-190 conditions system) rather than just a hard take-block?
3. **Carry limit on the player node**: Is `carry_capacity` a static `BASE_CARRY_CAPACITY`
   constant, or should it be a property on the `Player` object / character registry so
   different characters have different limits?
4. **Container contents in the total**: Does a backpack's contents count toward the
   player's carried weight? (It should — nest recursively via `EDGE_IN` into containers
   the player carries. Currently `_check_player_capacity` only sums direct `EDGE_CARRYING`
   edges.) Needs to apply `container_weight_mod` at each nesting level.)
5. **Equipped vs carried weight modifiers**: Should worn items (`EDGE_EQUIPPED`) and
   container-packed items get a `equipped_weight_mod` / `container_weight_mod` applied
   to their effective encumbrance contribution? (Yes — see section 3 above.)
6. **Weight mod stacking**: If an item is both equipped AND inside a worn container, do
   the mods multiply, add, or take the more favorable? (Design call.)

## Files to Modify

1. `engine/item_actions.py` — add `get_carry_load_ratio(player)` helper, nest container contents in weight sum, apply `equipped_weight_mod` + `container_weight_mod`
2. `engine/movement.py` — apply encumbrance energy cost
3. `engine/tick_manager.py` — weight-modulated move cost (delegates to movement or uses ratio helper)
4. `engine/player.py` — optional `carry_capacity` field on Player (if decision 3 goes that way)
5. `static/js/inspector/paperdoll-view.js` — carry weight display + progress bar
6. `static/js/inspector/item-view.js` — `current_carry_weight` read-only field, `equipped_weight_mod` / `container_weight_mod` / `capacity_modifier` editable fields on container items

## Testing

- [ ] Empty character has 0/100 kg, no penalty
- [ ] Character at 50% capacity triggers moderate-load energy cost on move
- [ ] Character at 90% capacity is blocked from taking a 5 kg item
- [ ] Container contents (backpack with 5 kg inside) counts toward carry ratio
- [ ] Equipped item (sword 3 kg, `equipped_weight_mod: 0.75`) contributes 2.25 kg to encumbrance
- [ ] Container-packed items apply `container_weight_mod` (backpack 5 kg × 0.8 mod = 4 kg effective)
- [ ] `strong_backed` trait doubles capacity, raising thresholds proportionally
- [ ] Hard block at `take` time still works (no regression)

## Related

- task-103: Weight/Volume Limits for Containers (container-specific `max_weight_capacity`;
  this task adds player total + `capacity_modifier` on containers)
- task-155: Item Uses Affect Weight
- task-156: Weight Affects Energy Decay
- task-202: Over-Encumbrance Counts as One Size Larger
