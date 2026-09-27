---
type: task
status: todo
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

- An area with `base_temperature: 5` and no forecast entry reports 5 °C plus
  the curve, and **not** 21 °C.
- Two areas with different `base_temperature` values differ by that much at the
  same hour.
- `temperature_mod: 0` in a forecast entry is honoured (not ignored).
- A world with no `base_temperature` anywhere reproduces today's numbers
  exactly — this is the backwards-compatibility guarantee and it is why the
  default must stay `21.0`.
- Temperature now varies across the day without any forecast entry changing.
- Interior propagation still works: an open door to a cold exterior area pulls
  heat out, and `effective_temperature()` composes as before.

## Files

- `engine/weather_forecast.py` — the curve
- `virtual_world_engine.py:1278-1304` — `_apply_forecast_env`
- `area.py:8` — default dict
- `engine/equipment_bonuses.py:130` — unchanged, but confirm callers still pass
  the right ambient
- `docs/virtualWorld/Environment/Temperature/Environment Temperature.md` — the
  model changed; the doc must say so
