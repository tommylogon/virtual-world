---
type: bug
status: review
area: environment
priority: medium
---

# bug-537: Deterministic forecast mode is frozen at clear

**Filed:** 2026-10-10
**Related:** task-227, task-763

## What

engine/weather_forecast.ForecastSchedule.roll_state() in 'deterministic' mode picks the FIRST non-zero weight in dict order ('pick the first non-zero weight (no randomness)'). Every row of DEFAULT_TRANSITION_TABLE lists 'clear' first, so from any state the next state is 'clear', and clear to clear is first again, so the weather is stuck at clear forever. Verified: from current_state 'clear' -> clear x6; from 'foggy' -> clear, clear, clear, clear, clear, clear. A scenario with mode:deterministic therefore has a permanently clear sky, which is not a weather system. Fix: 'deterministic' should be reproducible but real - pick the argmax next weight, or take a seeded RNG from the schedule's seed - never 'the first key'.

## Why

TODO

## How

TODO

## Steps to verify

1. Deterministic is no longer frozen.
   - expected: rolling from `clear` changes state over time.
   - observed: `tests/test_forecast_modes.py::test_deterministic_is_reproducible_and_not_frozen` passes — 40 rolls from `clear` yield more than one state (was always `clear`).
2. Deterministic is reproducible.
   - expected: two instances with no authored seed produce the same sequence.
   - observed: the same test asserts `seq_a == seq_b` (deterministic now forces seed 0).
3. Seeded random is reproducible.
   - expected: two instances with seed 7 match.
   - observed: `test_random_with_a_seed_is_reproducible` passes.

## Acceptance

- [ ] TODO

## Files

engine/weather_forecast.py (roll_state + __init__ seed); tests/test_forecast_modes.py

## Browser UI and intended live verification

Intended UI home: Settings → Weather/Forecast editor → set mode to `deterministic` → advance forecast ticks → inspect the sky and current forecast state.

Current availability: the card records that deterministic mode always chooses the first non-zero transition, and every default row puts `clear` first; observed sequences from clear and foggy both become clear repeatedly. The corrected selection rule is not claimed as implemented.

Live steps when available:
1. Load a scratch scenario in deterministic mode with current weather `foggy` and a nonzero transition weight to at least two non-clear states. Inspect the current forecast and sky.
2. Advance one forecast tick at a time and record six successive weather states.
   - expected: the sequence follows the documented deterministic weighting rule; it does not jump to `clear` solely because that key is first in a dict.
3. Repeat from `clear` and from `foggy` with the same table.
   - expected: identical inputs produce identical sequences, and clear is selected only when its rule/weight actually wins.
4. Save/reload between ticks and continue the sequence.
   - expected: deterministic state survives reload and does not restart as permanently clear.

This section is not a claim that the deterministic forecast bug is fixed today.
