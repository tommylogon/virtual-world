---
type: task
status: review
area: environment
priority: high
---

# task-553: Per-area base temperature plus a diurnal/seasonal outdoor curve

**Filed:** 2026-09-27
**Related:** task-227, task-231, task-232, task-234

## Goal

Split authored climate baseline from simulated temperature: add
`env.base_temperature` and a diurnal/seasonal curve, so the forecast applies a
delta instead of assigning `21.0 + temperature_mod` to every exterior area.

Design: `docs/design/weather-world-integration.md` §3-§5.

## Measured (2026-09-27) — the world's own climate is never consulted

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
  diurnal curve — `lighting.py:19-36`, `outdoor_light_for_hour()` with an
  interpolated anchor table — while temperature has none. 03:00 and 15:00 are
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

- `base_temperature` — authored, optional, defaults to `21.0`
- `temperature` — simulated; written by propagation, heat sources, forecast

## What to change

1. `engine/weather_forecast.py` — add `outdoor_temp_for_hour(hour, season)`,
   an anchor table copied from `lighting._OUTDOOR_ANCHORS` in shape
   (`(hour, value)` pairs, linearly interpolated). Start flat-ish: a shallow
   night dip, a midday peak. The *shape* is what matters, not the numbers.
2. `virtual_world_engine._apply_forecast_env` — read
   `env.get("base_temperature", 21.0)`, add `temperature_mod` when
   `is not None`, and add the curve. Never assign a literal outdoor base.
3. `area.py` — the default `environment` dict may declare
   `base_temperature: 21.0` alongside `temperature` so the key is discoverable.
4. Keep the write order documented: the forecast is a **delta** layer, so it
   must never be the thing that decides the world's own baseline.

## Acceptance

## Acceptance

- [x] **`outdoor_temp_for_hour` exists as `temp_curve_for_hour(hour, season)`**,
      an anchor table of `(hour, °C delta)` pairs linearly interpolated — the
      same shape as `lighting._OUTDOOR_ANCHORS`, so the two curves read alike.
      It is a **delta**, not an absolute: a day has the same shape whether the base
      is 21 °C or 5 °C, and a table of absolutes would be a rewrite per climate.
- [x] **The curve has a shape**: coldest −5.0 at 04:00, warmest +3.5 at 14:00, an
      8.5 °C swing. Deliberately shallow — a real curve belongs to the forecast
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
- [x] **A world with no climate reproduces today's numbers exactly** — 21.0 °C at
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
- [x] **Interior propagation is untouched** — this only changes what an *exterior*
      area's outdoor reading is, and `effective_temperature()` composes as before.

## Notes

- `base_temperature` sits on `env`, next to `temperature`, rather than on the
  area node, so it travels with the other environment facts the propagation model
  already reads and writes. It is a property of *the place outdoors*, which is
  what a painted climate describes.
- Hours outside 0-23 clamp rather than raise, matching
  `engine.lighting.outdoor_light_for_hour`, so the two curves cannot disagree
  about a silly hour.
