# Environment Temperature

## Room Property

Stored as an integer in each room's `environment` dict:

```python
area_node.properties["environment"]["temperature"] = 21  # default: 21°C
```

| Property | Default | Range | Who writes it |
|----------|---------|-------|---------------|
| `base_temperature` | 21.0°C | no clamp | **the author** — a painted climate (task-557) or world data |
| `temperature` | 21°C | -50 to 100°C | **the simulation** — forecast, propagation, heat sources |

**Two keys because they are two different facts** (task-553). "This is a mountain
range" and "right now it is 6 °C" are not the same statement, and a save that
carried only the second would lose the first the moment a tick overwrote it.

Default for new areas is 21°C (room temperature). The `adjust_environment` effect clamps to -50..100, but the engine itself has **no clamp** on the value — volcanic caves at 200°C or dragon fire at 500°C work fine (drift just scales proportionally).

## The Outdoor Curve

`temperature` for an **exterior** area is not a literal any more. Each tick,
`virtual_world_engine._apply_forecast_env` computes:

```
temperature = base_temperature + temp_curve_for_hour(hour, season) + temperature_mod
```

- **`base_temperature`** — the area's own authored baseline, `21.0` when it has
  none.
- **`temp_curve_for_hour`** — the diurnal swing, an anchor table of
  `(hour, °C delta)` pairs interpolated, in `engine/weather_forecast.py`. It
  reaches −5 °C at 04:00 and +3.5 °C at 14:00: an 8.5 °C swing, deliberately
  shallow.
- **`temperature_mod`** — the forecast's own delta. A value of `0` is honoured
  (it says "no change"), not dropped as falsy.

**The curve is opt-in, and that is the compatibility guarantee.** It applies when
the area has a `base_temperature` **or** the world has a season. An area with
neither stays at a flat 21 °C — the number every world has always reported —
because simulating a diurnal swing around a *placeholder* would invent variation
nobody asked for, in every world that never chose a climate.

The season comes from the clock (`world.current_season()`): an authored
`world_state.season` wins, otherwise the calendar decides, so a world turns to
winter without a save or a reload. See task-554 and
`Time & Weather.md`.

## How It's Set

1. **Default** — 21°C for new areas
2. **Effects** — `set_environment` (absolute) or `adjust_environment` (incremental) triggers
3. **Manual editing** — Inspector panel or world data
4. **NPC behaviors** — NPC actions can call `set_environment`
5. **Climate paint** — a WorldPainter `climate` layer compiles to a per-area
   `base_temperature`, so a painted map has a temperature across it rather than
   one number everywhere (task-557)

## Heat Propagation

Temperature propagates between areas connected by open ways each tick via `propagate_temperature()` in `environment_propagation.py:24-69`. Areas tagged `exterior` act as infinite reservoirs — their temperature never changes, so an open door to the blizzard pulls the room's temperature toward the exterior temp. Closing doors stops propagation.

Wind in connected areas accelerates heat propagation (1.0× to 3.0× based on wind strength). See task-231.

Heat sources (`heat_source` tag with `target_temperature`/`heating_rate`) push room temp toward their target via `apply_heat_sources()` at `environment_propagation.py:110-149`, called before propagation each tick. See details below.

Tag an area as `exterior` via the area inspector's tag section or by adding `"exterior"` to `properties.tags`.

## Temperature-Producing Items

Toggleable items can modify room temperature through `environment_modifiers`:

```json
{
  "toggleable": true,
  "effect_target": "room",
  "environment_modifiers": {"temperature": 15},
  "uses": 200
}
```

When toggled on, the item adds its temperature modifier to the room's environment. These effects are tracked in `_item_active_effects` and synced across room changes.

### Common Items
- **Fireplace** — large temperature boost (heating)
- **Stove** — medium temperature boost (cooking + heating)
- **Torch/Candle** — small temperature boost (minimal)
- **Air conditioner / Fan** — negative temperature modifier (cooling)

## Heat Source Tag

Items with the `heat_source` tag and `target_temperature`/`heating_rate` properties actively heat their area via `apply_heat_sources()` in `environment_propagation.py:112-151`, called from `tick_manager.py:336-338`. Unlike `environment_modifiers` (instant toggle), heat sources apply gradual heating each tick toward their target.

```json
{
  "tags": ["heat_source"],
  "light_level": "normal",
  "heat_source_target": 25,
  "heat_source_rate": 0.3
}
```

Applied in: `engine/environment_propagation.py:112-151`, called from `engine/tick_manager.py:336-338`.

## Area Descriptions

Environment descriptions and temperature warnings use **effective temperature** (feels-like after insulation + wind chill + humidity), not raw ambient. Effective temperature is calculated in `equipment_bonuses.py`:

```python
eff_temp = ambient + insulation + wind_chill + humidity_mod
```

- Wind chill is resisted by item `wind_resistance` (0–100%)
- Wet insulation penalty is resisted by item `water_resistance` (0–100%)
- Humidity modifier: dry = 0, humid = +2/-1, wet = +3/-2, flooding = +4/-3

Warnings trigger at:
- `effective_temp < -5` — bitter cold warning
- `effective_temp < 5` — cold warning
- `effective_temp > 32` — heat warning
- `effective_temp > 40` — extreme heat warning

See [[Temperature/UI & Display]] for thresholds.

## Air Quality Interaction

| Air Quality | Effect |
|---|---|
| `"stale"` | Energy -1/tick |
| `"humid"` | Social -1/tick |
| `"toxic"` | HP -3/tick |

Hot + humid conditions are especially punishing (Thirst drain + discomfort).

## Key Code Locations

| Concern | File | Lines |
|---------|------|-------|
| Area environment default | `area.py` | 8-14 |
| Temperature propagation | `environment_propagation.py` | 24-69 |
| Apply heat sources | `environment_propagation.py` | 110-149 |
| Propagation + heat source call in tick | `tick_manager.py` | 320-325 |
| Environment trigger effects | `effects.py` | 278-308, 394-428 |
| Area descriptions | `area_description.py` | 141-175, 202-210 |
