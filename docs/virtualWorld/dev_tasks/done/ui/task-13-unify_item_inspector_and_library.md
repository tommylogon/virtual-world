---
group: Items & Crafting
wiki: "[[Items & Inventory/Items Overview]]"
---
# Unify Item Inspector and Library Editors

**Filed**: 2026-07-18
**Updated**: 2026-07-30
**Priority**: Low
**Status**: Implemented — pending review

---

## Summary

The two item editors evolved independently but have organically converged through other tasks. As of 2026-07-30:

| Feature | Inspector | Library |
|---------|-----------|---------|
| Tags (TagMultiselect) | ✅ | ✅ |
| State dropdown (current_state) | ✅ | ✅ |
| AI Improve | ✅ | ✅ |
| AI Generate | ❌ (use create-item modal) | ✅ |
| Trigger list with Edit/Remove | ✅ (InspectorTriggers) | ✅ (now matches) |
| Container contents | ✅ | ✅ |
| Save to / Refresh from library | ✅ | ✅ |
| Move to room/container | ✅ (n/a in lib) | — |
| Graph physics toggle | ✅ (n/a in lib) | — |

### What was done
- Refactored `item-library.js._refreshEditorWithTriggers()` to render trigger cards matching `InspectorTriggers.buildTriggersHtml()` — same card style, effect detail summary, condition display
- Added `_editTrigger(idx)` to library — re-opens TriggerEditor with existing data (previously only had Remove)
- Added `_buildEffectDetail(effects)` shared helper for consistent effect summary across both editors
- Generate is not a goal for inspector — the create-item modal handles that flow
- Both editors now use `TriggerEditor.show()` with the same effect/condition/trigger type lists

### Remaining non-goals
- Unlock edges management — obsolete, removed
- Graph physics toggle — doesn't belong in library
- Move to container — doesn't belong in library (templates aren't placed)