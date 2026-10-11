---
type: task
status: review
area: environment
priority: medium
related: [task-227, task-231, task-234, task-555, task-556, task-557, task-758, task-762, task-772]
---

# task-763: Weather generator: seeded, terrain-aware, dated weather field with date and area overrides

**Filed:** 2026-10-10
**Related:** task-227, task-231, task-234, task-555, task-556, task-557, task-758, task-762

<!-- deps:start -->
**Related:** [[task-227-environment-forecast-schedule]], [[task-231-wind-system]], [[task-234-trigger-environment-forecast-overrides]], [[task-555-wind-gets-a-direction-not-just-a-magnitude]], [[task-556-weather-reaches-the-world-snow-accumulation-movement-forage]], [[task-557-worldpainter-climate-layer-paint-a-coarse-climate-compile-it-to-base-temperature]], [[task-758-biome-records-add-climate-and-neighbour-fields-for-the-palette]], [[task-762-forecast-page-author-and-view-the-weather-schedule]], [[task-772-weather-types-are-a-closed-enum-make-them-per-scenario-data-enables-extreme-setting-specific-weather]]
<!-- deps:end -->

## What

A heuristic weather field a world can generate over a dated horizon (e.g. a month) and that the forecast view (task-762) reads. Seeded from the world so the horizon is reproducible. Per scope/area, terrain modifies the heuristic: reuse the existing thermal baseline (base_temperature, season, temp_curve_for_hour) plus the climate paint layer (task-557) and the biome/area tags the compiler already writes (world_compile.py), instead of a second climate model: elevation/mountain colder and snowier, coast wetter and foggier, forest humid, desert dry. Overrides are ordered patches with one precedence chain: area override > date override > generated heuristic > authored schedule > default. Extend engine/weather_forecast.py and world.forecast_schedule; the authored schedule becomes one input mode, not the whole system. New state only where the model genuinely lacks it: precipitation amount (there is no mm/accumulation field today) and wind direction (task-555, todo). This field is what task-762 renders and what task-556's effects consume; without task-555/556 the field is decorative.

## Why

This generator was already designed, in pieces, before this card. docs/design/weather-world-integration.md sets the layering rule (world -> clock+season -> forecast+override -> interior physics -> presentation), the base_temperature vs temperature split, and an ordered plan (task-553 base_temperature+curve, task-554 season, task-555 wind direction, task-556 weather reaches the world, task-557 climate paint layer). It also measures why a spatial field cannot exist today: outdoor temperature is one global 21 C applied to every exterior area, and forecast.apply_scope is a two-way exterior/all switch, not a field. The terrain vocabulary the heuristic needs is designed in docs/design/world-environment-taxonomy.md: 170 categories carrying Climate and Elevation fields and a temperature x moisture matrix, though only 16 biomes ship as data. The user's own notebook (docs/design/notebook-notes.md) already frames weather / temp / climate as map overlays plus a heightmap with a colour key to features and biomes. Correction: weather-world-integration.md Section 8 had listed 'a procedural weather simulation' and 'per-area seasons' as Non-goals, reading the forecast as authored / state-machine only. That was a misreading of the intended design, not a decision; the doc was corrected 2026-10-10 to record the heuristic generator as the target. Seeded heuristic generation of a dated, terrain-aware, per-area weather field is the actual intent; the authored modes are inputs to it, not the ceiling. Treat Section 7 (open questions: lapse rate, snow accumulate-or-boolean, humidity source) as the unresolved decisions this card inherits.

## How

