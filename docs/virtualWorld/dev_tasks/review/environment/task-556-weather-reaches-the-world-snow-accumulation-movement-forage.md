---
type: task
status: review
area: environment
priority: medium
blocked_by: [task-553]
---

# task-556: Weather reaches the world: snow accumulation, movement, forage

**Filed:** 2026-09-27
**Related:** task-232, task-553

<!-- deps:start -->
**Blocked by:** [[task-553-per-area-base-temperature-plus-a-diurnal-seasonal-outdoor-curve]]
<!-- deps:end -->

## What

Give snowy weather a consequence: accumulate snow on an area and let it change surface presentation, movement cost and forage, instead of being a label that only dims the light.

Depends on task-553 (snow needs a real per-area temperature to be worth
simulating).
Design: `docs/design/weather-world-integration.md` §2.5, §5.

## Why

A weather state that only dims the light is decoration: the forecast could say
`snowy` for a month and nothing in the world would differ from `foggy` except a
number in `WEATHER_LIGHT_MULT`. Snow should *settle* - be a thing the ground
carries, that slows a walk and hides a cache, and that lingers and thaws rather
than blinking out with the forecast entry that made it. That is what makes the
generated field (task-763) worth having, and it is what the design doc's layering
(world -> clock/season -> forecast -> interior physics -> presentation) implies.

## How

`engine/weather_forecast.py` owns the model: a depth in centimetres, an
accumulation and a melt rate, thresholds, and the pure helpers
(`advance_snow_depth`, `snow_movement_energy`, `snow_forage_dc_penalty`,
`snow_depth_prose`). The depth is written to
`area.properties.environment["snow_depth"]` - the block that already carries
`temperature` and `weather`, so it serialises with the node and needs no new save
path - for open-sky areas only, and only while it is above zero.

Three readers consult the **depth**, not the weather word: `move_to_area` charges
its energy, `find_or_spawn` adds it to the search DC, and `weather_description`
narrates it. So a clearing sky decays the snow over hours instead of wiping it.

## Measured (2026-09-27) — `snowy` is a string with three readers

Every occurrence of snow in the backend:

| Where | What it does |
|---|---|
| `engine/weather_forecast.py:26` | `snowy` is in `WEATHER_STATES` |
| `engine/weather_forecast.py:49` | `WEATHER_LIGHT_MULT` gives snowy `0.6` — it dims the light |
| `routes/action_handlers.py:483` | a perception skill DC of `18` for `snowy` — the same value as `foggy` |

That is the whole of it. Snow **does not accumulate**, does not touch
`properties.surface`, does not gate movement, does not change forage, and does not shift temperature. A blizzard and a fog bank are the same event with a different word. The world's own surface vocabulary has no winter in it.

The same is true of the other weather states in a weaker form: `rainy` and `stormy` reach the world only through humidity, which is itself only ever *asserted* by a forecast entry — there is no water cycle producing it.

## What to change

1. A per-area accumulated value (`snow_depth`, or a boolean if accumulation
   proves too heavy — see the open question below) written when the weather is `snowy`, and decayed when it is not. Exterior areas only, consistent with
   `_apply_forecast_env`'s `apply_scope`.
2. Read it where the world actually cares:
   - **surface** — presentation and the `properties.surface` material
   - **movement** — a cost or a rule, not just a longer DC
   - **forage** — `engine/foraging.py` already keys off area tags, so this is
     likely a tag effect rather than new code
3. Keep the accumulation on the *area*, not the weather state, so it survives a
   forecast change the way a real world does (snow does not vanish the moment
   the sky clears).

## Decision: accumulate, do not boolean

The acceptance below decides the open question for us: "clearing weather
**decays** snow rather than clearing it instantly" is a statement a boolean
cannot satisfy — a boolean has no partial state and no thaw rate. So the depth
is a float in centimetres, and it lives on the **area**, not the weather state,
so it survives the forecast entry that made it exactly the way real snow does.

Depth is written to `area.properties.environment["snow_depth"]` — the same block
that already carries `temperature` and `weather` — so it serialises with the
node and needs no new save path. The key is only written when the depth is above
zero and is **removed** when it melts to zero, so a world that never snows is
bit-for-bit unchanged.

## Steps to verify

1. Run `python -m pytest tests/test_snow_accumulation.py`.
   - expected: 14 passed — mechanism (accumulate/melt/clamp), the forecast write,
     the thaw removing the key, and both readers (movement energy, forage DC).
   - observed: 14 passed.
2. Run the touched-engine regression set (movement, foraging, weather narration
   and types, wind direction).
   - expected: no new failures.
   - observed: 130 passed.
3. Load a world, author `snowy` weather over 3 hours, then clear it.
   - expected: depth rises to 9.0 cm, then falls to 7.5 cm (decays, not wiped),
     and a long clear removes the key.
   - observed: in-process E2E — 9.0, 7.5, key gone; the loaded test world already
     ships a 36-tick `snowy` override, so its exterior areas pile up snow with no
     authoring change.

## Acceptance

- [x] Snowy weather over an exterior area changes what that area is like, not
  just how bright it is — it settles a depth the area carries.
- [x] Clearing weather decays snow rather than clearing it instantly — depth
  falls at `SNOW_MELT_CM_PER_HOUR`, and the key is dropped only at zero.
- [x] Movement and forage actually respond — deep snow adds move energy
  (`snow_movement_energy`) and raises the forage DC (`snow_forage_dc_penalty`).
- [x] A saved world reloads with its snow intact — depth is in
  `area.properties.environment`, serialised by `Node.to_dict`.
- [x] `dry`/`clear` worlds are bit-for-bit unchanged — the key is never written
  below 1 cm, and an interior area never gains it.

## Files

- `engine/weather_forecast.py` — the snow model: `SNOW_ACCUM_CM_PER_HOUR`,
  `SNOW_MELT_CM_PER_HOUR`, `SNOW_MAX_CM`, the depth thresholds, and the pure
  `advance_snow_depth` / `snow_movement_energy` / `snow_forage_dc_penalty` /
  `snow_depth_prose` helpers.
- `virtual_world_engine.py` — `_apply_forecast_env` advances the depth per
  open-sky area, per tick.
- `engine/movement.py` — `move_to_area` charges the destination's snow energy.
- `engine/foraging.py` — `find_or_spawn` adds the depth to the search DC.
- `engine/area_description.py` — `weather_description` narrates the depth.
- `tests/test_snow_accumulation.py` — mechanism, wiring and reader tests.
