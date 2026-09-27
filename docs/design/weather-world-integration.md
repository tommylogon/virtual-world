# Weather ↔ World Integration

**Status:** design reference (data-first; the engine parts ship incrementally,
see §6)
**Related:** task-227 (forecast schedule), task-231 (wind), task-232 (air/wet),
task-234 (GM overrides), task-496 (grid→graph compiler), task-497 (biome
taxonomy), `docs/design/world-environment-taxonomy.md`,
`docs/virtualWorld/Environment/Time & Weather.md`,
`docs/virtualWorld/Environment/Temperature/*`

## Purpose

The forecast answers **"what is the weather right now"** for the whole map at
once. The painted world answers **"what is this place"**. Today the two are not
connected: nothing about the world feeds temperature, and nothing about
temperature ever reaches a surface, a movement cost, or a forage table.

This document fixes that connection **without adding a second world-state
representation**. The forecast stays an overlay; the world becomes its
baseline.

---

## 1. What already exists (measured)

| Subsystem | Where | What it does well |
|---|---|---|
| Forecast overlay | `engine/weather_forecast.py` | authored / deterministic / random / hybrid modes; `resolve()` merges a GM/trigger override over the schedule baseline |
| Override lifecycle | `virtual_world_engine.py:1251-1258` | `duration_ticks` countdown + auto-revert with a log line |
| Compose point | `engine/equipment_bonuses.py:130` | `effective_temperature()` folds ambient + insulation + wind chill + humidity in one place; humidity sign flips at 20 °C; four call sites share it |
| Heat propagation | `engine/environment_propagation.py:44` | heat flows through **open** ways, scaled by way insulation; exterior areas are infinite reservoirs; wind accelerates exchange |
| Heat sources | `environment_propagation.py:143` | lit `heat_source` items pull an area toward `target_temperature` |
| Air propagation | `environment_propagation.py:195` | smoke/toxic/stale creep through open ways, arriving `hazy` first |
| Item drying | `virtual_world_engine.py:1195` | wet items dry faster in wind, slower in humidity, never in flooding |
| Diurnal light | `engine/lighting.py:19-36` | `outdoor_light_for_hour()` — interpolated anchor table, the pattern to copy. **Gated on the `outdoor` tag, which the compiler never emits** (bug-54) |
| Moon | `weather_forecast.py:69` | deterministic 30-day phase driving night light. **Was never narrated: the block that rendered it raised `UnboundLocalError` into a bare `except`** (task-559, fixed) |
| State container | `area.py:8` | one `environment` dict per area: `light, temperature, air, smell, noise, weather, wind, humidity` |
| Weather prose | `engine/area_description.py` | added in task-559: one sentence per weather state, one per wind magnitude, and a time-of-day line — all gated on the open sky |
| Sky-time DC | `weather_forecast.py` | `WEATHER_TIME_DC` + `normalize_weather()` — the guess-time table, collapsed onto one vocabulary (task-559) |

This is good infrastructure. The shape is right: one state dict, one compose
function, one overlay, one propagation rule.

## 2. What is missing (measured)

1. **Outdoor temperature is one global number assigned from a hardcoded 21 °C.**
   `virtual_world_engine.py:1299-1301`:
   `env["temperature"] = round(21.0 + float(temp_mod), 1)`. Every exterior
   area on the map is the same temperature, always. A mountain and a valley
   are both 21 °C.
2. **No spatial dimension.** `forecast.apply_scope` is a two-way switch —
   `exterior` or `all` (`virtual_world_engine.py:1281`). That is not a field.
   An arctic north beside a tropical south is inexpressible.
3. **Light has a diurnal curve; temperature does not.** Compare
   `lighting.py:19-36` with the flat temperature above. Between forecast
   entries the world's temperature does not move at all.
4. **Seasons are theatre.** `season` is written by
   `tools/generate_scenario.py:337` and `tools/assemble_scenario.py:72` and is
   read **nowhere** in the backend. The only real season logic is
   `static/js/sky-scape.js:36-48`, which derives a season from `game_month` to
   colour the sky widget. Winter changes the sky and nothing else.
5. **Snow is a label.** `snowy` appears in exactly three places: the state list
   (`weather_forecast.py:26`), the light multiplier (`:49`), and a perception
   skill DC of 18 (`routes/action_handlers.py:483`). It does not accumulate, it
   does not change `surface`, it does not gate movement, it does not shift
   temperature.
6. ~~The weather light multiplier is dead data.~~ **Fixed (bug-54).**
   `WEATHER_LIGHT_MULT` had no readers, so a midday thunderstorm was as bright
   as a clear midday. `weather_light_mult()` is now the reader and
   `LightingSystem._own_light` scales the time-of-day curve by it.
7. **A painted world has no weather at all.** The compiler builds area tags
   from the biome record, and no biome in `data/worldpainter/biomes.json`
   declares `outdoor` or `exterior` — so for a WorldPainter world the forecast
   is skipped (`apply_scope`), the diurnal light curve never applies, and
   exterior areas are not heat reservoirs. `world_compile.py:670` computes the
   answer and discards it. See **bug-54**.
8. **Humidity has no source.** `HUMIDITY_STATES` is `dry/humid/wet/flooding`,
   and nothing in the engine ever transitions between them — they are asserted
   by a forecast entry or an override. There is no evaporation, no water
   cycle, no link to rivers or lakes.
9. **Wind has magnitude but no direction.** `WIND_STATES` is
   `none…hurricane`. No compass anywhere, so "wind from the north" is
   unrepresentable and there is nothing for a rain-shadow effect to attach to.
