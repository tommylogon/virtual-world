---
group: Equipment & Inventory
wiki: "[[Items & Inventory/Item States & Toggleables]]"
---

# Item Locked State — Lock Items, Block Contents Until Unlocked

**Filed**: 2026-07-17 (updated 2026-07-21)
**Priority**: High
**Status**: ✅ Complete

---

## Summary

Items need a `locked` state that blocks contents from being revealed until unlocked. Locked items **still fire triggers** (`on_examine`, `on_take`, `on_use`) — so examine can give extra info, and a trapped chest can activate on pickup. Only contents (items inside) are hidden until unlocked.

## What Was Implemented

### 1. `virtual_world_engine.py` — `get_item_desc()` (line ~1875)

Appends locked_message to description but **does not block triggers, skill checks, or available actions**. Only container contents are hidden when locked:

```python
if item_node.properties.get("locked"):
    locked_msg = item_node.properties.get("locked_message", "It's locked.")
    desc += f"\n{locked_msg}"

# ... skill checks run normally ...
# ... on_examine triggers fire normally ...

# Contents only revealed when unlocked
if not item_node.properties.get("locked"):
    content_items = []
    for ce in self.graph.get_edges_for_target(item_node.id, EDGE_CONTAINS):
        ...
```

When locked: shows description + locked_message + **triggers fire** (can add info). Contents stay hidden.

### 2. `virtual_world_engine.py` — `take_item()` (line ~2128)

**No locked check.** Locked items can be taken if their `actions` include `"take"`. The `on_take` trigger fires normally — enabling trap scenarios (e.g., pressure plate under a locked chest).

### 3. `virtual_world_engine.py` — Container search locked guard

Added locked container guards in **three search paths**:
- `take_item()` room container search (skips contents of locked containers)
- `take_item()` player inventory container search (skips contents of locked containers)
- `_find_item_node()` both room and player inventory container searches

### 4. `virtual_world_engine.py` — `use_item_on()` unlock flow (already existed)

The existing unlock flow at line ~2562 was already correct:
```python
if target_node and target_node.properties.get("locked"):
    lw = (target_node.properties.get("locked_with") or '').lower().replace('_', ' ').replace('-', ' ')
    ni = item_node.name.lower().replace('_', ' ').replace('-', ' ')
    if lw and lw == ni:
        target_node.properties["locked"] = False
        return f"You use the {item_name} on the {matched_item}. The lock clicks open!"
    elif lw:
        return f"You try to use the {item_name} on the {matched_item}, but the key doesn't fit."
```

### 5. `static/js/inspector.js` — Lock icon in room list

Area items list now shows 🔒 icon for locked items:
```javascript
`${i.properties?.locked ? '🔒 ' : '📦 '}${i.name}`
```

### 6. `static/js/inspector.js` — Locked_with + locked_message fields

Added to item inspector properties section:
- **Locked With (key name)** — text input for `locked_with`
- **Locked Message** — text input for `locked_message` (custom message when examining locked)

### 7. `static/js/main.js` — Lock icon in game output

Locked items show 🔒 in the game description panel.

### 8. `world_template.json` — Locked containers added

| Item | Area | Key | Content |
|------|------|-----|---------|
| `item_locked_chest` | Master Bedroom | `brass_key` (in grandfather clock) | `item_gold_coins` |
| `item_locked_cabinet` | Kitchen | `cabinet_key` (in Living Area, hidden) | `item_canned_food` |

## Item Properties Schema

```json
{
  "locked": true,
  "locked_with": "cabinet_key",
  "locked_message": "The cabinet is locked tight. You'll need a small key."
}
```

## Test Steps

### From a fresh reload (`Ctrl+R`):

1. **Find a locked item** — Go to Kitchen, `examine locked_cabinet` → shows description + "The cabinet is locked tight. You'll need a small key." + any `on_examine` triggers fire (if configured). Contents are NOT revealed.
2. **Take a locked item** — `take locked_cabinet` works if the item has `"take"` in its actions. The `on_take` trigger fires normally.
3. **Use a locked item** — `use locked_cabinet` fires `on_use` triggers normally (e.g., "It's locked, you need a key.").
4. **Find the key** — Go to Living Area, `take cabinet_key` (hidden but findable via room items list)
5. **Unlock with key** — Go back to Kitchen, `use cabinet_key on locked_cabinet` → "The lock clicks open!"
6. **Verify unlocked** — `examine locked_cabinet` now shows contents and actions normally
7. **Locked chest chain** — Examine grandfather clock → find brass key → take it → go to Master Bedroom → `use brass key on locked_chest` → unlocks
8. **Container search** — While locked, searching room/inventory does NOT reveal items inside locked containers

## Files Changed

- `virtual_world_engine.py` — `get_item_desc()` locked_message appended (triggers still fire), `take_item()` locked check removed, container search locked guards
- `static/js/inspector.js` — lock icon in room list, locked_with/locked_message fields in item inspector
- `static/js/main.js` — lock icon in game output panel
- `world_template.json` — locked chest (master bedroom), locked cabinet (kitchen), with keys and contents