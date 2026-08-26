---
group: Equipment & Inventory
wiki: "[[Items & Inventory/Equipment & Paperdoll]]"
---
# Equipment & Layering System

**Filed**: 2026-07-15 (updated 2026-07-30)
**Priority**: High
**Status**: Review

---

## Summary

A slot-based equipment system where items are worn in layered stacks on body slots. Orders of wearing determines what's visible vs concealed, and the LLM narrates the result in plain English rather than exposing slot/layer metadata. Two-handed items occupy both hand slots. Container items (backpacks, pouches, pockets) hold other items inside them.

## What Was Implemented (2026-07-21)

### Engine — Complete

- `player.py` — `equipped` dict with 12 slots (head, neck, torso, arms, hands, legs, feet, back, waist, accessory, hand_left, hand_right). Each slot holds a stack (list of item node IDs). Added `base_description` field for baseline appearance.
- `virtual_world_engine.py` — `equip_item()`, `unequip_item()`, `get_visible_equipment()`, `get_full_equipment()`, `get_equipment_narrative()`. Two-handed item support with marker system. Drop auto-unequips. `get_item_desc()` now handles examining other characters (shows base_description + visible equipment).
- `app.py` — commands `wear`/`equip`, `remove`/`unequip`, `undress`, `strip`. Inventory command shows [WORN] items. Player update endpoint accepts `base_description`.
- Item editor: `equip_slots` (multiselect) in both item library and item inspector. `build_item_from_library` transfers `equip_slots`.
- LLM prompts and prompt-docs.js updated with equipment fields.

### Frontend — Done

- ✅ Paperdoll view with 12 body slots, tooltips, click-to-inspect, equip/unequip buttons
- ✅ Grid inventory with icons, weight badges, click-to-inspect, drop/equip buttons, add-item picker
- ✅ "Generate from Equipment" button (LLM-powered with code fallback)
- ✅ `POST /api/players/<name>/generate-description` endpoint

### Equipment Bonuses (2026-07-27)

- ✅ `engine/equipment_bonuses.py` — Tag-to-bonus aggregation module:
  - `defense` from `armor`/`clothing`-tagged items
  - `damage` from `weapon`-tagged items
  - `insulation` — temperature shift (sum of all equipped, shifts effective temp ±N°C)
  - `resistances` — tag-based: `fire_resistant`, `cold_resistant`, `toxic_resistant`, `magic_resistant`, `vacuum_sealed`
  - Custom `resistances` dict on items overrides tag defaults
- ✅ `tick_manager.py` — Effective temperature from `insulation` used for environmental checks and core temp drift; toxic air reduced by `toxic_resistant`
- ✅ `combat.py` — Target defense subtracted from weapon damage
- ✅ Library items updated: cleaver (weapon+damage), heavy_fur_lined_coat (defense+insulation+cold_resistant), boots (defense), EVA suit (armor+defense+insulation+vacuum_sealed)
- ✅ Equipment & Paperdoll, Combat System, Temperature System docs updated

### Fixes applied (2026-07-30)

- Fixed `CONDITION_HIERARCHY` naming mismatch: `"asleep"` → `"sleeping"` in `player.py` so `player.state` returns `"sleeping"` matching all engine checks
- Updated `test_unequip_empty_slot_raises_error` regex to match current error message `"Nothing equipped in your {slot}"`


## Equipment Slots

Each slot holds a **stack** of items. Stack order IS the layering — items worn first are closer to the skin, items worn later go on top.

| Slot | Max Stack | Examples |
|------|-----------|---------|
| `head` | 3 | Hat over bandana over circlet |
| `neck` | 2 | Scarf over necklace |
| `torso` | 5 | Bra → shirt → chainmail → jacket → cloak |
| `arms` | 2 | Bracers over sleeves |
| `hands` | 2 | Rings under gloves |
| `legs` | 4 | Panties → pants → greaves |
| `feet` | 3 | Socks → boots |
| `back` | 2 | Backpack over cloak |
| `waist` | 2 | Belt over sash |
| `accessory` | unlimited | Rings, earrings, piercings, watches |
| `hand_left` | 1 | Held items (sword, torch, shield) |
| `hand_right` | 1 | Held items |