10. **Elevation never reaches temperature.** The compiler uses elevation as a
    description input only (`engine/world_compile.py:829`).
11. **Every tick clobbers authored temperature.** `_apply_forecast_env` runs
    each tick and overwrites `env["temperature"]`, while
    `environment_propagation.py` also writes it. A hand-set value cannot
    survive, so a **separate** base key is mandatory — not "just stop
    overwriting".
12. **Falsy-zero bug.** `if temp_mod:` / `if light_mod:`
    (`virtual_world_engine.py:1299, 1302`) are truthiness tests, so an authored
    `0` is silently ignored. Harmless only because 0 happens to equal the
    21 °C default; it becomes a real bug the moment the base is not 21.

## 3. The layering rule

Four layers, each writing only downward:

```text
world (authored, static)        →  env.base_temperature      identity + climate baseline
clock + season (derived)        →  diurnal / seasonal curve
forecast + GM override (delta)  →  temperature_mod, wind, humidity, weather
interior physics (simulated)    →  env.temperature            propagation, heat sources
presentation                    →  effective_temperature() + area_description
```

**Nothing at runtime ever writes `base_temperature`.** The world is the floor;
everything above modulates it. This is the project's "one copy of every truth"
rule applied to climate, and it is what keeps the forecast from becoming a
competing representation.

## 4. Two keys, two facts: `base_temperature` vs `temperature`

Exactly the split already used for `surface` (ground material) vs `floor`
(storey index) in `engine/world_grid.py`, and for `area.environment` (state) vs
`area.properties` (authored). One word, one fact:

- `base_temperature` — authored, optional, defaults to 21.0. The world's own
  contribution.
- `temperature` — simulated. Written by propagation, heat sources, and the
  forecast write.

## 5. Target model

```python
# engine/weather_forecast.py  (copy the shape of lighting._OUTDOOR_ANCHORS)
def outdoor_temp_for_hour(hour: int, season: str = "summer") -> int: ...

# virtual_world_engine._apply_forecast_env
base = float(env.get("base_temperature", 21.0))
if eff.get("temperature_mod") is not None:
    base += float(eff["temperature_mod"])
env["temperature"] = round(outdoor_temp_for_hour(hour, season) + base, 1)
```

Additive, backwards-compatible, no new engine module:

- **`base_temperature`** per area, authored or compiled.
- **A diurnal + seasonal curve** for the outdoor baseline. The anchor-table
  pattern already exists in `engine/lighting.py:19-36`.
- **`temperature_mod` as a real delta** (`is not None`, not truthiness).
- **`wind_direction`** — a compass string alongside the existing magnitude.
  Purely additive; opens the door to rain shadows later, nothing more.
- **Accumulating weather** — `snow_depth` (or a boolean) on the area, read by
  movement, `surface` presentation, and forage. Gives `snowy` a consequence.
- **A WorldPainter `climate` layer** (5 enum values: arctic / temperate /
  arid / tropical / alpine) that the compiler turns into
  `base_temperature`. It is *a way to fill in one field*, not a new subsystem.

## 6. Order of work

Each step is independently shippable, independently testable, and none requires
migrating an existing world — the default `base_temperature` of 21.0 reproduces
today's numbers exactly.

| # | Step | Area | Unlocks |
|---|---|---|---|
| 1 | `base_temperature` + diurnal/seasonal curve + `is not None` | environment | everything else |
| 2 | `season` read in the engine (move it out of `sky-scape.js`) | environment | real winter |
| 3 | `wind_direction` | environment | rain shadows, later |
| 4 | weather → world state (snow, movement, forage) | environment | weather that matters |
| 5 | WorldPainter `climate` layer → `base_temperature` at compile time | world | spatial variety |

Step 5 is last on purpose: it is the only step that touches the compiler, and
it is only worth building once step 1 proves the baseline is load-bearing.

The filed tasks, in order:

| Step | Task |
|---|---|
| 1 | task-553 — per-area `base_temperature` + the curve |
| 2 | task-554 — `season` read in the engine |
| 3 | task-555 — wind gets a direction |
| 4 | task-556 — weather reaches the world (snow, movement, forage) |
| 5 | task-557 — WorldPainter `climate` layer |

## 7. Open questions

- **Does climate change anything at runtime, or is it authoring scaffolding?**
  This gates how urgent step 5 is. Authoring-only means the layer can live
  entirely in the WorldPainter and never touch the engine.
- **Lapse rate:** how much does one storey / one cliff step shift temperature?
  Elevation exists per area but has never fed the model.
- **Is `season` a world-level fact, or does a painted climate region shift it?**
  The forecast is currently global-per-tick; per-area seasons are a much larger
  change and are out of scope until step 5 proves the need.
- **Snow: accumulate and decay, or a boolean?** Accumulation is better but
  needs a tick-level decay rule and save/load coverage.
- **Does humidity get a source** (water proximity, season) or stay authored?

## 8. Non-goals

- A second climate representation, or climate stored outside `area.environment`.
- Climate as an input to navigation, steering, or the LLM prompt (deferred).
- Per-area seasons.
- A procedural weather simulation. The forecast is authored / state-machine by
  design (task-227) and stays that way.

## 9. Adjacent, not covered here

The biome taxonomy and the environment picker are a separate piece of work —
see `docs/design/world-environment-taxonomy.md`. Two dependencies worth noting
for that work: the 170 categories there are currently **prose**, not data
(`data/worldpainter/biomes.json` ships 16 biomes + 9 features), and climate fit
should be a 2D `temperature × moisture → biome` matrix rather than per-record
suitability ranges.
