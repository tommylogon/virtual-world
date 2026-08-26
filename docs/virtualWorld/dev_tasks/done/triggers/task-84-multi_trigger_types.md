# Multi Trigger Types Per Trigger — One Trigger, Multiple Fire Conditions

**Filed**: 2026-07-21
**Priority**: Medium
**Status**: In Review — completed 2026-08-05. Added `mode: 'multi'` to both inspector.js TriggerEditor.show calls (add at :279, edit at :352) — engine array support and item-library multi-select were already in place. Added 2 backend tests for array trigger_type (fires per listed type; skips unlisted types). Full suite: 490 passed, 1 skipped.

---

## Summary

Currently each trigger has a single `trigger_type` (e.g. `on_use`). A trigger should be able to fire on **multiple** trigger types — e.g. both `on_use` AND `on_examine`, or `on_open` AND `on_close`. This avoids duplicating the same effects/conditions across separate trigger entries.

## Example

Instead of two identical triggers:
```json
{"trigger_type": "on_use", "effects": [{"type": "message", "params": {"message": "The drawer rattles."}}]}
{"trigger_type": "on_examine", "effects": [{"type": "message", "params": {"message": "The drawer rattles."}}]}
```

One trigger:
```json
{"trigger_type": ["on_use", "on_examine"], "effects": [{"type": "message", "params": {"message": "The drawer rattles."}}]}
```

## Engine Changes

### `virtual_world_engine.py` — `_execute_triggers()` (line ~1405)

Change the trigger type filtering to support arrays:

```python
tp = trigger_edge.properties.get("trigger_type", "")

# Support multiple trigger types via array
if isinstance(tp, list):
    if trigger_type not in tp:
        continue
elif tp == "on_use_on" and target_name:
    # existing logic
    ...
elif tp != trigger_type and not (tp.startswith("on_use_on") and trigger_type == "on_use_on"):
    continue
```

Backward compatible — existing string `trigger_type` values work unchanged.

## UI Changes

### `inspector.js` — Edit Trigger overlay (line ~1294)

Replace single `<select>` with a **multi-select or checkbox group**. Options:
1. **`<select multiple>`** — simple, Ctrl+click for multiple selection, styled with `height: auto`
2. **Tag-based selector** — click "+Add type" to append chips, better UX but more code

The save function (`pullTriggerData`) must store `trigger_type` as:
- A **string** if only one type selected (backward compat)
- An **array** of strings if multiple selected

### `item-library.js` — Add Trigger overlay (line ~581)

Same change as inspector.js.

### Data migration

Existing triggers with string `trigger_type` continue working. New triggers with multiple types are stored as `trigger_type: ["on_use", "on_examine"]`.

## Files Affected

- `virtual_world_engine.py` — `_execute_triggers()` array support
- `static/js/inspector.js` — edit trigger overlay UI
- `static/js/item-library.js` — add trigger overlay UI
