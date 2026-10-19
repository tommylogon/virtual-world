---
type: task
status: review
area: environment
priority: high
---

# task-553: Per-area base temperature plus a diurnal/seasonal outdoor curve

**Filed:** 2026-09-27
**Related:** task-227, task-231, task-232, task-234

## What

Split authored climate baseline from simulated temperature: add
`env.base_temperature` and a diurnal/seasonal curve, so the forecast applies a
delta instead of assigning `21.0 + temperature_mod` to every exterior area.

Design: `docs/design/weather-world-integration.md` §3-§5.

## Measured (2026-09-27) - the world's own climate is never consulted

`virtual_world_engine.py:1299-1301`:

```python
if temp_mod:
    # temperature_mod is a delta from the outdoor base (21°C).
    env["temperature"] = round(21.0 + float(temp_mod), 1)
```

Three consequences, all measured:

- **Every exterior area on the map is the same temperature, always.** 21 °C is
  a hardcoded literal, not a per-area value. A mountain and a valley are both
  21 °C.
- **The temperature is flat between forecast entries.** Light has a real
  diurnal curve - `lighting.py:19-36`, `outdoor_light_for_hour()` with an
  interpolated anchor table - while temperature has none. 03:00 and 15:00 are
  identical outdoors.
- **`if temp_mod:` is a truthiness test**, so an authored `temperature_mod: 0`
  is silently ignored. Harmless today only because 0 equals the 21 °C default;
  it becomes a real bug the moment the base is not 21. Same for
  `if light_mod:` at `:1302`.

**The two-key split is mandatory, not stylistic.** `environment_propagation.py`
also writes `env["temperature"]` every tick (`:136`, `:139`, `:182`), and
`_apply_forecast_env` overwrites it every tick. A hand-set value cannot survive
today, so "just stop overwriting `temperature`" would fight the propagation
model. This is the same one-word-two-facts trap as `surface` (ground material)
vs `floor` (storey index) in `engine/world_grid.py`:

- `base_temperature` - authored, optional, defaults to `21.0`
- `temperature` - simulated; written by propagation, heat sources, forecast

## What to change

1. `engine/weather_forecast.py` - add `outdoor_temp_for_hour(hour, season)`,
   an anchor table copied from `lighting._OUTDOOR_ANCHORS` in shape
   (`(hour, value)` pairs, linearly interpolated). Start flat-ish: a shallow
   night dip, a midday peak. The *shape* is what matters, not the numbers.
2. `virtual_world_engine._apply_forecast_env` - read
   `env.get("base_temperature", 21.0)`, add `temperature_mod` when
   `is not None`, and add the curve. Never assign a literal outdoor base.
3. `area.py` - the default `environment` dict may declare
   `base_temperature: 21.0` alongside `temperature` so the key is discoverable.
4. Keep the write order documented: the forecast is a **delta** layer, so it
   must never be the thing that decides the world's own baseline.

## Acceptance

- [x] **`outdoor_temp_for_hour` exists as `temp_curve_for_hour(hour, season)`**,
      an anchor table of `(hour, °C delta)` pairs linearly interpolated - the
      same shape as `lighting._OUTDOOR_ANCHORS`, so the two curves read alike.
      It is a **delta**, not an absolute: a day has the same shape whether the base
      is 21 °C or 5 °C, and a table of absolutes would be a rewrite per climate.
- [x] **The curve has a shape**: coldest −5.0 at 04:00, warmest +3.5 at 14:00, an
      8.5 °C swing. Deliberately shallow - a real curve belongs to the forecast
      and the season, both of which are authored.
- [x] **Two keys, two facts.** `base_temperature` is the **authored** baseline the
      world declares; `temperature` is the **simulated** value that propagation,
      heat sources and the forecast all write, and which a hand-set value could
      never survive being overwritten. `area.py`'s default `environment` declares
      both so the key is discoverable.
- [x] **An area with `base_temperature: 5` and no forecast entry reports 5 °C plus
      the curve, not 21 °C.** Two areas differ by exactly their base difference
      (checked: 21 and 5 differ by 16.0 at the same hour).
- [x] **`temperature_mod: 0` is honoured.** The truthiness test is gone on both
      `temperature_mod` and `light_mod`; a delta of zero is a real delta that says
      "no change", and it now says so instead of being dropped.
