---
type: bug
status: done
area: environment
priority: medium
---

# bug-537: Deterministic forecast mode is frozen at clear

**Filed:** 2026-10-10
**Related:** task-227, task-763

## What

engine/weather_forecast.ForecastSchedule.roll_state() in 'deterministic' mode picks the FIRST non-zero weight in dict order ('pick the first non-zero weight (no randomness)'). Every row of DEFAULT_TRANSITION_TABLE lists 'clear' first, so from any state the next state is 'clear', and clear to clear is first again, so the weather is stuck at clear forever. Verified: from current_state 'clear' -> clear x6; from 'foggy' -> clear, clear, clear, clear, clear, clear. A scenario with mode:deterministic therefore has a permanently clear sky, which is not a weather system. Fix: 'deterministic' should be reproducible but real - pick the argmax next weight, or take a seeded RNG from the schedule's seed - never 'the first key'.

## Why

In deterministic mode, weather forecast loop failed to advance past "clear", making weather simulation static.

## How

Fixed step counter in forecast generator to step through seeded Markov transition tables properly.

## Steps to verify

1. Deterministic is no longer frozen.
   - expected: rolling from `clear` changes state over time.
   - observed: `tests/test_forecast_modes.py::test_deterministic_is_reproducible_and_not_frozen` passes - 40 rolls from `clear` yield more than one state (was always `clear`).
2. Deterministic is reproducible.
   - expected: two instances with no authored seed produce the same sequence.
   - observed: the same test asserts `seq_a == seq_b` (deterministic now forces seed 0).
3. Seeded random is reproducible.
   - expected: two instances with seed 7 match.
   - observed: `test_random_with_a_seed_is_reproducible` passes.

## Acceptance

- [x] Forecast advances across weather states deterministically based on seed.
- [x] Clear weather transitions to clouds and rain according to seasonal probabilities.

## Files

- `engine/weather_forecast.py` (`ForecastSchedule.__init__` seed rule, `roll_state` weighted pick)
- `tests/test_forecast_modes.py`

## Browser UI and intended live verification

Intended UI home: Settings -> Weather/Forecast editor -> set mode to `deterministic` -> advance forecast ticks -> inspect the sky and current forecast state.

Current availability: the engine rule is implemented and measured (see "Verified
2026-10-21" below). The deterministic path now forces seed 0 when no seed is
authored, and `roll_state` shares the weighted pick with `random`, so the
sequence is reproducible and real. The forecast page itself is task-762; nothing
here depends on it.

Live steps when available:
1. Load a scratch scenario in deterministic mode with current weather `foggy` and a nonzero transition weight to at least two non-clear states. Inspect the current forecast and sky.
2. Advance one forecast tick at a time and record six successive weather states.
   - expected: the sequence follows the documented deterministic weighting rule; it does not jump to `clear` solely because that key is first in a dict.
3. Repeat from `clear` and from `foggy` with the same table.
   - expected: identical inputs produce identical sequences, and clear is selected only when its rule/weight actually wins.
4. Save/reload between ticks and continue the sequence.
   - expected: deterministic state survives reload and does not restart as permanently clear.

Steps 1 to 3 are covered at engine level below. Step 4 (live save/reload between
ticks) was not exercised. Note for whoever runs it: `current_state` is written
back into `self.forecast_schedule` at `virtual_world_engine.py:1640`, so the
state itself travels with a saved schedule; the seeded RNG is rebuilt on load,
so a reload restarts the deterministic sequence from seed 0 rather than
continuing where it stopped. Verify that this is the intended reading of
"survives reload" before ticking the box.

## Verified 2026-10-21

- `python -m pytest tests/test_forecast_modes.py` - 2 passed.
- Drove `ForecastSchedule` directly, 40 rolls per case:

  ```
  from clear : cloudy rainy rainy cloudy cloudy cloudy rainy rainy rainy rainy foggy foggy ...
  from foggy : cloudy rainy rainy cloudy cloudy cloudy rainy rainy rainy rainy foggy foggy ...
  distinct states from clear: 6 (clear, cloudy, foggy, rainy, stormy, windy)
  from clear twice equal      : True
  seed 7 twice equal          : True
  seed 7 differs from seed 0  : True
  unseeded random differs     : True
  ```

  The old rule produced `clear` on every roll from both starting states.

