# Equipment & Paperdoll System

## Overview

The equipment system (`engine/equipment.py`) manages equipping/unequipping items to body slots on a 100×100px paperdoll grid, with layered stacking (multiple items per slot), two-handed weapon support, full-body suit support, and LLM-powered appearance generation.

## Paperdoll Grid

Defined in `static/js/inspector/paperdoll-view.js:10-24`, the paperdoll has 13 visual areas mapped to equipment slots:

| Visual Area | Slot | Label |
|---|---|---|
| `head` | `head` | Head |
| `neck` | `neck` | Neck |
| `larm` | `arms` | Arms |
| `torso` | `torso` | Torso |
| `rarm` | `arms` | Arms |
| `lhand` | `hands` | Hands |
| `waist` | `waist` | Waist |
| `rhand` | `hands` | Hands |
| `hand_l` | `hand_left` | L.Held |
| `legs` | `legs` | Legs |
| `hand_r` | `hand_right` | R.Held |
| `back` | `back` | Back |
| `feet` | `feet` | Feet |

Plus an additional `accessory` slot (no grid area, shown below paperdoll).

## Equipment Slots

Defined in `EquipmentSystem.EQUIP_SLOTS` (`equipment.py:14-27`):

```python
EQUIP_SLOTS = {
    "head":     {"max_depth": 3, "label": "Head"},
    "neck":     {"max_depth": 2, "label": "Neck"},
    "torso":    {"max_depth": 5, "label": "Torso"},
    "arms":     {"max_depth": 2, "label": "Arms"},
    "hands":    {"max_depth": 2, "label": "Hands"},
    "legs":     {"max_depth": 4, "label": "Legs"},
    "feet":     {"max_depth": 3, "label": "Feet"},
    "back":     {"max_depth": 2, "label": "Back"},
    "waist":    {"max_depth": 2, "label": "Waist"},
    "accessory": {"max_depth": None, "label": "Accessory"},
    "hand_left": {"max_depth": 1, "label": "Left Hand"},
    "hand_right": {"max_depth": 1, "label": "Right Hand"},
}
```

### Stacking (Layered Slots)

Each slot has a `max_depth` limit:
- `accessory` has no limit (`None`)
- `hand_left`/`hand_right` max 1 (only one held item per hand)
- `head` max 3 (e.g., coif → hood → helmet)
- `hands` max 2 (e.g., gloves → gauntlets — worn on hands, not held)
- `torso` max 5 (e.g., undershirt → shirt → vest → coat → cloak)

Items stack from **innermost (index 0)** to **outermost (last index)** in `player.equipped` lists (`player.py:131-137`).

### Worn vs Held: The Two Hand Slot Families

**`hands`** and **`hand_left`/`hand_right`** are different slots that coexist independently:

| Slot | Purpose | Max Depth | Example |
|---|---|---|---|
| `hands` | **Wearing** items on hands (gloves, rings, gauntlets) | 2 | leather gloves + steel gauntlets |
| `hand_left` | **Holding** an item in the left hand | 1 | sword, torch, shield |
| `hand_right` | **Holding** an item in the right hand | 1 | sword, torch, shield |

A character can wear gloves on `hands` AND simultaneously hold a sword in `hand_left` — they are separate equipment slots with no conflict. The paperdoll visual areas reflect this: `lhand`/`rhand` (hands slot, for wearables) and `hand_l`/`hand_r` (hand_left/hand_right slots, for held items).

Items declare which category they belong to via `equip_slots`:
- Wearable gloves: `"equip_slots": ["hands"]`
- Held weapon: `"equip_slots": ["hand_left", "hand_right"]`

### Slot Whitelist

Items declare which slots they fit via `equip_slots` property (`engine/equipment.py:37`). This is a whitelist — an item can be equipped to any slot in its list. **It does not enforce simultaneous occupancy** (e.g., a ring could list both hands but only occupies one at a time).

Example from `static/js/inspector/paperdoll-view.js:157-159`:
```javascript
const equippable = inventory.filter(n => {
    const node = worldState.getNodeByIdentifier(n);
    const slots = node?.properties?.equip_slots || [];
    return slots.includes(slot) && !equippedIds.has(node?.id || n);
});
```

