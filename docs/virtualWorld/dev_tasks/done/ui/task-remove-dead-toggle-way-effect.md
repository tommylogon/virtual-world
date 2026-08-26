---
group: UI & Settings
---

# Remove Dead "Toggle Way" Effect Option

**Filed**: 2026-08-09  
**Priority**: Low  
**Status**: In Review — implemented 2026-08-09, `node --check` clean.

---

## Summary

The inspector's trigger-editor effect dropdown offered `🚪 Toggle Way` (`static/js/inspector.js`, both effect lists), but the engine has no such effect: `toggle_way` is missing from `EFFECT_TYPES` (`engine/trigger_system.py:47`) and has no `handle_toggle_way` in `engine/effects.py`. Selecting it produced a no-op (`[Unknown effect type: toggle_way]`) at runtime.

## Fix

Removed `{ value: 'toggle_way', ... }` from both effect lists in `static/js/inspector.js`. The real way-toggle commands (`movement.py:toggle_way`/`toggle_way_by_id`, open/close door commands) are unaffected. Door toggling from a trigger remains `set_state` (state open/closed), optionally guarded by a `state_equals` condition.

## Files Changed

- `static/js/inspector.js` — removed dead effect option (both lists)
