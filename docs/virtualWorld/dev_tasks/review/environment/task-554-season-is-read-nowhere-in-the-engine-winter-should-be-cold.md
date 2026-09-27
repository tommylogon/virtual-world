---
type: task
status: todo
area: environment
priority: high
---

# task-554: Season is read nowhere in the engine; winter should be cold

**Filed:** 2026-09-27
**Related:** task-553, task-227

## Goal

Move the season logic out of the sky widget into the engine, so the temperature
curve and narration know what season it is.

Depends on task-553 (the curve consumes the season).
Design: `docs/design/weather-world-integration.md` §2.4, §7.

## Measured (2026-09-27) — `season` is written by tools and read by nothing

A search for `season` across `engine/`, `routes/`, and
`virtual_world_engine.py` returns **nothing**. The only backend-side hits are
writers in fixtures:

- `tools/generate_scenario.py:337` — `"world_state": {"season": "summer", ...}`
- `tools/assemble_scenario.py:72` — `"season": "summer"`
- `tools/scenario_components/runtime_overrides.json:14`

The only place a season is actually *computed* is the frontend, from the month:

- `static/js/sky-scape.js:36` — `SEASON_BY_MONTH = [...]`
- `static/js/sky-scape.js:47-48` — `_season(state)` from `state.game_month`
- `static/js/sky-scape.js:218-228` — a second copy of the same table

So "winter" currently changes the colour of the sky widget and nothing else. No
temperature, no snow, no forage, no narration. A scenario can declare
`"season": "winter"` in its save file and the engine will never look at it.

Two copies of the month→season table in one JS file is also a duplication bug
waiting to happen: they can disagree, and the engine has no copy to arbitrate.

## What to change

1. One server-side month→season resolver, mirroring the existing
   `SEASON_BY_MONTH` boundaries. Prefer deriving it from `game_month` over
   reading `world_state.season`, because `game_month` is what the sky widget
   already trusts — but if `world_state.season` stays a supported override, say
   explicitly which one wins.
2. Feed the season into `outdoor_temp_for_hour()` (task-553) so winter is
   genuinely colder and summer warmer, rather than only a sky tint.
3. Make the frontend consume the engine's answer rather than recomputing it,
   so there is one table in the codebase.
4. Log or narrate a season change the way forecast entry changes are narrated
   (`virtual_world_engine.py:1269-1276`), so a world visibly turns to winter.

## Acceptance

- A scenario with `"season": "winter"` produces measurably colder outdoor
  temperatures than the same world in summer, with no forecast entry changed.
- The engine reads a season; there is no backend code path where a scenario
  can set a season and have it ignored.
- `sky-scape.js` no longer carries its own month→season table.
- Season is derived from the clock, so a world that crosses a season boundary
  without a save/load changes season.

## Files

- new resolver in `engine/weather_forecast.py` or the time module
- `static/js/sky-scape.js:36-48, 218-228` — delete the duplicated tables
- `docs/virtualWorld/Environment/Time & Weather.md` — season is now real
