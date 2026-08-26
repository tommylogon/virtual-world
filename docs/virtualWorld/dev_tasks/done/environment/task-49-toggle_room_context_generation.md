---
group: Agent AI & Behavior
wiki: "[[AI & Narration/Narration System]]"
---

# Toggle for Area Context in AI Generation

**Filed**: 2026-07-15
**Priority**: Low
**Status**: In Review — implemented (code-verified 2026-08-11). `gen-use-context`/`lib-gen-use-context` checkboxes in create-modal + item library (`create-modal.js:105/163/236`, `item-library/ai-generation.js:174/242`), read by `main.js:241/426`.

---

## Summary

Add a toggle/checkbox in the create modal and item library that controls whether AI generation includes context about the current room (for items) or existing areas (for areas). Some users may want standalone generation without context bias.

## Current State

Neither the create modal nor the item library has any toggle for context inclusion. Context is either always sent or never sent.

## Proposed Change

### Create Modal

Add a checkbox to both room and item create forms:

```html
<label>
  <input type="checkbox" id="gen-use-context" checked>
  🧠 Use room/world context for thematically correct generation
</label>
```

When unchecked, the AI prompt does NOT include context about existing areas (for room generation) or the target room (for item generation).

### Item Library Modal

Add the same checkbox to the library's AI generation UI (when generating via 🤖 in the library editor).

### Default

Default to **checked** (context included), since this is the more useful behavior for world-building.

## Audit

**Status**: Ready to test
**How to test**:
- Open the create modal for Area or Item — verify a "🧠 Use world context" checkbox exists and is checked by default.
- Open the Item Library, click Generate — verify a "🧠 Use room context" checkbox exists.
- Uncheck and generate — verify the AI prompt excludes room/world context.

## Files Affected

- `static/js/main.js` — check context toggle before including room context in prompts
- `static/js/item-library.js` — check context toggle before including room context in prompts
- `templates/index.html` — add toggle checkbox to create modal forms