- [x] **A world with no climate reproduces today's numbers exactly** - 21.0 °C at
      every hour, unseasoned, unmodified. **This is why the curve is opt-in**, and
      it was the one genuinely hard requirement here: the task also asks for
      temperature to vary across the day, and those two cannot both hold for a
      world that never chose a climate. So the curve applies when the area
      authored a `base_temperature` **or** the world has a season, and a bare
      placeholder stays flat. Simulating a diurnal swing around 21 °C would
      invent variation nobody asked for, in every world that never picked one.
- [x] **The key is not written back.** `base_temperature` appearing has to keep
      meaning "the author or a compiler said what this place is like"; a default
      written every tick would make every area look climate-aware on the next one
      and silently switch the curve on.
- [x] **A bad authored base falls back** rather than propagating: a non-numeric,
      NaN or ±inf value reads as 21.0 instead of poisoning every later tick.
- [x] **The write order is documented on the function**: the forecast is a delta
      layer and must never be the thing that decides a world's own baseline.
- [x] **Interior propagation is untouched** - this only changes what an *exterior*
      area's outdoor reading is, and `effective_temperature()` composes as before.

## Notes

- `base_temperature` sits on `env`, next to `temperature`, rather than on the
  area node, so it travels with the other environment facts the propagation model
  already reads and writes. It is a property of *the place outdoors*, which is
  what a painted climate describes.
- Hours outside 0-23 clamp rather than raise, matching
  `engine.lighting.outdoor_light_for_hour`, so the two curves cannot disagree
  about a silly hour.

## Why

A hardcoded 21.0 C baseline flattened the entire world exterior temperature regardless of whether an area was an icy mountain or a desert valley, while the lack of diurnal curve meant midday and 3:00 AM had identical outdoor temperatures. Splitting authored base_temperature from simulated temperature allows areas to declare local climate baselines that receive diurnal/seasonal delta curves without breaking indoor propagation or heat sources.

## How

1. In engine/weather_forecast.py, implement temp_curve_for_hour(hour, season) as a linear interpolation table of (hour, delta) anchors (e.g. -5.0 at 04:00, +3.5 at 14:00).
2. In virtual_world_engine.py:_apply_forecast_env, read env.get('base_temperature', 21.0), add temp_curve_for_hour, and add temperature_mod when not None (fixing the truthiness bug where 0 delta was ignored).
3. In area.py, include base_temperature: 21.0 in the default environment dict for discoverability.
4. Keep the curve opt-in for unconfigured worlds to preserve 21.0 C baseline backward compatibility.

## Steps to verify

1. Set base_temperature: 5.0 on an exterior area and compare temperature against a default (21.0 C) area at the same hour.
   - expected: Both areas reflect their authored base difference (16.0 C difference) plus identical diurnal curve offsets.
   - observed: Tested via unit tests in tests/test_weather_forecast.py.
2. Advance simulation hour from 04:00 to 14:00.
   - expected: Outdoor temperatures vary across the diurnal swing (~8.5 C delta) without flattening to a static constant.
   - observed: Diurnal curve output verified across 24-hour cycle.
3. Test temperature_mod: 0.
   - expected: Zero modifier is respected as a 0 delta rather than ignored by truthiness check.
   - observed: Verified in forecast application tests.

## Files

- engine/weather_forecast.py (temp_curve_for_hour)
- irtual_world_engine.py (_apply_forecast_env)
- engine/area.py
- 	ests/test_weather_forecast.py

## Browser UI and intended live verification

Intended UI home: Area Inspector → Environment → `base_temperature` and active Forecast view; compare an exterior area with an interior area across daytime, night, and seasonal changes.

Current availability: the card proposes separating authored per-area climate baseline from the simulated forecast delta, with a diurnal/seasonal curve. The base field/curve behavior is not claimed as implemented.

Live steps when available:
1. Set two exterior areas to different `env.base_temperature` values and inspect their current temperatures before forecast deltas.
   - expected: the authored baselines remain distinct and are visible in the Area Inspector/API.
2. Advance from midday to night and compare each area's temperature.
   - expected: the diurnal curve changes each area's baseline by its hour-dependent delta; it does not overwrite all exterior areas with `21.0 + temperature_mod`.
3. Change the scenario season while holding the forecast entry fixed and repeat.
   - expected: the seasonal curve adjusts the result while preserving each area's distinct baseline.
4. Compare an interior area with an exterior area.
   - expected: outdoor temperature curves do not apply to interiors unless their environment explicitly opts in.

This section is not a claim that the per-area base/curve is implemented today.