## equip Command

**Command**: `equip <item_name>` or `wear <item_name>` (also `wear <item> under <other_item>`)

**Backend**: `EquipmentSystem.equip_item()` (`engine/equipment.py:66`)

Flow:
1. Validate player state (not sleeping/unconscious/dead/bound) — line 71
2. Find item in inventory (`find_item_node`) — line 74
3. Verify item is carried (`EDGE_CARRYING`) — lines 79-85
4. Check item has `equip_slots` — lines 87-92
5. If slot specified, validate it's in `equip_slots` — lines 94-98
6. Auto-detect slot via `_get_slot_for_item()` — lines 99-102
7. Check slot has room (`_slot_has_area()` checks `max_depth`) — lines 104-106
8. **Two-handed check**: If item has `"two_handed"` tag and equipping to a hand, check other hand has room — lines 146-151
9. Add to slot stack — lines 158-170
   - If `under` parameter given, inserts beneath the named item in the stack
10. **Two-handed marker**: If two-handed, adds `__multi_slot_<item_id>` marker to other hand slot — lines 183-186
11. **Full-body markers**: If `"equips_all_slots"` tag, adds `__multi_slot_<item_id>` marker to every other declared slot — lines 188-190
12. Execute `on_equip` triggers — line 192
13. Rebuild equipment description via `_update_equipment_description()` — line 194
14. Record turn event — lines 199-204

### Two-Handed Weapons

Items with `"two_handed"` tag in `tags` occupy both `hand_left` and `hand_right`. The `_get_extra_hand_slot()` method (`equipment.py:70-74`) returns the opposite hand. A marker node `__multi_slot_<item_id>` is added to the second hand slot (`equipment.py:153`). These markers are filtered out by `_is_marker()` (`equipment.py:65-67`).

### Full-Body Items (`equips_all_slots`)

Items with the `"equips_all_slots"` tag occupy **every** slot they declare in `equip_slots` at once — e.g. the EVA Suit declares `["torso","legs","arms","head","feet","hands"]` and fills all six when equipped. The real item lands in the first declared slot; a `__multi_slot_<item_id>` marker is dropped into each remaining slot (same marker pattern as `two_handed`, via `_get_extra_slots()` at `equipment.py:77`).

Behavior:
- **Occupancy, not sealing** — each covered slot's marker consumes one stack depth, so other clothing can still layer over/under it (boots under a suit, jacket over).
- **Blocked when full** — equipping errors if any covered slot has no room left (`_slot_has_area()` checks `max_depth`).
- **Narrative reports coverage** — `get_equipment_narrative()` renders the suit once with every covered slot: `"You are wearing: EVA Suit over your torso, legs, arms, head, feet, hands."` rather than just its primary slot.
- **Unequip** works via the shared marker cleanup (`_clean_multi_slot_markers`) — removing the suit clears all covered slots.

## unequip Command

**Command**: `unequip <slot>` or `unequip <item_name>` (also `remove <slot>` / `remove <item_name>`)

**Backend**: `EquipmentSystem.unequip_item()` (`engine/equipment.py:230`)

Supports two modes:
1. **By slot**: Pops the outermost item from the slot stack — line 254
   - If pop returns a multi-slot marker, cleans up and removes the real item
2. **By item name**: Searches all slots for the named item — lines 298-327

Cleanup (`_clean_multi_slot_markers`, `equipment.py:240-247`): Removes `__multi_slot_` markers from all slots when a two-handed or full-body item is unequipped.

## Visual Equipment Display

### get_visible_equipment() (`equipment.py:333`)

Returns the **outermost** item of each slot — what other characters see at a glance. For hand slots, it shows the last real item or a `"(two-handed)"` / `"(part of a full-body suit)"` note if only a marker remains.

### get_full_equipment() (`equipment.py:414`)

Returns **all layers** of each slot as lists of item names. Used for self-view and LLM prompts.

### get_equipment_narrative() (`equipment.py:444`)

Generates plain-English equipment description:
- **Self-view** (`viewer_name is None` or matches player): Shows all layers with `"over"` stacking:
  ```
  "You are wearing: helmet over coif on your head; steel cuirass over gambeson on your torso..."
  ```
