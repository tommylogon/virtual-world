---
area: ui
wiki: "[[Items & Inventory/Items Overview]]"
type: task
status: done
priority: medium
---

# Unify Item Inspector and Library Editors

**Filed**: 2026-07-18
**Updated**: 2026-07-30
**Priority**: Low
**Status**: Implemented — pending review

---

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. Open a world item with tags and at least one trigger in the Item Inspector,
   then open the matching template in Library Browser.
   - expected: both editors show the same tag picker, current-state control,
     trigger summary, and Edit/Remove actions; the inspector also keeps its
     world-only move and physics controls.
   - observed: the card's 2026-07-30 implementation record says the two
     trigger-card renderers now match; no browser comparison is recorded.
2. Edit an existing trigger in Library Browser, save it, and reopen the entry.
   - expected: the same trigger editor opens with the prior condition/effect
     values and the saved card updates in place.

## Browser UI and intended live verification

Intended UI home: Graph → select an item → Item Inspector; Library menu →
Library Browser → Items → select the matching template.

Current availability: The card records both editors as implemented with
matching tag, state, trigger, container, AI Improve, and library-sync surfaces.
The feature comparison was recorded from code on 2026-07-30; a fresh visual
comparison is not recorded.

Live steps when available:
1. Open the same item as a world node and as a library template; compare its
   tags, state, trigger cards, and container contents.
   - expected: shared fields and trigger summaries use the same controls and
     labels; world-only move/physics controls remain only in the inspector.
2. In Library Browser, edit an existing trigger, save, reopen the item, and
   use Remove on a second trigger.
   - expected: Edit reopens the configured trigger and Remove deletes only the
     selected trigger; the inspector still offers the same trigger editor.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Acceptance

- [ ] TODO

## Files

- TODO
