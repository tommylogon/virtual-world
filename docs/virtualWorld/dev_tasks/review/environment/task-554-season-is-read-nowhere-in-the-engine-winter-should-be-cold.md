---
type: task
status: review
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

## Acceptance

- [x] **One server-side month→season resolver**: `engine/weather_forecast.py`
      gained `SEASON_BY_MONTH`, `season_for_month()` and `resolve_season()`. It
      uses the same boundaries the old frontend table did (Dec-Feb winter,
      Mar-May spring, Jun-Aug summer, Sep-Nov autumn) — changing them would change
      what "winter" means in every existing world.
- [x] **The engine reads a season, and there is no path where one is ignored.**
      `world_state.season` is now consumed by the temperature model, so a scenario
      that says `"season": "winter"` and is otherwise identical to one saying
      `"summer"` is 11 °C colder at midday with no forecast entry changed.
- [x] **Precedence is decided and documented: an authored `world_state.season`
      wins over the clock.** A scenario stating a season is making a claim about
      its world and should not be overruled by whatever month the calendar is on.
      With none authored the clock decides, so a world crossing a boundary changes
      season **with no save and no reload** (checked: month 1 and 12 both resolve
      to winter from the clock alone).
- [x] **An unrecognised season falls through to the clock** rather than becoming a
      state the temperature model has no bias for. A broken save is still a
      readable world.
- [x] **`sky-scape.js` no longer carries a month→season table.** The
      `SEASON_BY_MONTH` const is deleted and the second, inline copy in the iframe
      `postMessage` is deleted with it — the duplicate that could disagree with
      itself. Both read `world.current_season()` through one helper.
- [x] **The engine ships its answer to the browser**, in
      `/api/settings/forecast` and the tick state, so the sky widget reads the
      engine's season rather than recomputing one. A month-based fallback remains
      only for the frames before the first state arrives, and it is the old table
      used for nothing else.
- [x] **Season changes are narrated** the way forecast entry changes are
      (`[Season] Winter arrives.`), so a world visibly turns to winter. The first
      tick does not narrate, so starting a world does not announce the weather.
- [x] **A month outside 1-12 clamps rather than raising**, because the same clock
      that hands the resolver a month also renders it.

## Notes

- **`world.current_season()` is the one entry point** — the temperature model, the
  narration and the API payload all call it, so the engine and the browser cannot
  end up in different seasons. `resolve_season()` is the pure function under it,
  which is what makes the precedence table testable without a world.
- The season is a **bias on the shape**, not a temperature: winter is −7 °C on the
  curve, so a tropical base with a winter bias is still warm and a temperate base
  in winter is properly cold. That is why `SEASON_TEMP_BIAS` lives in 553's table
  rather than being a second temperature model here.
- `DEFAULT_SEASON` is `summer`, which is what the old frontend fell back to and
  what the shipping scenarios declare — so their temperature behaviour is
  unchanged.