## Item Properties for Equipment

Items declare equipment compatibility. Boolean properties (`two_handed`, `container`) are replaced by tags:

```json
{
  "name": "Chainmail",
  "equip_slots": ["torso"],
  "tags": ["armor"],
  "capacity_kg": 0
}
```

```json
{
  "name": "Greatsword",
  "equip_slots": ["hand_left", "hand_right"],
  "tags": ["two_handed", "weapon", "metal"]
}
```

```json
{
  "name": "Backpack",
  "equip_slots": ["back"],
  "tags": ["container", "leather"],
  "capacity_kg": 20
}
```

- `equip_slots` — which slots the item can be worn on (e.g. full plate could be `["torso", "arms", "legs"]`)
- `tags` — includes `"two_handed"` for two-handed items, `"container"` for containers
- `capacity_kg` — weight limit for contained items

## Tag-based Properties (2026-07-25)

Boolean properties `two_handed` and `container` have been removed from all code paths:

- Engine reads `"two_handed" in tags` instead of `item_node.properties.get("two_handed", False)`
- Frontend no longer renders `two_handed` checkbox or `container` checkbox
- Library editor converts any remaining legacy booleans to tags on display
- AI generation prompts instruct LLM to use `"two_handed"` and `"container"` as tags
- `build_item_from_library` and `build_item_legacy` routes use tag-based checks

## Multi-Slot Occupation (2026-07-25)

Items can occupy multiple body slots simultaneously (scuba suit covering torso+arms+legs, dress covering torso+legs, coat covering torso+arms+legs):

- Generalized marker system extends two-handed pattern: `__multi_{item_id}_{slot}`
- Equipping an item with `equip_slots: ["torso", "arms", "legs"]` fills all three slots
- Unequipping from any slot clears all linked slots
- Stack depth limits checked per-slot

## Engine Methods

### Data model (player.py)

```python
self.equipped: dict[str, list[str]] = {}  
# {"torso": ["item_bra", "item_shirt", "item_chainmail"], "legs": ["item_panties", "item_pants"]}
```

Item at index 0 = closest to skin. Last item = outermost.

### Core methods (virtual_world_engine.py)

- `equip_item(player, item_name, under=None)` — adds item to auto-detected slot. If `under` is specified (e.g. "under jacket"), inserts below that item in the stack. Auto-detects slot from item's `equip_slots`. If multiple slots possible, fills all.
- `unequip_item(player, slot=None, item_name=None)` — removes item from stack. For multi-slot items, removes from all occupied slots.
- `get_visible_equipment(player)` → returns outermost items per slot (what others see at a glance).
- `get_full_equipment(player)` → returns all stacks (for own knowledge, search, intimacy).
- `get_equipment_narrative(player, viewer)` → plain English description.

### Commands

- `wear chainmail` — equip to auto-detected slot
- `wear chainmail under shirt` — equip with specific ordering
- `remove chainmail` — unequip by item name
- `remove from torso` — unequip top item from a slot
- `undress` — remove outermost layer from each slot
- `strip` — remove all equipment
- `inventory` — show equipped items (marked with [WORN]) and carried items
- `put key in backpack` — move item into a container item's contents
- `take key from backpack` — retrieve item from container

### Triggers

- `on_equip` / `on_unequip` — already exist in TRIGGER_TYPES. Fire when items are worn/removed.
- Items can have `on_equip` triggers for magical effects, stat adjustments, narrative messages.

## Create-Item Modal (2026-07-25)

The create-item modal (`static/js/ui/create-modal.js`) now includes:
- `equip_slots` multiselect with all 12 slot options
- `_collectFormData()` returns `equip_slots` array
- `generateWithAI('item')` populates `equip_slots` from AI response
- `build_item_legacy` route accepts and stores `equip_slots`

## Edge Model (planned)

See `task-105-edge-refactor.md` for the edge type refactor:
- `in` — item/character in room or container (replaces `location` + `contains`)
- `carried` — item in character inventory (replaces `carried_by`)
- `equipped` — item equipped on character (slot in edge properties)
