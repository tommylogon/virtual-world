---
group: Equipment & Inventory
---
# Equipment Description in Prompts Instead of Raw Slot List

**Filed**: 2026-07-29  
**Priority**: Low  
**Status**: Done � equip/unequip now triggers LLM auto-generation via frontend hook in api.js

---

## Summary

Replace the raw equipped-items slot list in prompts with a natural-language equipment description generated on equip/unequip.

### Current
```
Equipped: back: item_Backpack, feet: item_Stovepipe Leather Boots (Pair), legs: item_Reinforced Wool Trousers > item_Wool Blend Undershirt & Drawers > item_Clockwork Prosthetic (Left Leg)
```

### Target
```
Wearing a heavy fur-lined coat over a waxed canvas vest, with sturdy leather boots on your feet and a backpack slung over one shoulder. Your left leg is a clockwork prosthetic.
```

### Approach
The `engine/equipment.py` system already generates a description string on equip/unequip triggers. This string should be stored on the player object and surfaced in the prompt instead of the raw slot list.

### Scope
- `engine/equipment.py` — ensure description generation happens and persists
- `player.py` — add `equipment_description` field
- `static/js/agent/prompt-builder.js` — use equipment_description in `buildRoomContext()`
- Keep the raw slot list available as fallback/backup
