---
group: Environment & Climate
status: todo
priority: medium
filed: 2026-08-15
supersedes: [task-163-wind-environmental-enum.md, task-194-wind-water-resistance-insulation.md]
---

# Task 231: Wind System

## Summary

Add `wind` as an area environment property. Wind accelerates heat propagation, creates wind chill on effective temperature, drains Energy during exterior movement, and can extinguish light/heat sources. Wet clothing loses insulation effectiveness. Items can have `wind_resistance` and `water_resistance` as percentage values.

## Wind Enum

`environment.wind` values: `none` / `breeze` / `wind` / `gale` / `storm` / `hurricane`

Numeric scale for calculations: 0 / 1 / 2 / 3 / 4 / 5

## Effects

### Heat Propagation Acceleration

In `engine/environment_propagation.py`, wind increases the heat exchange rate:

```python
wind_mult = {"none": 1.0, "breeze": 1.2, "wind": 1.5, "gale": 2.0, "storm": 2.5, "hurricane": 3.0}
area_wind = float(env_a.get("wind", "none"))
rate = BASE_RATE * way_insulation * wind_mult.get(area_wind, 1.0)
```

Use the **stronger** wind of the two connected areas.

### Wind Chill on Effective Temperature

In `engine/equipment_bonuses.py`, extend `effective_temperature()`:

```python
def effective_temperature(ambient_temp: float, bonuses: dict, wind_level: str = "none") -> float:
    insulation = bonuses.get("insulation", 0)
    wind_chill = {"none": 0, "breeze": -1, "wind": -3, "gale": -6, "storm": -10, "hurricane": -15}.get(wind_level, 0)
    wind_resist = bonuses.get("wind_resistance", 0)
    resisted_chill = wind_chill * (1.0 - min(wind_resist / 100.0, 0.85))
    return ambient_temp + insulation + resisted_chill
```

### Wet Clothing Insulation Penalty

In `engine/equipment_bonuses.py`:

```python
wet_penalty = 0.7
water_resist = bonuses.get("water_resistance", 0)
resisted_penalty = wet_penalty * (1.0 - min(water_resist / 100.0, 0.85))
for item in equipped_items:
    ins = int(item.properties.get("insulation", 0))
    if item.properties.get("wet", False):
        ins = int(ins * resisted_penalty)
    total_insulation += ins
```

### Item Resistance Properties

Items can declare:
- `"wind_resistance": 50` — resists 50% of wind chill
- `"water_resistance": 30` — resists 30% of wet insulation penalty

These are **percentage values** (0–100). A raincoat might have `water_resistance: 80`, a windbreaker `wind_resistance: 60`, a leather jacket both at `40`.

Clothing can be both wet AND in wind simultaneously. The penalties stack independently:
1. Wind chill is applied, reduced by `wind_resistance`
2. Wet penalty is applied to insulation, reduced by `water_resistance`
3. Final value feeds into `effective_temperature()`

`set_environment` with `"rain"` or `"humidity": "flooding"` can set `wet: true` on equipped/equippable items via trigger effect.

### Energy Drain per Move (Exterior Areas)

In `engine/tick_manager.py`, when player is in an area tagged `"exterior"`:

```python
wind = env.get("wind", "none")
energy_drain = {"none": 0, "breeze": 0, "wind": 1, "gale": 2, "storm": 3, "hurricane": 5}.get(wind, 0)
if action_name in ("move", "dash") and energy_drain > 0:
    cost["energy"] = cost.get("energy", 0) + energy_drain
```

### Wind Extinguishing Light/Heat Sources

In `tick_turn()`, for lit items in exterior or windy areas:

```python
wind = env.get("wind", "none")
if wind in ("gale", "storm", "hurricane"):
    extinguish_chance = {"gale": 0.1, "storm": 0.3, "hurricane": 0.6}.get(wind, 0)
    if random.random() < extinguish_chance:
        item_node.properties["current_state"] = "unlit"
        # fire on_extinguished trigger
```

## Files Affected

1. `engine/environment_propagation.py` — wind multiplier on heat propagation rate
2. `engine/equipment_bonuses.py` — wind chill resisted by wind_resistance %, wet penalty resisted by water_resistance %
3. `engine/equipment.py` — track `wet` state on equipped items
4. `engine/tick_manager.py` — wind energy drain, wind extinguishing logic
5. `engine/effects.py` — `set_environment` / `adjust_environment` support `wind` key; `set_wet` effect for items
6. `engine/area.py` — add `wind` to default environment dict
7. `engine/serialization.py` — save/load `wind`, `wet`, `wind_resistance`, `water_resistance`

## Dependencies

- **Blocked by**: task-227 (forecast provides wind values)
- **Blocks**: task-232 (humidity + wet interaction)

## Testing

- Hurricane wind increases heat propagation rate 3x
- Wind chill lowers effective temp, wind_resistance reduces the penalty
- Wet coat contributes 30% of its normal insulation, water_resistance improves it
- Storm extinguish chance = 30% per tick for lit torches in exterior
- Hurricane energy drain = +5 per move action