Algorithm: a seeded, first-order Markov chain that already exists as ForecastSchedule.roll_state() over DEFAULT_TRANSITION_TABLE (engine/weather_forecast.py), keyed by the current weather state. Extend it three ways, and keep the roll on the FULL weighted distribution: never truncate to the top-N states for the roll itself, or tail states like snowy/stormy can never occur (show the top N in the view only). (1) Condition the weights on season: winter biases toward cloudy/snowy/windy, summer toward clear/stormy. (2) Condition on terrain per area: the area's biome tags, climate layer (task-557) and elevation - mountains cooler/snowier, coasts wetter/foggier, forest humid, desert dry. (3) Run the chain per area, not one global state, and couple neighbours so a front spreads to adjacent open areas and stalls or is blocked on ridges; independent per-area rolls read as checkerboard noise, not weather moving across the map. Cadence: roll once per day for a day-granularity horizon (the default of one tick would roll every tick and churn). Seeded from the world seed so a generated month is reproducible. Precipitation amount and snow accumulation stay new state (Section 7 open question); the chain yields a state, not millimetres.

Findings from the standalone preview (tools/weather_preview.py), 2026-10-10. (a) snowy is UNREACHABLE: no row of DEFAULT_TRANSITION_TABLE transitions into snowy, so no season or terrain multiplier can ever produce it (multiplying a base weight of zero is zero); a winter plus alpine month generated zero snow. Season and terrain must be able to ADD an edge, not only scale existing ones. (b) Extreme weather should be rare but reachable: a distinct tail tier - blizzard (snowy plus gale/hurricane wind), thunderstorm (stormy), heatwave (clear plus high temperature), drought, flood - with a low base probability that season and terrain may raise only up to a cap, so extremes stay surprising. This is the concrete reason the roll must never truncate the tail: the tail IS the extreme weather. (c) The state machine currently synthesizes only the weather field: current_environment() sets weather and nothing else, so wind, humidity and temperature are not driven by the state despite its docstring promising a per-state tuning table; a state should imply a wind magnitude, a humidity tendency and a temperature nudge. (d) The existing deterministic mode is separately broken - see bug-537.

## Outcome

Implemented, and it addresses all four preview findings:

- **(a) snowy reachable** — season and terrain now **add** a weighted edge; winter
  from `clear` gives `snowy` a weight the base table never had, and a 30-day
  winter field produces snow.
- **(b) extreme tail** — every registry state marked `kind: extreme` is a
  candidate (`EXTREME_BASE_WEIGHT`), raisable by season/terrain up to
  `EXTREME_CAP` and **suppressible to zero** by a negative bias (no summer
  blizzard, no desert thunderstorm); the roll is over the **full** distribution
  (never top-N), so the tail cannot be truncated away. Four climate-universal
  extremes ship as library content (`blizzard`, `thunderstorm`, `heatwave`,
  `cold_snap`); the *set* is still library data (task-772), so a world adds its
  own setting-specific ones (acid rain, sandstorm, ion storm, blood rain).
- **precipitation amount** — the state carries millimetres per hour
  (`WEATHER_TUNING[...]["precipitation"]`), written to open-sky areas only when
  falling, and read back to scale the snow rate, so heavy snow settles faster
  than light snow.
- **(c) state implies more than a word** — `WEATHER_TUNING` gives each state a
  wind magnitude, a humidity tendency and a temperature nudge, applied per area
  at the write point.
- **(d) deterministic mode** — fixed earlier under bug-537.

## Steps to verify

1. Run `python -m pytest tests/test_weather_generator.py`.
   - expected: 15 passed — the snow edge, terrain summation, the extreme cap and
     the season/terrain *gating* of extremes, the snow-tagged-extreme rule,
     precipitation scaling the snow rate, the painted-climate bias, the records
     being registered, the no-truncation roll, the seeded reproducible per-area
     field, neighbour coupling, a winter-month reachability check, override
     precedence, and the per-area application to `environment`.
   - observed: 15 passed.
2. Run `python tools/weather_library_check.py --report`.
   - expected: 0 errors, 0 warnings (11 records) — reachability now counts
     season, terrain and the extreme tail, not just the base table.
   - observed: 11 records, 0 error(s), 0 warning(s).
