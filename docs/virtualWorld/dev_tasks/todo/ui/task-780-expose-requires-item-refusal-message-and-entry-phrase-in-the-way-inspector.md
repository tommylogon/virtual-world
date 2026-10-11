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
