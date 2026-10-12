---
type: task
status: todo
area: environment
priority: low
wiki: "[[Weather System]]"
---

# task-798: Rename the weather forecast_schedule key and its identifiers to forecast

**Filed:** 2026-10-12
**Related:** task-227, task-762

## What

Finish the 'forecast schedule' -> 'Forecast' rename (Character Pursuits.md, Decisions 2026-10-12) at the IDENTIFIER level. The user-facing label pass is already done (docs, UI strings, tooltips, comments). Remaining scope: the world-state key `forecast_schedule` -> `forecast`; the POST body field `schedule` on `/api/settings/forecast` -> `forecast`; the Python class `ForecastSchedule` -> `Forecast`; and the sky-scape editor function names / element ids. Accept the legacy spellings on load so existing saves, scenarios and fixtures do not lose their weather.

## Why

"Schedule" now belongs to MOSIAC (the decision layer's Schedule letter). Left in code, `forecast_schedule` / `ForecastSchedule` / the `schedule` body field keep two meanings of the same word alive for every future reader and agent, which is exactly what the rename exists to remove. This is the deferred half of the decision; the surface already reads "Forecast".

## How

Rename the world-state attribute/key `forecast_schedule` -> `forecast`:

- `virtual_world_engine.py` (8 sites: `self.forecast_schedule`, including the `_apply_forecast_env` / `_forecast_tick` readers and the `current_state` writer at ~1625).
- `engine/serialization.py:391,804,805` (write `forecast`; on read accept `forecast` OR the legacy `forecast_schedule`).
- `engine/soak_runner.py:640`, `routes/settings.py:159,200`, `routes/action_handlers.py:207`, `tools/weather_preview.py:140`.
- Data: `data/scenarios/*.json` (7 files), `world_template.json` (repo root), `tests/fixtures/world.json`.

Rename the POST body field `schedule` -> `forecast` on `POST /api/settings/forecast` (`sky-scape.ts:1223,1236` and the `routes/settings.py` handler); accept the legacy `schedule` key for one release so an older client keeps working.

Rename the class `ForecastSchedule` -> `Forecast` (`engine/weather_forecast.py:658`) plus its users: the `sky-scape.ts` interface, `tests/test_forecast_modes.py`, `tests/test_wind_direction.py`.

Rename the sky-scape editor identifiers: `_renderScheduleEditor`, `_collectSchedule`, `_saveSchedule`, the `forecast_schedule?` interface field, and the `sky-sched-*` element ids.

Update the `world_state.forecast_schedule` references in `Weather System.md`, `Weather Guide.md` and `Time & Weather.md`.

Back-compat is the whole risk: `engine/serialization.py` must read the legacy key (a save written before the rename still carries it) and the route must accept the legacy body field. Prove it by loading one pre-rename scenario/save per branch.

Leave historical task cards and slugs (task-227, task-234, task-228, task-762) as the record; do not rewrite the past.

## Steps to verify

1. Legacy-key load keeps weather.
   - expected: a scenario/fixture carrying `forecast_schedule` (and a POST using the legacy `schedule` body) loads with its weather intact, and `GET /api/state` then exposes it under `forecast`.
   - observed: TODO
2. Round-trip through the route.
   - expected: `POST /api/settings/forecast {"forecast": {...}}` saves and `GET` returns it; the legacy `{"schedule": {...}}` body is still accepted.
   - observed: TODO
3. Live World Sky.
   - expected: the Forecast tab renders the saved forecast, the timeline and transport work, and switching to Regions does not move the clock.
   - observed: TODO
4. Grep is clean.
   - expected: `rg "forecast_schedule|ForecastSchedule"` returns only the back-compat read sites and the historical task cards.
   - observed: TODO

## Acceptance

- [ ] `GET /api/state` and every scenario store the forecast under `forecast`; nothing writes `forecast_schedule`.
- [ ] A pre-rename save/scenario restores its weather (back-compat read proven).
- [ ] `POST /api/settings/forecast` accepts `forecast` and still accepts `schedule`.
- [ ] The class is `Forecast`; the sky-scape editor functions and `sky-sched-*` ids no longer say "schedule".
- [ ] `tests/test_forecast_*`, `test_weather_generator.py`, `test_wind_direction.py` pass; `python tools/ts_convert.py check` is green.
- [ ] Docs reference `world_state.forecast`.

## Files

- `engine/weather_forecast.py` (class `ForecastSchedule` at 658)
- `engine/serialization.py` (391, 804, 805)
- `engine/soak_runner.py` (640)
- `virtual_world_engine.py` (8 sites)
- `routes/settings.py` (159, 200), `routes/action_handlers.py` (207)
- `static/js/sky-scape.ts`, `static/js/inspector/area-view.ts` (274)
- `tools/weather_preview.py` (140), `tools/weather_library_check.py` (36, comment)
- `data/scenarios/*.json` (7), `world_template.json`, `tests/fixtures/world.json`
- `tests/test_forecast_settings_route.py` (36), `tests/test_forecast_outlook.py` (31, 78, 79, 90, 119), `tests/test_weather_generator.py` (135), `tests/test_forecast_modes.py`, `tests/test_wind_direction.py`
- `docs/virtualWorld/Environment/Weather System.md`, `Weather Guide.md`, `Time & Weather.md`
