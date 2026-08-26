# Temperature System

Body temperature simulation tied to environment temperature, equipment insulation, and trigger effects. Affects HP, Energy, Thirst, and can cause death.

## Data Flow

```
Room Temperature (area_node.properties.environment.temperature)
  │  Default: 21°C
  │
  ▼
Effective Temperature (after equipment insulation)
  │  Shifted by `insulation` from worn clothing
  │
  ▼
Core Body Temperature (player.vitals.Temperature)
  │  Range: 25.0 – 45.0°C, Starts at 37.0°C
  │
  ├──→ Core temp drift (per tick, toward effective temp)
  ├──→ Core temp damage (per tick, based on deviation)
  ├──→ Death check (<30°C hypothermia / >42°C heat stroke)
  └──→ HP regen gate (blocked outside 35-39°C)
```

## Pages

- **[[Temperature/Environment Temperature]]** — Room temp property, defaults, heat sources (`heat_source` tag, `environment_modifiers`), heat propagation (none yet), air quality
- **[[Temperature/Body Temperature]]** — Core temp vital, drift mechanics (thresholds 5°C/35°C), damage table, death checks, exhaustion death, HP regen gate
- **[[Temperature/Equipment & Temperature]]** — Insulation stacking, effective temp formula, resistance tag, toxic air protection
- **[[Temperature/Trigger Integration]]** — `temperature_below`/`temperature_above` conditions, `set_environment`/`adjust_environment` effects, heat source examples
- **[[Temperature/UI & Display]]** — Vital bar colors, narrative tiers, environment description thresholds, graph heat overlay, UI panels

## Quick Reference

| What | Where |
|------|-------|
| Environment temp | `room.environment.temperature`, default 21°C |
| Core temp | `player.vitals["Temperature"]`, starts 37°C |
| Drift thresholds | Cold < 5°C, Hot > 35°C (effective temp) |
| Drift rate | `(threshold - eff_temp) × 0.02` per tick |
| Hypothermia death | Core temp < 30°C |
| Heat stroke death | Core temp > 42°C |
| Insulation formula | `eff_temp = ambient + insulation + wind_chill + humidity_mod` |
| Heat propagation | Temperature spreads between areas via open ways each tick (rate `heat.base_rate` = 0.05/tick, capped `heat.max_delta` = 2.0°C/tick — both tunable in Settings → Engine Config) |
| Description bands | 14 bands from -50°C to 60°C — `temperature_description()` / `temperature_warning()` |
| Feels-like in state | `player.feels_like` serialized by `WorldSerializer._compute_feels_like()` |

## Key Code Locations

| Concern | File | Lines |
|---------|------|-------|
| Player initialization | `player.py` | 71-78 |
| Core drift + damage | `tick_manager.py` | 196-275 |
| Death check | `tick_manager.py` | 185-192 |
| Exhaustion death | `tick_manager.py` | 138-149 |
| HP regen gate | `tick_manager.py` | 288-293 |
| Temperature propagation | `environment_propagation.py` | 24-69 |
| Apply heat sources | `environment_propagation.py` | 110-149 |
| Propagation + heat source call | `tick_manager.py` | 320-325 |
| Equipment bonuses | `equipment_bonuses.py` | 34-99 |
| Area environment default | `area.py` | 8-14 |
| Trigger effects | `effects.py` | 278-308, 394-428 |
| Trigger conditions | `trigger_system.py` | 557-597 |
| Temperature description (14-band) | `area_description.py` | `temperature_description()`, `temperature_warning()` |
| Feels-like serialization | `serialization.py` | `_compute_feels_like()` |
| Area descriptions | `area_description.py` | 141-230 |
| Vital detail API | `routes/players.py` | 361-432 |
| Frontend vital bar | `agent-view.js` | 233-275 |
| Frontend narrative | `agent-engine.js` | 790-798 |
| Frontend alerts | `ui-controller.js` | 118-119 |
| Graph heat overlay | `network-manager.js` | 375-386 |

## Related Tasks

- [[dev_tasks/review/environment/task-5-heat_propagation]] — Temperature spread between areas (done)
- [[dev_tasks/todo/environment/task-227-environment-forecast-schedule]] — Forecast schedule with weather/wind/temp mods
- [[dev_tasks/todo/environment/task-231-wind-system]] — Wind chill, wind resistance, wet insulation penalty
- [[dev_tasks/todo/environment/task-232-humidity-atmospheric-conditions]] — Humidity modifier on effective temp
- [[dev_tasks/todo/environment/task-233-area-status-system]] — Area statuses that modify temperature
- [[dev_tasks/review/environment/task-126-tag-based-light-and-heat-sources]] — Light/heat source tag system
- [[dev_tasks/review/characters/task-28-character_needs_system]] — Added the drift system
- [[dev_tasks/review/items/task-3-equipment_system]] — Added insulation + resistances
- [[dev_tasks/review/environment/task-18-fireplace_lighting_recipe]] — Fireplace as heat source example
- [[UI & Settings/Engine Config|Engine Config (task-304)]] — `heat.base_rate` / `heat.max_delta` are live tunables
