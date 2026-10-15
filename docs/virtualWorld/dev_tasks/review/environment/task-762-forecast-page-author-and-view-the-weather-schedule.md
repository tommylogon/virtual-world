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

<!-- deps:start -->
**Blocked by:** [[task-763-weather-generator-seeded-terrain-aware-dated-weather-field-with-date-and-area-overrides]]
<!-- deps:end -->

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
card, an *Override* card with a single active-dot, and a *Forecast*
card with a column-header row over the entry grid, a timeline on a real axis, a
styled empty state, and a footer readout. All wiring survived (element ids were
preserved); verified live, including no-scroll fit at 1600x900.

**A second pass made the hero a real readout and added the outlook.** The stage
was raised to 238px, a **live environment strip** was added beneath it (Wind,
Humidity, Air, Temp, Light, Precip, Snow - read from the controlled player's
current area, so it shows real values rather than a placeholder), and a
**transport** row (Play day, Dawn/Noon/Dusk/Midnight, Now) drives the existing
schedule scrub. The embedded stage now takes its temperature from the same
engine value the strip shows, so the hero and the strip cannot disagree (they
read 25 vs 28 before).

The same pass added a **Regions** tab (a segmented toggle under the transport;
the hero and transport stay visible across both tabs). It renders a days x
per-area table - one row per open-sky area, one column per day, today first -
projected over the generated field by `VirtualWorld.weather_outlook()` and served
by `GET /api/settings/forecast/outlook`. The projection rolls
`generate_weather_field` forward one day at a time (each day's field is the next
day's coupling input) and **never writes** `self._weather_field` or the clock, so
opening the tab cannot advance the world. Each cell is the engine's weather word
and its tuning-derived daytime temperature (reusing `temp_curve_for_hour` and
`weather_tuning`, so the numbers are the engine's own, not the client's). A badge
says `live field` when the mode is `generated` and `preview - mode: <mode>`
otherwise, because in any other mode the sim follows the authored schedule and
the field is only a preview.

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
4. Run `python -m pytest tests/test_forecast_outlook.py`.
   - expected: 8 passed - the outlook is per-area, reproducible, honours the
     ordered overrides, advances the date, and never writes the live field or the
     clock.
   - observed: 8 passed.
5. In a browser, open World Sky and switch to the Regions tab.
   - expected: a days x per-area table with a mode badge; the clock does not move.
   - observed (live): **470 rows**, 8 header cells (Area + 7 days), **3760 cells**;
     badge `preview - mode: authored`; clock `08:58:00` before and after
     switching, so the tab did not tick; filter `Farm` narrows to 1 row; the tab
     toggle restores the Forecast view with its ribbon intact.

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
- [x] A live environment strip and a transport bar make the hero a real readout.
- [x] A **Regions** tab shows the next days per open-sky area, projected over the
  generated field, without advancing the world, with a badge distinguishing a
  live field from a preview.

## Files

- `static/js/sky-scape.ts` (+ emitted `.js`) — the token-based modal styles
  (`MODAL_CSS`), the scene-only stage embed (`STAGE_CSS`), the schedule editor,
  the registry-driven weather dropdowns, the two display fixes, the live stats
  strip and transport, and the Regions tab (`_switchSkyTab`, `_renderRegions`,
  `_regionsTable`).
- `virtual_world_engine.py` — `weather_outlook(days)` (the pure look-ahead over
  `generate_weather_field`) and `_calendar_dims`.
- `routes/settings.py` — `area_overrides`/`date_overrides` passthrough and
  `weather_field` on the GET (task-763); `GET /api/settings/forecast/outlook`.
- `tests/test_forecast_settings_route.py` — route round-trip.
- `tests/test_forecast_outlook.py` — the outlook projection.

## Browser UI and intended live verification

Intended UI home: Game menu → World Sky → Forecast tab for schedule editing; World Sky → Regions tab for the per-area outlook. Keep the sky stage, Time & date, Override, Forecast, and Regions controls on this one modal.

Current availability: The card records live verification of the schedule editor, weather override, scroll behavior, and Regions table, including a 470-row result and an unchanged clock when switching tabs.

Live steps when available:
1. Open World Sky → Forecast, change one entry's weather and humidity, click “Save schedule”, then close and reopen the modal.
   - expected: the edited row is still present with the chosen weather and humidity; the status shows saved and the stage/top-bar weather agree.
2. Set a weather override, then clear it.
   - expected: the top-bar `● override active` indicator appears while set and disappears when cleared; the weather label follows the selected value.
3. Open Regions and enter `Farm` in its filter.
   - expected: the table narrows to the Farm area, the badge identifies live field versus preview mode, and the world clock remains unchanged while the tab is open.
4. Scroll the modal to its bottom in a short viewport, then return to Forecast.
   - expected: the last Regions rows are reachable and the forecast controls remain usable.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