3. Run the environment/weather regression slice.
   - expected: no new failures.
   - observed: 202 passed (`area_description`, `clothing_environment`,
     `lighting`, `temperature_bands`, `weather_*`, `forecast_modes`,
     `forecast_settings_route`, `movement`, `foraging`).
4. Put a loaded world in `mode: generated` and tick it.
   - expected: one weather state per open-sky area, reproducible for the same
     seed/day, applied per area with matching wind/humidity/temperature.
   - observed: 7 open-sky areas, `clear`/`windy`/`stormy` distributed, identical
     on re-run, temperatures differing by state.

## Acceptance

- [x] Seasoned heuristic generation of a **dated, per-area** weather field, seeded
  from the world so the horizon is reproducible.
- [x] Terrain conditions the heuristic per area from the tags the compiler writes
  (mountains snowier, coasts foggier/wetter, forest humid, desert dry).
- [x] Season conditions the chain (winter -> cloudy/snowy/windy, summer ->
  clear/stormy); season and terrain may **add** an edge, not only scale one.
- [x] Neighbours are coupled so a front spreads rather than reading as
  checkerboard noise.
- [x] The roll is over the full distribution; extreme-kind states are a reachable
  tail, raised by season/terrain only up to a cap.
- [x] Overrides are ordered with one precedence chain: **area override > date
  override > generated heuristic > authored schedule > default**.
- [x] The authored schedule remains an input mode; `generated` is a new mode
  beside `authored`/`deterministic`/`random`/`hybrid`.
- [x] A weather state implies a wind, a humidity, a **precipitation amount** and
  a temperature nudge.
- [x] Rolled once per game day (the one-tick default would churn).
- [x] Four extreme types ship as content and are reachable, season/terrain gated.

## Files

- `engine/weather_forecast.py` — `SEASON_WEATHER_BIAS`, `TERRAIN_WEATHER_BIAS`,
  `CLIMATE_WEATHER_BIAS` (reads task-557's compiled `climate`),
  `EXTREME_BASE_WEIGHT`/`EXTREME_CAP`, `WEATHER_TUNING`, `SNOW_CM_PER_MM`, and the
  pure `weather_state_kind`, `terrain_weather_bias`, `conditioned_weights`,
  `roll_from_weights`, `generate_weather_field`, `apply_field_overrides`,
  `weather_tuning`, `weather_produces_snow`.
- `engine/weather_types.py` — `WEATHER_ALIASES` no longer folds `blizzard` into
  `snowy` or `thunderstorm` into `stormy` (they are their own types now).
- `data/library/weather/{blizzard,thunderstorm,heatwave,cold_snap}.json` — the
  extreme records (kind `extreme`).
- `virtual_world_engine.py` — `_area_terrain_index`, `_weather_field_for_day`,
  the day roll in `_forecast_tick`, and the per-area `_apply_forecast_env`
  (weather from the field; wind/humidity/precipitation/temperature from the
  area's state; precipitation feeds the snow rate).
- `routes/settings.py` — the forecast GET exposes the field; the POST passes
  `area_overrides`/`date_overrides` through and resets the field.
- `tools/weather_library_check.py` — reachability now counts season, terrain and
  the extreme tail.
- `tests/test_weather_generator.py` — mechanism and wiring.

## Intentionally not implemented

- **Elevation.** task-557 (done) deliberately did **not** restore a painted
  elevation layer — it was removed for meaning two things — so there is no
  elevation input for the generator to read. The compiled **climate**
  (`arctic`/`alpine`/`temperate`/`arid`/`tropical`, task-557) *is* read now, via
  `CLIMATE_WEATHER_BIAS`, alongside biome tags; `base_temperature` continues to
  drive the temperature write (task-553), not the weather heuristic.
- **Setting-specific extremes** (acid rain, ion storm, sandstorm, blood rain) are
  not shipped: they are global-library content and would appear in every world.
  A world authors them through the library (task-772) and the generator's tail
  picks them up with no code change.
- **Rendering the field** is task-762; this card produces and applies it, and
  exposes it on the forecast GET.
