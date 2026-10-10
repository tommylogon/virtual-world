---
type: doc
tags: [system/environment]
---

# Weather System

Technical reference for how weather works in VirtualWorld *now*: the vocabulary,
the schedule, the seeded generator, how it reaches the world, and the readers
that give it consequences. Player/GM-facing usage is in [[Weather Guide]]; the
clock, calendar and lighting it rides on are in [[Time & Weather]].

Status: implemented, wired and authored. Vocabulary, per-area generation, snow,
the per-area write, and the Regions outlook have all shipped (task-231/232/234,
553–557, 762, 763, 772).

## Where the code lives

| Layer | File | What it owns |
|---|---|---|
| Vocabulary | `engine/weather_types.py` | Loads `data/library/weather/*.json` into `WEATHER_STATES`, `WEATHER_TIME_DC`, `WEATHER_LIGHT_MULT`, `WEATHER_PROSE`, `WEATHER_ALIASES`; `normalize_weather()`; `weather_state_kind()`; `weather_light_mult()`. |
| Forecast engine | `engine/weather_forecast.py` | `ForecastSchedule`; the generator (`generate_weather_field`, `conditioned_weights`, the season/terrain/climate bias tables, the extreme tail); `WEATHER_TUNING`; the snow model; moon phases; the temperature curve and season tables. |
| World integration | `virtual_world_engine.py` | `_forecast_tick`, `_weather_field_for_day`, `_area_terrain_index`, `_apply_forecast_env`, `weather_outlook`, `set_forecast_override`, `current_season`, `_calendar_dims`. |
| API | `routes/settings.py` | `GET`/`POST /api/settings/forecast`, `POST /api/settings/forecast-override`, `GET /api/settings/forecast/outlook`. |
| UI | `static/js/sky-scape.ts` (+ emitted `.js`) | The Sky Clock and the **World Sky** modal (Forecast and Regions tabs). |
| Readers | `engine/movement.py`, `engine/foraging.py`, `engine/area_description.py`, `engine/lighting.py`, `engine/environment_propagation.py`, `engine/equipment_bonuses.py` | Snow movement cost, snow forage DC, sky/ground prose, the light multiplier, heat and air exchange, effective temperature. |
| Content | `data/library/weather/*.json` | 11 records: `clear`, `cloudy`, `rainy`, `stormy`, `snowy`, `foggy`, `windy` + extremes `blizzard`, `cold_snap`, `heatwave`, `thunderstorm`. |

## 1. The vocabulary is library data (task-772)

A weather type is a record, not a branch. `engine/weather_types.py` reads
`data/library/weather/*.json` and derives the runtime tables:

- `WEATHER_STATES` — the canonical ids, in registry order.
- `WEATHER_TIME_DC` — the guess-time survival DC per id (`time_dc`, default 15).
- `WEATHER_LIGHT_MULT` — the daylight multiplier (`light_mult`).
- `WEATHER_PROSE` — the one-line description (`description`).
- `WEATHER_ALIASES` — read-time spellings → canonical id.

A record also carries `kind` (`normal` | `extreme`), an `icon`, an `order`, and
`tags`. Two derived facts the engine reads:

- `weather_state_kind(id)` — `"extreme"` for a tail-tier type. The generator
  treats every extreme as always-reachable (see §3).
- `weather_produces_snow(state)` — true for `snowy`, or for any record tagged
  `snow` (so `blizzard` accumulates snow without the engine knowing its name).

`normalize_weather()` is the one aliasing point: every reader (`area_description`,
the guess-time DC, the sky stage) normalises through it rather than keeping a
private list, so `overcast → cloudy`, `sunny → clear`, etc., cannot drift apart.
An unrecognised value stays unrecognised and falls through to each reader's
default instead of silently becoming `clear`.

`tools/weather_library_check.py` validates the records (fields, reachability from
the generator across seasons/terrain) — currently **11 records, 0 errors**.

## 2. The schedule (`ForecastSchedule`)

The schedule is the world's authored baseline, stored in
`world_state.forecast_schedule`.

**Modes** (`engine/weather_forecast.ForecastSchedule`):