- **Other view**: Shows only outermost visible items:
  ```
  "Miki is wearing a steel helmet on their head, holding a longsword."
  ```

## LLM-Powered Appearance Generation

`_update_equipment_description()` (`equipment.py:342-393`) rebuilds `player.description` whenever equipment changes:

1. Builds a prompt from `base_description` (naked physical traits) + current equipment list
2. Calls LLM with prompt asking for a vivid 3rd-person description (2-4 sentences)
3. Falls back to **code-generated text** if LLM fails, using slot labels and item names:
   ```
   "Miki is wearing leather boots on their feet, steel cuirass over gambeson on their torso..."
   ```
4. Stores result in `player.description`

The prompt (`equipment.py:356-363`):
```
You are writing a visual appearance description for a character in a fantasy RPG.

BASELINE APPEARANCE (naked physical traits):
{tall, with sharp features and dark hair}

CURRENT EQUIPMENT:
- head: coif → helmet (innermost to outermost)
- torso: gambeson → steel cuirass (innermost to outermost)

Write a vivid, natural 3rd-person description of how this character looks right now...
```

### Hygiene Modifier

`get_hygiene_modifier()` (`equipment.py:403-410`) returns a social penalty:
- 0 at 100 Hygiene → -5 at 0 Hygiene
- Calculated as `-((100 - hygiene) // 20)`
- Range: 0 to -5 in steps of -20 Hygiene

## Equipment Bonuses (`engine/equipment_bonuses.py`)

Equipped items confer **stat bonuses** based on their tags and properties. Aggregated per-player each tick and during combat by `aggregate_bonuses()`.

### Tag-to-Bonus Mapping

| Tag | Bonus | Item Field |
|---|---|---|---|
| `weapon` | Base damage for attacks | `damage`, `damage_skill`, `damage_type` |
| `armor`, `clothing` | Damage reduction (DR) | `defense` |
| `resistance` | Type-based damage resistance | `resistances` dict |
| `insulation` | Temperature shift | `insulation: N` (shifts effective temp ±N°C) |

### `defense` — Damage Reduction

Equipping any item tagged `armor` or `clothing` with a `defense` field reduces incoming weapon/unarmed damage by that amount. Multiple items stack.

```json
{ "defense": 1, "tags": ["clothing"] }
```

```python
# combat.py — damage after defense:
damage = max(1, rolled_damage - target_defense)
```

### `damage` — Weapon Damage (Unified)

Items with the `weapon` tag support a **unified `damage` field** that accepts dice notation or flat numbers:

| Field | Type | Example | Description |
|---|---|---|---|
| `damage` | int or string | `"2d6+3"`, `"1d8"`, `8` | Dice expression or flat number for damage |
| `damage_skill` | string | `"Athletics"` | Skill whose stat (STR/DEX/etc) adds modifier to damage |
| `damage_type` | string | `"slashing"`, `"fire"` | Damage type — enables resistance checks on target |

Damage is calculated as: **dice roll (or flat)** + **stat modifier from skill** - **target defense**, then reduced by **target resistance** if a damage type is set.

```json
{
  "damage": "1d6",
  "damage_skill": "Athletics",
  "damage_type": "slashing",
  "tags": ["weapon"]
}
```

If `damage` contains a dice expression (`"2d6+3"`, `"1d8"`), it's rolled. If it's a bare number (`8`), it's used as flat damage with `roll_dice(1, 8, mod)`. Without the `weapon` tag, unarmed combat falls back to `1d4 + STR` with no type.

### `insulation` — Temperature Shift

Items with the `insulation` tag can have an `insulation` property. When equipped, the player's **effective ambient temperature** is shifted:

```json
{ "insulation": 14, "tags": ["clothing", "insulation"] }
```

Positive insulation warms (traps body heat), negative insulation cools (wicks heat away). Values from multiple worn items **stack**. For example:
- A coat with `insulation: 14` at -12°C feels like 2°C
- At 35°C, that same coat feels like 49°C (traps heat against you)

