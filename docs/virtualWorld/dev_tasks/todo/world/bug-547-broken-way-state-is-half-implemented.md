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

## Browser UI and intended live verification

Intended UI home: select a `way` in the graph → Way Inspector → set `current_state` to `broken` → try passage actions and inspect area description, light, and sound across the way.

Current availability: the card records that `broken` is offered in the Inspector and blocks open/close, but movement still allows traversal and barrier lookup falls back to open. This incomplete state is not claimed as fixed.

Live steps when available:
1. In a scratch world, set a connected way to `broken` in its Inspector and attempt `go`/crossing from both connected areas.
   - expected: either the way is explicitly removed from the state selector, or the broken state consistently blocks passage according to the chosen design; it cannot look broken and still be traversable.
2. Stand on each side and examine the exit line.
   - expected: both directions describe the same broken passage state; no side presents it as open.
3. Put a light source and a sound source on one side and observe from the other.
   - expected: broken-state light and sound behavior follow the barrier tables, not `UNKNOWN_STATE_FALLBACK` open.
4. Save and reload the scenario, then inspect the way state and repeat traversal.
   - expected: the selected policy survives serialization and remains consistent across passage, light, and sound.

This section is not a claim that broken-way behavior is implemented consistently today.