| Mode | Behaviour |
|---|---|
| `authored` | `_entry_for_offset()` picks the entry whose `[offset, next_offset)` window contains the time, within a repeating `period`. |
| `deterministic` | `roll_state()` walks the `transition_table`. Always seeded (seed defaults to `0`), so the sequence is reproducible. |
| `random` | The same weighted pick, unseeded. |
| `hybrid` | Authored entries supply the base; `current_state` supplies the weather. |
| `generated` | The per-area field (§3) supplies the weather; the schedule supplies the seed/table/overrides. |

**Period** comes from `granularity`: `hourly` = 1440 min, `weekly` = 10080,
`yearly` = 525600. Entries repeat each period; weekly/yearly also shift the origin
by `game_day`.

**Override.** A separate `forecast_override` dict supersedes the schedule
(`set_forecast_override`). It is set from the UI or a trigger (`forecast_override`
effect) and carries `duration_ticks`; `_forecast_tick` counts it down and reverts
when it hits zero, logging `[Weather] The override wears off`. `resolve()`
overlays the override's `weather`/`wind`/`wind_direction`/`humidity`/
`temperature_mod`/`light_mod`/`air`/`blood_moon` on the schedule environment.

The forecast is a **delta overlay**, re-applied every turn — trigger
`set_environment`/`adjust_environment` effects are temporary and the forecast
baseline is what survives.

## 3. The generator (task-763)

`generate_weather_field(prev, areas, neighbours, *, table, season, seed, day,
coupling_bonus=2.0, climates=None)` produces one day's per-area weather:

- **Seeded and reproducible.** `random.Random(f"{seed}|{day}")`, areas iterated in
  sorted id order. The same world and day always give the same field; a different
  day differs because the seed string does.
- **Per area.** `areas` maps `area_id → tags` (open-sky only); `climates` maps
  `area_id → painted climate` (task-557).
- **Neighbour-coupled.** For each area, every neighbour already in a state adds
  `coupling_bonus` to that state's weight, so a front spreads across adjacent open
  ground instead of each area rolling in isolation.

Weights come from `conditioned_weights(current, table, season, terrain,
coupling)`:

```
weight(state) = table[current][state]          # the Markov row
              + season_bias[state]             # SEASON_WEATHER_BIAS
              + terrain_bias[state]            # tags + climate
              + coupling[state]                # neighbours
```

with two rules:

- **Additive, not multiplicative.** `snowy` is the proof: no row of
  `DEFAULT_TRANSITION_TABLE` transitions *into* it, so a multiplier on a weight of
  zero is still zero. Only an additive edge works — winter's `{"snowy": 5}` is
  what makes snow reachable.
- **The tail is folded in, never truncated.** Every id the library marks
  `extreme` is a candidate with a base `EXTREME_BASE_WEIGHT` (1.0) on top of its
  biases, clamped to `EXTREME_CAP` (6.0). A negative season/terrain bias can push
  it back to zero, so a summer blizzard or a desert heatwave stays sensible;
  `roll_from_weights` then draws from the **full** distribution.

`terrain_weather_bias(tags, climate)` sums every recognised tag's
`TERRAIN_WEATHER_BIAS` entry (mountains snowier, coasts foggy/wet, desert dry/hot)
and folds in `CLIMATE_WEATHER_BIAS` for the painted climate enum
(`arctic`/`alpine`/`temperate`/`arid`/`tropical`).

**Ordered overrides.** `apply_field_overrides(field, area_overrides,
date_overrides, day)` applies, lowest to highest: generated heuristic < **date
override** (replaces every area's state for that day) < **area override** (pins
one area over it).

**Cadence.** The live world rolls the field **once per game day**, not per tick:
`_weather_field_for_day(season)` caches on `self._weather_field` /
`self._weather_field_day`, seeded from the schedule's `seed` with the day folded
in, and reuses the previous day's field as `prev` (the coupling input).
`_area_terrain_index()` supplies `areas`/`neighbours`/`climates`: open-sky areas
(`is_open_sky`), neighbours found through area → way → area edges (`EDGE_CONNECTION`,
the same edges movement uses), and the compiled climate where painted.

**`WEATHER_TUNING`.** A state implies the rest of the environment, applied per
area at the write point (not globally) so a per-area field works:

| state | wind | humidity | temperature_mod | precipitation (mm/h) |
|---|---|---|---|---|
| clear | none | dry | +1.0 | 0 |
| cloudy | breeze | dry | 0 | 0 |
| windy | wind | dry | 0 | 0 |
| rainy | breeze | wet | −1.0 | 3 |
| stormy | storm | flooding | −2.0 | 8 |
| foggy | none | humid | −1.0 | 0 |
| snowy | breeze | dry | −3.0 | 4 |
| blizzard | hurricane | dry | −6.0 | 5 |
| thunderstorm | storm | flooding | −2.0 | 12 |
| heatwave | none | dry | +8.0 | 0 |
| cold_snap | breeze | dry | −8.0 | 0 |

Tuning applies only in the machine modes (`deterministic`/`random`/`hybrid`/
`generated`); an authored entry's own values win.

## 4. Applying to the world (`_apply_forecast_env`)

Each turn, `_forecast_tick` (task-227/234) runs, in order:

1. **Roll** the state machine at transition boundaries (machine modes).
2. **Count down** the override; auto-revert at zero.
3. Compute the effective environment (`sched.resolve`) and, in `generated` mode,
   the day's field (`_weather_field_for_day`).
4. **Apply** to areas (`_apply_forecast_env`).
5. **Narrate** an entry transition (`entry["message"]`) and a season change
   (`[Season] … arrives.`), each once.

`_apply_forecast_env(eff, field)` is where the **write order contract** lives.
For every area in scope (`apply_scope` = `exterior` | `all`; `exterior` means
`is_open_sky`):

```
base   = env.get("base_temperature", OUTDOOR_BASE_C=21.0)   # authored climate
curve  = temp_curve_for_hour(hour, season)                  # diurnal + season bias
delta  = curve + (temperature_mod  or  tuning.temperature_mod)
env["temperature"] = round(base + delta, 1)
```

- **Two keys, two facts.** `base_temperature` is authored climate and is **never
  written at runtime**; `temperature` is the simulated value, also written by
  `environment_propagation` and heat sources. A mountain base in winter is
  genuinely colder than a valley base; the forecast only modulates it.
- **Per-area weather.** `weather = field[area_id] or eff["weather"]`; wind and
  humidity follow the area's own state (tuning) when the machine is the source,
  and an explicit forecast value still wins.
- **Precipitation** is written only when it is falling (`> 0`) and popped
  otherwise, so a dry world gains no key.
- **Snow** (`advance_snow_depth`) is written only under the open sky and only
  above zero; the key is dropped when it melts away, so a world that never snows
  is unchanged.
- `light_mod` scales ambient light; `air` and `wind_direction` are written when
  present.

`is_open_sky(tags)` accepts both spellings of "outdoors" — `outdoor` and
`exterior` — reconciling the two historical tags (see bug-54). An unpainted world
(`base_temperature` absent, no season authored) reproduces its old flat 21 °C
exactly, which is the compatibility guarantee.

## 5. Snow (task-556)

Snow is a **depth** on the area (`environment.snow_depth`, cm), not the word
"snowy", so it lingers after the sky clears.

```
advance_snow_depth(depth, weather, minutes, precipitation=None)
  snow-producing weather : +rate * hours, rate = precipitation * SNOW_CM_PER_MM
                           (or SNOW_ACCUM_CM_PER_HOUR when precipitation is None)
  otherwise              : -SNOW_MELT_CM_PER_HOUR * hours
  clamped to [0, SNOW_MAX_CM=60], rounded to 0.01
```

Constants: `SNOW_ACCUM_CM_PER_HOUR=3.0`, `SNOW_MELT_CM_PER_HOUR=1.5`,
`SNOW_CM_PER_MM=0.8`, thresholds `SNOW_LIGHT_CM=2`, `SNOW_DEEP_CM=15`,
`SNOW_BURIED_CM=35`.

Readers:

- **Movement** (`engine/movement.py`): extra move Energy on arrival —
  `snow_movement_energy`: +1 / +3 / +6 at the light/deep/buried thresholds.
- **Foraging** (`engine/foraging.py`): extra search DC from
  `snow_forage_dc_penalty`: +2 / +4 / +6. The ground stays covered, so the search
  stays slow until it thaws.
- **Prose** (`engine/area_description.py`): `snow_depth_prose` narrates the ground
  from the depth, after the sky line.

## 6. Temperature, season and light