This affects core temperature drift and area-temp vitals effects (Thirst, Energy, HP from heat/cold).

**Migration from `temp_range`**: The old `temp_range: [min, max]` acted as a clamp, which was unrealistic (a winter coat would cap heat at 20°C). `insulation` shifts temperature equally in both directions — cold feels warmer, hot feels hotter.

### `resistances` — Type-Based Damage Mitigation

Items with the `resistance` tag use a `resistances` property dict to define damage type reductions:

```json
{ "resistances": { "fire": 10, "cold": 5, "toxic": 999 }, "tags": ["resistance"] }
```

Applied in tick processing (e.g., toxic air damage = `max(0, 3 - toxic_resistance)`) and in combat when the weapon has a `damage_type` set.

**Migration note**: Per-type tags (`fire_resistant`, `cold_resistant`, `toxic_resistant`, `magic_resistant`, `vacuum_sealed`) are removed. Use the single `resistance` tag with the `resistances` property dict instead.

### Aggregation

`aggregate_bonuses(player, graph)` (`engine/equipment_bonuses.py:28`) is called:
- Per tick for environmental effects (`tick_manager.py`)
- Per attack for target defense calculation (`combat.py`)
- Iterates `EDGE_EQUIPPED` edges from the player's graph node
- Returns a dict of `{defense, damage, damage_dice, damage_skill, damage_type, insulation, resistances}`

## Frontend UI (Paperdoll View)

The paperdoll is rendered in `static/js/inspector/paperdoll-view.js`:

- **Grid slots**: Rendered as `<div class="paperdoll-slot">` with `data-area` attribute for positioning
- **Filled slots**: Show item name + stack badge (if inner layers exist)
- **Empty slots**: Show `—` with an "Equip +" button
- **Right-click**: Opens context menu with Inspect/Unequip/Open Container
- **Stack badge**: `+N more` badge on layered slots; click opens popup with all layers
- **Equip picker**: `showEquipPicker()` opens modal listing inventory items that fit the selected slot
- **CSS**: Dark theme via CSS custom properties, paperdoll grid layout in `static/css/style.css`

## Slot Occupancy Edge Cases

### Recent Fixes

- `_is_marker()` (`equipment.py:55-57`): Filters `__`-prefixed IDs (multi-slot markers) from all slot operations
- `_clean_multi_slot_markers()` (`equipment.py:159-166`): Removes orphaned markers when a two-handed item is dropped or unequipped
- `drop_item()` calls unequip logic when a carried item is equipped (`item_actions.py:394-399`)
- Slot whitelist allows an item to declare multiple possible slots but does NOT allow simultaneous occupancy of multiple slots by the same item

## Commands Summary

| Command | Example | Description |
|---|---|---|
| `equip <item>` | `equip steel_helmet` | Equip item to auto-detected slot |
| `wear <item>` | `wear leather_gloves` | Alias for equip |
| `wear <item> under <inner>` | `wear vest under coat` | Equip beneath existing item |
| `unequip <slot>` | `unequip head` | Remove outermost item from slot |
| `unequip <item>` | `unequip steel_helmet` | Remove named item |
| `remove <slot/item>` | `remove head` | Alias for unequip |
| `undress` | `undress` | Remove outermost layer from all body slots |
| `strip` | `strip` | Remove everything from all slots |

## Related tasks

- [[task-3-equipment_system|task-3: Equipment system]]
- [[task-87-paperdoll_icon_art|task-87: Paperdoll icon art]]
- [[dev_tasks/review/items/task-54-weapon_system|task-54: Weapon system]]
- [[dev_tasks/done/bugs/bug_2-choices-equip-slots-white-bg|bug-2: Choices equip slots white bg]]
- [[bug_6-inspector-equip-slots-white-bg 1|bug-6: Inspector equip slots white bg]]

## See Also

- `engine/equipment_bonuses.py` — Aggregation module
- `data/library/items/eva_suit.json` — EVA suit example (vacuum_sealed, insulation)
- `data/library/items/heavy_fur_lined_coat.json` — Cold weather gear example
- [[Combat System]] — Defense reduction and weapon damage
- [[Temperature System]] — Effective temperature from equipment
