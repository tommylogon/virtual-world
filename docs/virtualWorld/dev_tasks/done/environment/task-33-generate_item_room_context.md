---
group: Agent AI & Behavior
wiki: "[[World Building/Rooms & Areas]]"
---

# Generate Item: Pass Area Description as AI Context

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: In Review — implemented (code-verified 2026-08-11). Item AI generation passes target room description via `_targetArea`/`roomDesc` (`item-library/ai-generation.js:175-178`), create modal via `main.js`.

---

## Summary

When generating an item via AI (from the create modal or item library), the room description is not passed to the LLM. This means generated items are generic and not thematically aligned with the room they're placed in.

## Current State

In `main.js:generateWithAI()` (line 308-311), the AI generation prompt for items is:

```js
const formatHint = '{"name":"...","description":"...","actions":"examine,take,use","uses":1,"weight":0.5,"hidden":false}';
```

The full prompt sent to the LLM is just the user's prompt + format hint. No room context is included.

In `item-library.js:generateWithAI()` (not shown fully), same pattern — the AI gets just the item-level prompt with no context.

## Proposed Change

### Create Modal (main.js)

When generating an item, detect the selected target room and include its description in the system prompt:

```js
const selectedRoom = document.getElementById('item-room')?.value;
const roomDesc = selectedRoom ? worldState.areas?.[selectedRoom]?.description : '';
const context = roomDesc ? `\nThis item will be placed in "${selectedRoom}": ${roomDesc}` : '';
```

Append this context to the system prompt or user message.

### Item Library (item-library.js)

When the library is opened for a specific room (`openForRoom`), the `_targetRoom` is set. The AI generation in the library modal should use this context.

### System Prompt Update

Update the system prompt to instruct the AI to generate items that fit the room's theme:

```
You are a procedural content generator for a horror adventure game. Generate an item based on the user's prompt.
The item will be placed in the following room: "{area_name}: {area_description}"
Respond ONLY with raw JSON matching the form fields. No markdown.
```

## Audit

**Status**: Ready to test
**How to test**:
- Open the create modal for an Item, select a target room. Type an AI prompt, ensure "🧠 Use world context" is checked. Click Generate. Verify the generated item matches the room's theme.
- Uncheck "Use world context", generate again. Verify the output is more generic (no room-specific styling).

## Files Affected

- `static/js/main.js` — add room context to item AI generation in create modal
- `static/js/item-library.js` — add room context to library's AI generation