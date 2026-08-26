---
wiki: "[[Items & Inventory/Items Overview]]"
---

# Task 108: Tags as Dicts with Type and Description

**Status**: Done (superseded by task-106)
**Priority**: Medium
**Filed**: 2026-07-26
**Closed**: 2026-07-27

---

## Summary

Tags are currently `list[str]` (e.g. `["food", "fruit"]` or `["two_handed", "metal"]`). Change them to `list[dict]` so each tag carries metadata inline:

```json
// Current (flat strings)
"tags": ["two_handed", "metal"]

// Target (rich dicts)
"tags": [
  {"name": "two_handed", "type": "mechanical", "description": "Requires both hands to wield"},
  {"name": "metal", "type": "material", "description": "Made of metal"}
]
```

This lets the system distinguish **category tags** (fantasy, magical, book, table — what the item *is* thematically) from **mechanical tags** (two_handed, equip_all_slots, toggleable — what the item *does* in the engine).

---

## Design

### Tag shape

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | str | yes | The tag identifier (e.g. "two_handed", "food", "magic") |
| `type` | str | no | Tag classification: `"mechanical"`, `"category"`, `"material"`, `"state"`, `"faction"`, etc. |
| `description` | str | no | Human-readable explanation of what the tag means |

### Backward compatibility

Old-style string tags auto-convert on load:

```python
# On deserialization, convert flat strings to dicts
if isinstance(tags, list) and tags and isinstance(tags[0], str):
    tags = [{"name": t} for t in tags]
```

Engine checks that currently do `"toggleable" in tags` change to:

```python
any(t.get("name") == "toggleable" for t in tags)
```

Or via a helper:

```python
def has_tag(tags, name):
    return any(t.get("name") == name for t in tags)
```

---

## Files to Touch

### Backend — Engine checks (16+ locations)

All locations that currently do `"<tag>" in tags` or `"<tag>" not in tags`:

| File | Lines | Tag(s) checked |
|---|---|---|
| `graph.py` | 101, 121, 141 | General `get_items_by_tag()`, `get_characters_by_tag()`, `get_tagged_items_in_area()` — currently does `tag in [t.lower() for t in node_tags]` |
| `engine/toggleable_items.py` | 26-28 | `"toggleable"` |
| `engine/equipment.py` | 108-113 | `"two_handed"` |
| `engine/trigger_system.py` | 618 | `"food"`, `"drink"`, `"openable"` in `_get_available_actions()` |
| `engine/item_actions.py` | 440 | `"food"`, `"drink"` |
| `engine/item_actions.py` | 230 | Tag display in inventory |
| `engine/traits.py` | 372, 419 | Area tags, inventory tag aggregation |

### Backend — Serialization

| File | What |
|---|---|
| `engine/serialization.py` | Both import paths (lines 297, 452) — ensure tags convert to dicts |
| `routes/items_registry.py` | Line 72 — `lib_item.get('tags', [])` used to build props |
| `routes/library_routes.py` | Lines 150, 213 — library item serialization |

### Frontend — Tag display and editing

| File | What |
|---|---|
| `static/js/item-library.js` | Tag display (line 171), tag editing (line 371), tag search (line 146), type icon derivation (lines 109-134) |
| `static/js/library-browser.js` | Character/room tag editing |
| `static/js/inspector/item-view.js` | Tag rendering and editing in inspector |
| `static/js/inspector/agent-view.js` | Character tag editing |

### Library JSON files

All item definitions in `data/library/items/*.json` — ~30+ files. Tags must be updated to dict format:

```diff
- "tags": ["food", "fruit"]
+ "tags": [{"name": "food", "type": "category"}, {"name": "fruit", "type": "category"}]
```

---

## Migration Strategy

1. **Add backward-compat shim** in deserialization (convert `list[str]` → `list[dict]` automatically)
2. **Add `has_tag()` helper** and replace all engine checks
3. **Update library JSON files** to use dict format (can be done incrementally — old format still works via shim)
4. **Update frontend** to read/write dict format
5. **Remove shim** after all data is migrated

---

## Relationship to task-106

Task-106 creates a **centralized tag library** (registry of tag metadata). This task changes the **inline tag shape** on entities. They complement each other:

- Task-106: `data/library/tags/flammable.json` → defines `{id, name, description, category, color, icon}`
- Task-108: Item tags become `[{"name": "flammable", "type": "mechanical"}]`

The inline `type` field on the entity tag can be auto-populated from the library's `category` field when the tag is registered. If a tag is not in the library, `type` defaults to `"custom"`.

---

## Commit History

| Commit | What |
|--------|------|
| | Add backward-compat shim + `has_tag()` helper |
| | Replace all engine tag checks |
| | Update frontend tag display/editing |
| | Update library JSON files |
