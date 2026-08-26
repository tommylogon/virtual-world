---
group: Environment & Climate
wiki: "[[Environment/Light System]]"
---

# Fireplace Lighting Recipe

**Filed**: 2026-07-17
**Priority**: Medium
**Status**: Implemented / Ready for Review

---

## Summary

The fireplace in the Living Area is lightable by `use fireplace` when the player carries both **kindling** and **tinderbox**. Lighting it consumes the kindling, sets the fireplace state to `"on"`, and warms the room.

## What Was Implemented

### Engine Changes (`virtual_world_engine.py`)

Three new capabilities were added to the trigger system:

1. **`has_items` condition type** — checks the player has ALL items in an array (unlike `has_item` which checks a single item). Used by the lighting trigger to verify both kindling AND tinderbox are in inventory.

2. **`state_equals` condition improved** — previously only supported the format `"value": "node_id=state"`. Now also supports:
   - `{"target": "node_name", "value": "expected_state"}` — finds the node by name/id and checks its `current_state`
   - Fallback: when value has no `=` and no target, checks the current item node's own state

3. **`consume_item` effect type** — finds an item in the player's inventory by name and removes it (removes location/carried_by edges to the player, reduces uses, and removes the node if uses reaches 0).

### World Template Changes (`world_template.json`)

1. **Fireplace `current_state`** changed from `"unlit"` to `"off"` for consistency with the `"off"` → `"on"` state transition.

2. **Lighting trigger** (replaces old broken `on_use` trigger):
   - Conditions: `has_items: ["kindling", "tinderbox"]` AND `state_equals: target=fireplace, value=off`
   - Effects: `set_state` (fireplace→on), `consume_item` (kindling), `set_environment` (temp=22, light=80, noise=crackling fire, smell=woodsmoke), `message` (success text)
   - Fail message: "You need kindling and a tinderbox to light the fire."

3. **"Already lit" trigger** (new):
   - Conditions: `state_equals: target=fireplace, value=on`
   - Effects: `message` ("The fireplace is already burning.")
   - Edge ordered BEFORE the lighting trigger so it's processed first (prevents double-firing when lighting succeeds)

4. **On-tick trigger** (replaced old broken one):
   - Conditions: `state_equals: target=fireplace, value=on` AND `temperature_below: 28`
   - Effects: `adjust_environment` (temperature+1, "The fire crackles warmly.")
   - Note: only fires during `process_toggleable_items` — the fireplace is not a toggleable item, so this is dormant. Requires a toggleable system or dedicated tick handler to activate.

## Files Changed

- `virtual_world_engine.py` — added `has_items` condition, fixed `state_equals`, added `consume_item` effect
- `world_template.json` — updated fireplace triggers and state

## How to Test

1. Reset the world: `POST /api/reset`
2. Set active player to Lyrie: `POST /api/player/set` with `{"name": "Lyrie"}`
3. Move Lyrie to Living Area: `POST /api/players/Lyrie/move` with `{"room": "Living Area"}`
4. Move kindling to Living Area: `POST /api/graph/node/item_kindling/move` with `{"room": "Living Area"}`
5. Move tinderbox to Living Area: `POST /api/graph/node/item_Tinderbox/move` with `{"room": "Living Area"}`
6. Take kindling: `POST /api/action` with `{"action": "take", "target": "kindling"}`
7. Take tinderbox: `POST /api/action` with `{"action": "take", "target": "Tinderbox"}`
8. Use fireplace: `POST /api/action` with `{"action": "use", "target": "fireplace"}`

**Expected result:**
```
You use the fireplace.
fireplace is now on.
kindling is consumed.
The environment in Living Area shifts.
You arrange the kindling in the hearth and light it with the tinderbox. Flames crackle to life, casting a warm glow across the room.
```

**Test already lit:** Use fireplace again → shows "The fireplace is already burning."

**Test no items:** After reset, use fireplace without items → shows "You need kindling and a tinderbox to light the fire."

## Known Limitations

- `use kindling on fireplace` is not supported (kindling has no `on_use_on` trigger for fireplace). Use `use fireplace` instead.
- The on_tick trigger for gradual warming requires toggleable-item processing or a dedicated tick handler (existing limitation, not new).
- When fireplace is already lit AND player has no kindling, two messages show: "already burning" + fail message. Informs the player of both conditions.