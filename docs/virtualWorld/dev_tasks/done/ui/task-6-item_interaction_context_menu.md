---
group: Equipment & Inventory
wiki: "[[Items & Inventory/Items Overview]]"
---
# Tab-Completion for Commands — Cycle Available Targets

**Filed**: 2026-07-17
**Updated**: 2026-08-13
**Priority**: Medium
**Status**: Completed

---

## Summary

Add Tab-key autocomplete to the command input that cycles through valid targets for whatever command verb is being typed. When the user types `take ` and presses Tab, it completes the next available item that supports `take`. Pressing Tab again cycles to the next one. Works for all commands where target completion makes sense.

This is a keyboard-first, text-adventure-native replacement for a GUI context menu. Instead of clicking a target, you Tab through what you can interact with.

## Design

### How it works

The user types a verb + space, then hits Tab:

```
> take                     [Tab]
> take brass_key           [Tab → cycles to next]
> take old_letter          [Tab → cycles to next]
> take candle_stick        [... wraps around]
```

The completion only activates after a recognised verb + space. If the user hasn't typed a verb yet, Tab does nothing (or inserts a tab character — default browser behaviour).

### When it applies

| Verb | Completes With |
|------|----------------|
| `take`, `get`, `grab` | Items in current area that have `take` in actions |
| `examine`, `search`, `inspect`, `check` | Any item in area + carried + exits |
| `use` | Items in inventory that have `use` in actions |
| `open`, `close` | Doors/exits in current area |
| `drop` | Items in inventory |
| `eat`, `drink` | Items with `eat`/`drink` in actions or matching tags |
| `toggle` | Items with `toggleable` tag |
| `attack` | Players in same area |
| `speak`, `say` | Players in same area |

### Tab cycle behaviour

1. User types `take ` (verb + space)
2. First Tab → appends first valid item name: `take brass_key`
3. Second Tab → replaces with next: `take old_letter`
4. Third Tab → next: `take candle_stick`
5. ...wraps around to start
6. Shift+Tab → cycles backwards
7. If the user starts typing after the space, Tab filters to items matching that prefix

### Backend

Add an endpoint `POST /api/autocomplete` that takes `{"verb": "take", "prefix": ""}` and returns:

```json
{
  "options": ["brass_key", "candle_stick", "old_letter"],
  "verb": "take"
}
```

The frontend caches the options list and cycles through it on repeated Tab presses, only re-fetching when the verb or prefix changes.

### Frontend

Add a `keydown` handler on the command input (`#command-input` or equivalent). On Tab:
1. Prevent default
2. If cursor is after a recognised verb + space, fetch autocomplete options (or use cached)
3. Cycle to the next option and replace the current partial text
4. On next Tab, cycle again

No new UI components needed — just the input field behaviour.

### Backend logic

`/api/autocomplete` iterates available targets in the current area/inventory and filters by:
- The verb's action requirements (item must have `take` in actions for `take`, etc.)
- The current prefix (if any)
- Player context (same area, lighting, state, etc.)

## Files Affected

- `static/js/main.js` — Tab key handler on command input
- `static/js/api.js` — add `getAutocomplete()` endpoint call
- `routes/action.py` — add `/api/autocomplete` route  
- `virtual_world_engine.py` — add `get_autocomplete_options(verb, prefix)` helper
- `tests/test_autocomplete.py` — test autocomplete endpoint & engine logic
