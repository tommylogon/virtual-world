---
type: task
status: review
area: environment
priority: medium
---

# task-555: Wind gets a direction, not just a magnitude

**Filed:** 2026-09-27
**Related:** task-231, task-553

## What

Add a compass `wind_direction` alongside the existing `WIND_STATES` magnitude, so wind has spatial meaning. Purely additive; a prerequisite for any rain-shadow or weather-travel work later.

Design: `docs/design/weather-world-integration.md` §2.7, §5.

## Measured (2026-09-27) — wind is a number, never a bearing

`engine/weather_forecast.py:29-41` gives wind four encodings and not one of them is a direction:

```python
WIND_STATES = ["none", "breeze", "wind", "gale", "storm", "hurricane"]
WIND_SCALE = {"none": 0, "breeze": 1, "wind": 2, "gale": 3, "storm": 4, "hurricane": 5}
WIND_HEAT_MULT = {...}   # heat exchange multiplier
WIND_CHILL = {...}       # °C applied by effective_temperature
```

A search for a compass or bearing anywhere in the backend returns nothing. "Winds from the north" is simply not expressible.

What wind *does* do today is local:

- `environment_propagation.py:88-96` — wind multiplies heat exchange between two  connected areas, and the **stronger** of the pair wins.
- `virtual_world_engine.py:1200-1202` — wind boosts how fast wet items dry.

Both are good, and both are consistent with a single global reading of "how hard is it blowing right now". Neither needs a direction. But it means there is no spatial weather gradient at all: wind cannot blow *across* the map, and there is nothing for a rain-shadow effect to attach to.

## What to change

1. A `WIND_DIRECTIONS` vocabulary and an `env["wind_direction"]` key, written
   from the forecast alongside `wind`. Cardinal, matching the project's own
   compass handling in `engine/world_compile.py:405`
   (`_compass_direction`).
2. Decide the semantics: is `wind_direction` where the wind comes *from*
   (meteorological convention) or where it blows *to*? Pick one and document it
   in the code comment — this is exactly the kind of non-obvious fact that gets
   misread later.
3. Additive only: a world with no `wind_direction` behaves exactly as today.
   Do not fold direction into the existing `WIND_STATES` strings
   (`"gale northerly"`) — that would break every consumer listed above.

## Acceptance

- A forecast entry can set a wind direction, and the area reports it.
- Absent direction changes nothing about today's behaviour, including the
  `WIND_HEAT_MULT` and drying paths.
- The from/to convention is stated in a code comment, not just the task file.
- A wind direction round-trips through save/load.

## Deliberately not here

Rain shadows, weather travelling across the map, and orographic precipitation.
Those need per-area climate (task-557) before they are meaningful. This task only makes the fact representable.

## Verified (2026-10-10)

- `WIND_DIRECTIONS` is the same 8-word compass as `world_compile._COMPASS_BY_SIGN` — one vocabulary, not two; a test asserts the two sets match so they cannot drift.
- `normalize_wind_direction` accepts `N` / `ne` / `northwesterly` / `north` and returns `""` for unknown.
- A forecast entry or `set_forecast_override` can set `wind_direction`; `ForecastSchedule.resolve` merges it and `_apply_forecast_env` writes `env["wind_direction"]`.
- **Live:** `POST /api/settings/forecast-override {wind: gale, wind_direction: northeast}` → 470 of 629 open-sky areas reported `environment.wind_direction = "northeast"`.
- The **from** convention (meteorological) is documented in the `WIND_DIRECTIONS` code comment.
- Round-trips through serialization: `Node.to_dict()` carries `properties.environment.wind_direction`.
- Additive: the key is written only when the effective forecast sets it, so no direction means no change; `WIND_HEAT_MULT` and the drying path are untouched.
- UI: the World Sky override row gains a direction select (`#sky-override-wind-direction`).
- Tests: `tests/test_wind_direction.py` (5 passed); front-end gate green.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Forecast editor → set wind magnitude and compass `wind_direction` → load the affected area and inspect its environment description and `/api/state`.

Current availability: the card proposes direction alongside existing wind magnitude and requires a from/to convention and save/load support. Directional wind behavior is not claimed as implemented.

Live steps when available:
1. Set wind magnitude to a nonzero value and direction to north in the Forecast editor; inspect the area's report.
   - expected: the area reports the documented direction convention and magnitude; the UI does not infer direction from magnitude alone.
2. Change only the direction to south and repeat.
   - expected: direction changes while magnitude, `WIND_HEAT_MULT`, and drying behavior remain unchanged.
3. Save/reload the scenario and inspect the forecast entry and area report.
   - expected: `wind_direction` round-trips with the forecast and remains distinct from the wind-state enum.
4. Remove `wind_direction` from a legacy fixture and inspect it.
   - expected: legacy behavior is unchanged and no direction is fabricated.

This section is not a claim that directional wind is implemented today.
