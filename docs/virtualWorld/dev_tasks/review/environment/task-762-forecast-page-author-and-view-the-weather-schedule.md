---
type: task
status: review
area: environment
priority: medium
blocked_by: [task-763]
---

# task-762: Forecast page: author and view the weather schedule

**Filed:** 2026-10-10
**Related:** task-227, task-229, task-231, task-234, task-555, task-556, task-758

## What

One surface to author and view forecast_schedule (task-227), extending the existing World Sky modal (static/js/sky-scape.ts) rather than building a second weather engine. The modal today shows the current sky, the next change and an override quick-set; it cannot edit the schedule entries. Add a timeline of the schedule entries laid out over the period granularity (hourly 1440 / weekly 10080 / yearly 525600 minutes, entries repeat), each editable in place (offset, weather, wind, temperature_mod, light_mod, air, message), plus mode (authored|deterministic|random|hybrid), seed and transition_table controls, over the existing GET/POST /api/settings/forecast. Columns must be honest: temperature is the derived effective outdoor value (base_temperature + diurnal/seasonal curve + climate + humidity/wind-chill), not an authored per-entry temperature; there is no precipitation model, so do not render mm; wind is magnitude only until task-555 gives direction. Random/deterministic modes are not enumerable ahead, so show the transition table rather than a fake dated forecast.

## Why

The schedule was authorable only by editing a scenario file or POSTing JSON: the
World Sky modal could show the current sky and set a one-shot override, but it
could not touch `forecast_schedule`. So the one surface a GM opens to see and
change the weather could not, in fact, change the weather's schedule.

## How

Extended the World Sky modal (`static/js/sky-scape.ts`) — no second engine:

- A **Forecast** row: `mode` (authored / deterministic / random / hybrid /
  **generated**), `granularity` (hourly / weekly / yearly), `seed`,
  `transition_interval`, `+ entry`, and `Save schedule`.
- A **timeline** bar over the period with a chip per entry (its position is the
  offset / period), and one editable row per entry: offset, weather, wind,
  wind_direction, humidity, temperature_mod, light_mod, air, message.
- A collapsible **transition table** textarea (JSON), validated on save — the
  honest view for the state-machine modes, which cannot be enumerated ahead.
- Save POSTs the same shape the route expects to `/api/settings/forecast`, and
  the route (task-763) now passes `area_overrides`/`date_overrides` through.

**Two departures from the card's field list, both because the live data demanded
them**: the rows carry `wind_direction` (task-555 shipped, so direction exists)
and `humidity` — the scenario's own entries already set `humidity`, and a row
without that field would have silently dropped it on save. The card's "no
precipitation model" is now stale: task-763 added it, so the note says so.

The box also had to become scrollable (`max-height:90vh; overflow-y:auto`): it
was `overflow:hidden`, and the new section sat below the fold on a short viewport
where it could not be reached at all.

A browser pass over the whole weather surface turned up **two more defects**,
both fixed here:

- **The stage disagreed with the top bar about the same moment.** With an
  authored spelling (`overcast`) effective at "now", the top bar read `overcast`
  while the sky stage read `Clear`: the stage's `weatherMap` keys on canonical
  ids, and the raw spelling fell through to the `'clear'` default. The widget now
  resolves the spelling through the engine's own alias map before the stage
  lookup, so both read the same value.
- **The `● override active` dot did not update when an override was set.** It was
  refreshed only by `_populateControls` (modal open or clock skip), not on a
  state update, so setting an override showed the new weather but no dot until
  the modal was reopened. It is now refreshed on every state update.

**The modal was then rebuilt as one surface** instead of two stacked ones. It
embedded `sky-atmosphere.html` — a 720-line console with its own header, time
slider and season/moon deck — and added a *second* header and three loose,
inline-styled control rows on top: two UIs, two headers, two time controls. The
embedded console is now reduced to a **scene-only hero** (a scoped stylesheet
injected into the same-origin iframe hides its chrome and lets the sky canvas
fill), and every control lives in a **card** built from the app's own design
tokens (`--bg-inset`, `--border`, `--accent`, `--font`): a labelled *Time & date*
card, an *Override* card with a single active-dot, and a *Forecast schedule*
card with a column-header row over the entry grid, a timeline on a real axis, a
styled empty state, and a footer readout. All wiring survived (element ids were
preserved); verified live, including no-scroll fit at 1600x900.

## Steps to verify

1. Run `python tools/ts_convert.py check` (build:ts, typecheck, lint,
   module:check, unit runner).
   - expected: gate green.
   - observed: gate green.
2. Run `python -m pytest tests/test_forecast_settings_route.py`.
   - expected: 2 passed — the schedule round-trips through the route and the
     generated field is exposed.
   - observed: 2 passed.
3. In a browser, open World Sky on a running world and edit the schedule.
   - expected: the editor populates from the live schedule; the row's weather,
     wind, wind_direction, humidity, temperature_mod, light_mod, air and message
     all survive a save; the override dropdown lists the registry's weather
     types (including the task-763 extremes).
   - observed (live): top bar renders (`08:58 · May 13, 2016 · quarter ·
     overcast · in 3h 2m: rain`); the stage reads `Overcast` matching the bar
     (was `Clear`); 3 entries load with their `humidity` (`dry`/`humid`/`wet`)
     intact; `+ entry` adds a row and `✕` removes it; Save →
     `POST /api/settings/forecast` **200**, status `✓ saved`, GET returns the
     entries unchanged; the override dropdown shows the 11 registry ids
     (`clear…snowy` + `blizzard`/`cold_snap`/`heatwave`/`thunderstorm`) and no
     alias spellings; setting an override flips the bar to `snowy` and shows the
     `● override active` dot, clearing hides it; the modal scrolls under a 600px
     viewport.

## Acceptance

- [x] One surface authors **and** views `forecast_schedule`, extending the World
  Sky modal rather than a second weather engine.
- [x] A timeline of the entries over the period granularity, each editable in
  place (offset, weather, wind, wind_direction, humidity, temperature_mod,
  light_mod, air, message).
- [x] `mode`, `seed` and `transition_table` controls.
- [x] Save/edit over the existing `GET`/`POST /api/settings/forecast`.
- [x] Columns are honest: the deltas (`temperature_mod`/`light_mod`) are what the
  author sets, the temperature shown in-game stays engine-derived, and the
  transition table is shown for the modes that cannot be enumerated ahead.
- [x] A save is lossless — no authored entry field is dropped.

## Files

- `static/js/sky-scape.ts` (+ emitted `.js`) — the token-based modal styles
  (`MODAL_CSS`), the scene-only stage embed (`STAGE_CSS`), the schedule editor,
  the registry-driven weather dropdowns, and the two display fixes.
- `routes/settings.py` — `area_overrides`/`date_overrides` passthrough and
  `weather_field` on the GET (task-763).
- `tests/test_forecast_settings_route.py` — route round-trip.
