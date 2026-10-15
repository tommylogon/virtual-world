---
type: task
status: todo
area: ui
priority: medium
---

# task-780: Expose requires_item, refusal_message and entry_phrase in the way inspector

**Filed:** 2026-10-11
**Related:** 

## What

The way inspector (static/js/inspector/way-view.ts) exposes current_state, pass_message, needs_open, auto_close, see_through, one_way, requires, max_size, sound_barrier and edge_length, but not requires_item, refusal_message or entry_phrase. All three are read by the engine (movement.py:507 requires_item, movement.py:579 refusal_message, area_description.py:696 entry_phrase) and shown to agents, so a way authored only through the inspector can never set a gear gate, a themed refusal, or a 'go down the tunnel' phrasing. Add them. Also reconcile the needs_open DC default: the checkbox saves 15 (way-view.ts:481) while the engine falls back to 10 (movement.py:594).

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Select a way → Inspector → way properties. Configure `requires_item`, `refusal_message`, `entry_phrase`, and `needs_open` on the same way record used by movement and area description.

Current availability: The card records that the way inspector exposes neighboring properties but omits these three engine-read fields; it also records a 15-versus-10 `needs_open` default mismatch. The editor additions are planned.

Live steps when available:
1. Open a scratch way between two areas and use the inspector's item picker to select a real key item; set a refusal message and an entry phrase, then save and reopen the way.
   - expected: all three values round-trip from the way properties without a second editor-only copy.
2. Attempt to traverse the way without the key, then carry the selected key and try again.
   - expected: the first attempt displays the authored refusal message; the second passes the `requires_item` gate when the existing movement rules allow it.
3. Travel through the way and inspect the destination area's exit description.
   - expected: the authored entry phrase is used in the ordinary area description for that route.
4. Toggle `needs_open` and inspect its default DC in the editor, then attempt the closed way.
   - expected: the editor and engine use the same documented default DC; the way still requires its existing open action before passage.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
