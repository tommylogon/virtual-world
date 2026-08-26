---
group: Agent AI & Behavior
wiki: "[[World Building/Rooms & Areas]]"
---

# Area Generator: Pass Existing Rooms as AI Context

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: In Review — implemented (code-verified 2026-08-11). Existing rooms injected into AI area generation at `main.js:259-262`.

---

## Summary

When generating a room via AI, no context about existing areas is provided to the LLM. This means generated areas may be thematically inconsistent with the world, use duplicate names, or describe environments that don't fit the established setting.

## Current State

In `main.js:generateWithAI()` (line 310), the room generation prompt is:

```js
const formatHint = '{"name":"Area Name","description":"...","light":80,"temperature":21,"air":"fresh","smell":"musty","noise":"quiet"}';
```

The system prompt tells the AI to generate a room but gives no context about existing areas, their descriptions, or the overall world setting.

## Proposed Change

### Context Inclusion

Before the AI prompt, gather context about existing areas:

```js
const existingRooms = Object.entries(worldState.areas || {}).map(([name, data]) => {
  return `- ${name}: ${data.description || '(no description)'}`;
}).join('\n');
```

Include this in the system prompt:

```
Existing areas in this world:
- Foyer: A grand entrance hall with marble floors.
- Kitchen: A warm kitchen smelling of herbs.
- Library: Shelves of ancient books line the walls.

Generate a new room that fits thematically with these existing areas.
Respond ONLY with raw JSON matching the form fields. No markdown.
```

## Toggle Option

See separate task: `toggle_room_context_generation.md` — a toggle should control whether room context is included, since some users may want standalone generation.

## Audit

**Status**: Ready to test
**How to test**:
- Open the create modal, select Area, type an AI prompt, ensure "🧠 Use world context" is checked. Click Generate. Verify the generated room fits the existing world theme.
- Check the network request to the LLM — verify existing areas and their descriptions are included in the prompt.

## Files Affected

- `static/js/main.js` — add room context to AI generation in create modal