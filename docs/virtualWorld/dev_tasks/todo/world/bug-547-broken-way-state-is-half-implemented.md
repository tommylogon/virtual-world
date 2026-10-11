---
type: bug
status: todo
area: world
priority: medium
---

# bug-547: broken way state is half-implemented

**Filed:** 2026-10-11
**Related:** 

## What

current_state 'broken' is offered by the inspector (STATE_OPTIONS, way-view.ts:25) and refuses open/close (movement.py:1118), but the traversal gate in move_to_area never tests it, so a broken way can be walked through; and engine/barriers.py has no broken rung, so it resolves to UNKNOWN_STATE_FALLBACK open (barriers.py:71) for light and sound. Either implement broken across the passage gate and both barrier tables, or remove it from the dropdown. See the States section of Ways.md.

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
