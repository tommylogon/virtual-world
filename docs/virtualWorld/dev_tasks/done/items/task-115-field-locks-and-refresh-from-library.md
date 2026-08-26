---
group: Items & Crafting
wiki: "[[Items & Inventory/Items Overview]]"
---

# Task 115: Field Locks + Refresh from Library

**Status**: In Progress
**Priority**: High
**Filed**: 2026-07-29
**Updated**: 2026-07-29

---

## Summary

**Field-level locking** lets you mark specific item properties as "locked" — they're preserved during AI Improve, Refresh from Library, and Sync to Library. Plus a **Refresh from Library** button that resets unlocked fields from the library template.

## Concept

Items gain a `locked_fields` array in their properties:

```json
{
  "description": "My custom description...",
  "triggers": [...],
  "insulation": 5,
  "locked_fields": ["description", "triggers"]
}
```

Locked fields are **never overwritten** by:
- ✨ Improve (AI generation skips them)
- 📚 Refresh from Library (keeps your custom values)
- 🔄 Sync to Library (preserved on the library side when syncing world→lib)

---

## Implementation

### 1. Field Lock UI (item-view.js)

Add 🔒 lock toggles next to each editable field in the item inspector:
- Description
- Actions
- Tags
- Triggers (lock/unlock all triggers)
- Insulation
- Resistances
- Defense/Damage (weapon stats)

Each toggle calls `api.updateNode()` to set/unset the field in `locked_fields`.

### 2. AI Improve respects locks (item-view.js)

`_improveItemWithAI()` currently regenerates: name, description, actions, uses, weight, hidden, tags, action_costs, skill_check. 

Modify to:
- Read `locked_fields` from node properties
- Strip locked fields from the prompt (don't send them to the LLM)
- Strip locked fields from the response (don't apply them even if LLM returns them)

### 3. Refresh from Library (items_registry.py + item-view.js)

**Backend**: `POST /api/items/<node_id>/refresh-from-library`
1. Find the library entry via `node.properties.library_id`
2. Load library item data from the registry
3. Remove old trigger edges + logic_trigger nodes
4. Rebuild triggers from library data
5. Copy unlocked properties from library to the graph node
6. Return updated node data

**Frontend**: Button in item inspector footer (alongside "Save to Library")
- Calls the new endpoint
- Refreshes inspector

### 4. Sync to Library respects locks (item-library.js)

`_saveToLibrary()` and batch sync check `locked_fields` on the world item. Locked properties on the world item are NOT overwritten in the library entry.

### 5. Sync from Library (future) respects locks

When refreshing the graph node from library, locked fields are preserved.

---

## Files to touch

| File | Change |
|------|--------|
| `static/js/inspector/item-view.js` | Lock toggles, refresh button, modify improve |
| `routes/items_registry.py` | POST /api/items/<node_id>/refresh-from-library |
| `static/js/item-library.js` | Sync-to-library respects locked_fields |
| `static/js/api-client.js` | Add refreshFromLibrary() method |

---

## Verification

1. Open item inspector → toggle lock on description
2. Click Improve → description stays unchanged
3. Click Refresh from Library → locked fields preserved, unlocked reset
4. Sync to Library → locked fields preserved on lib side
