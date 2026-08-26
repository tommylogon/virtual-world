---
group: Trigger System
wiki: "[[Rules Engine/Triggers & Effects]]"
---

# Triggers: Success and Fail Messages

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: Implemented — 2026-08-06, verified in browser (Playwright) + live engine check pending full E2E. Fail message now displays in the editor when conditions exist and is wired to the location the runtime reads (`effects[0].params.fail_message`, trigger_system.py:1281-1283).

---

## Summary

Currently, triggers have a single "Message" field that displays regardless of whether the trigger's condition succeeds or fails. Triggers need separate success and fail message fields so that the game can give contextual feedback.

## Current State

In `item-library.js:_addTrigger()` (line 586-588), the trigger editor has a single message input:

```html
<label>Message</label>
<input type="text" id="trigger-message" placeholder="What happens..." style="width:100%;">
```

Both the frontend storage (`trigger.effect_params.message`) and the backend trigger processing only handle this single message. When a trigger condition is met, the message is shown. When not met, nothing is shown.

## Proposed Change

### Frontend (`item-library.js`)

Replace the single Message field with two fields if the trigger has a condition:

1. **Success Message** — shown when the condition is met and the effect fires
2. **Fail Message** — shown when the condition is NOT met (optional; if empty, no fail message is shown)

Update the trigger editor overlay to show both fields:

```html
<label>✅ Success Message</label>
<input type="text" id="trigger-success-msg" placeholder="What happens on success...">
<label>❌ Fail Message (optional)</label>
<input type="text" id="trigger-fail-msg" placeholder="What happens if condition not met...">
```

Update `_saveTrigger()` to store both as `effect_params.success_message` and `effect_params.fail_message`.

### Backend (`virtual_world_engine.py`)

Update the trigger processing engine to:
1. Check the trigger condition
2. If condition met: fire the effect, show success message
3. If condition NOT met: show fail message (if provided), do NOT fire the effect

### Display in Editor

Update `_refreshEditorWithTriggers()` to show both messages in the trigger list display.

## Audit

**Status**: Implemented — verified 2026-08-06 (browser + engine check)
**How to test**:
- Open the Item Library trigger editor. Add a trigger with a condition. Verify two message fields appear: "✅ Success Message" and "❌ Fail Message".
- Fill both, save. Verify the trigger list shows both messages.
- In-game: trigger the condition successfully — verify success message appears. Fail the condition — verify fail message appears (and no effect fires).

## Implementation (2026-08-06)

- `static/js/shared/trigger-editor.js`:
  - Success/fail message inputs now also load from `effects[0].params.*` (fallback) so previously-saved effect-param messages display.
  - `_collectData()` mirrors `success_message`/`fail_message` into `effects[0].params` — the location `trigger_system.py` actually reads at runtime (fail: :1281-1283, success: :1306).
  - Fail message group visibility now updates dynamically when conditions are added/removed (`_updateFailGroupVisibility()` hooked into `show()`, `_addLeafTo`, `_addGroupTo`, `_removeCondItem`, `_ungroupGroup`) instead of only at editor load.
- Related bug fix in `static/js/inspector.js` (edit-trigger button): trigger nodes are now actually created via `POST /api/graph/node` (previously `PATCH` 404'd, leaving orphan `triggers` edges whose target nodes didn't exist — making the edit button silently no-op). `_editTriggerFromNode` falls back to the edge's data copy when the node is missing, and saves keep node + edge properties in sync.

## Files Affected

- `static/js/shared/trigger-editor.js` — fail message display/visibility + message→effect-param wiring
- `static/js/inspector.js` — trigger node creation on add; edge-property fallback + node/edge sync on edit