**Season is resolved in exactly one place** — `current_season()` →
`resolve_season(world_state)`: an authored `world_state.season` wins; otherwise
the clock's month decides via `SEASON_BY_MONTH`. The season is a **bias on the
temperature curve** (`SEASON_TEMP_BIAS`: winter −7, summer +4, spring +1,
autumn −1), not a temperature. `temp_curve_for_hour(hour, season)` returns the
diurnal delta from the anchor table plus that bias.

**Light** is the time-of-day curve (`engine/lighting.py`) scaled by
`weather_light_mult(weather)` — clear 1.0, cloudy 0.7, rainy 0.5, windy 0.8,
foggy 0.4, stormy 0.3 — so weather dims *daylight*, not a carried light source.
`OBSCURING_WEATHER` (`stormy`, `foggy`) also nullifies or halves the moon's night
bonus. Before bug-54 these values were dead data.

## 7. The outlook (task-762)

`VirtualWorld.weather_outlook(days=7)` is a **pure projection**: it rolls
`generate_weather_field` forward one day at a time from the current day, using
`self._weather_field` (copied) as the seed and each day's output as the next day's
coupling input. It **never writes** `self._weather_field` or the clock.

- Season is the engine's current season for every day: `world_state` is authored
  data the clock does not advance, so `current_season()` would answer the same on
  each future day — advancing the month here would invent a turn the sim does not
  make.
- Each day carries its date (`day`, `day_of_month`, `month`, `year`), the moon,
  the `states` map, and a `temps` map computed from the engine's own
  `temp_curve_for_hour(13, season)` + `weather_tuning` (a 13:00 daytime
  temperature).
- The payload: `{mode, generated, start_day, days[], areas[], tuning}`. It is
  served by `GET /api/settings/forecast/outlook?days=N` and rendered by the
  **Regions** tab. `generated` is the honesty flag — true only when the world's
  mode is `generated`, so the UI can badge a **live field** versus a **preview**.

## 8. API surface

| Route | Method | Purpose |
|---|---|---|
| `/api/settings/forecast` | GET | Schedule + active override + moon + date/season + `weather_field` (current-day field). |
| `/api/settings/forecast` | POST | Replace the whole schedule (including `area_overrides`/`date_overrides`); resets the caches. |
| `/api/settings/forecast-override` | POST | Set/clear the GM override; re-runs `_forecast_tick`. |
| `/api/settings/forecast/outlook` | GET | The N-day per-area projection (§7). |

## 9. Invariants and gotchas

- **One season source.** Only `current_season()` reads a season; the browser asks
  the engine rather than keeping a month→season table (task-554).
- **One vocabulary.** Every reader normalises through `normalize_weather()`; do
  not add a private alias list.
- **`base_temperature` is authored and never written at runtime.** The forecast is
  a delta layer on top of it.
- **The field is per *day*, not per *tick*.** Rolling it every tick churns the
  weather; `_weather_field_for_day` caches until `game_day` changes.
- **The outlook mutates nothing.** It copies the live field; opening the Regions
  tab cannot advance the world.
- **Preview vs live.** Off `generated` mode the field is a preview, and the UI
  says so.
- **Not modelled:** `visibility`, `pressure`, `elevation` (elevation feeds
  description/comparison, not temperature). `precipitation` *is* modelled.
- **Dual "outdoors" tag.** `is_open_sky()` accepts `outdoor` and `exterior`; the
  compiler historically emitted neither (bug-54), so hand-authored scenarios carry
  the tag explicitly.

## 10. Testing

| Test | Pins |
|---|---|
| `tests/test_weather_generator.py` | Seasonal/terrain edges, the extreme cap and gating, coupling maths, seeded per-area reproducibility, override precedence. |
| `tests/test_snow_accumulation.py` | Accumulation/decay, precipitation scaling, movement/forage thresholds, prose. |
| `tests/test_forecast_settings_route.py` | The schedule round-trips through the route; the field is exposed. |
| `tests/test_weather_types.py` | The library vocabulary, aliases, extremes. |
| `tests/test_weather_narration.py` | Weather/wind/time-of-day prose. |
| `tests/test_forecast_outlook.py` | The outlook is per-area, reproducible, honours overrides, advances the date, and never writes the live field or the clock. |

`tools/weather_library_check.py --check` validates the records;
`tools/weather_preview.py` renders the generator standings for eyeballing.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Light System]], [[Temperature System]], [[Time & Weather]], [[Weather Guide]]

<!-- connected:end -->
