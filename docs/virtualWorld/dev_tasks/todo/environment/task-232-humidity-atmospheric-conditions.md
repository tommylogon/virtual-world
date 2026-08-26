---
group: Environment & Climate
status: todo
priority: low
filed: 2026-08-15
supersedes: [task-130-air-vacuum-atmospheric-effects.md, task-195-humidity-in-areas.md]
---

# Task 232: Humidity & Atmospheric Conditions

## Summary

Add `humidity` as an area environment property with gameplay effects on effective temperature, item drying, and stealth. Expand `air` propagation so smoke, poison gas, and other atmospheric conditions can spread through open connections.

## Humidity Enum

`environment.humidity`: `dry` / `humid` / `wet` / `flooding`

Defaults to `dry` in `area.py`.

## Humidity Effects

| Humidity | effective_temp modifier | Drying speed | Stealth modifier | Other |
|----------|------------------------|--------------|------------------|-------|
| dry | 0 | fast (baseline) | 0 | — |
| humid | +2 (hot) / -1 (cold) | slow (2x) | -5 | Social -1/tick |
| wet | +3 / -2 | very slow (4x) | -10 | Items may slip |
| flooding | +4 / -3 | no drying | -15 | Movement cost +1 energy |

### effective_temp Integration

In `equipment_bonuses.py`:

```python
humidity = env.get("humidity", "dry")
if humidity == "humid":
    modifier = 2 if ambient_temp > 20 else -1
elif humidity == "wet":
    modifier = 3 if ambient_temp > 20 else -2
elif humidity == "flooding":
    modifier = 4 if ambient_temp > 20 else -3
else:
    modifier = 0
```

### Item Drying

In `tick_turn()` or a dedicated pass, items with `wet: true` in exterior/humid areas dry over time. Drying rate is halved in `humid`, quartered in `wet`, zero in `flooding`.

## Air Propagation

Expand `engine/environment_propagation.py` to handle `air` spread between connected areas:

```python
def propagate_air(graph) -> None:
    """Spread air conditions through open ways."""
    # Similar to propagate_temperature() but for air quality
    # Transfers: smoke → smoke, poison → poison, stale → stale
    # Dilution: if source is "smoke" and target is "fresh", target becomes "hazy"
    # Rate: slower than heat (0.02 base)
```

Air propagation is **slower** than heat propagation.

## Flooding Propagation

Flooding spreads to lower-connected areas through open doors (water flows downhill). Use area height metadata or simple direction-based spread.

## Files Affected

1. `engine/area.py` — add `humidity` to default environment
2. `engine/equipment_bonuses.py` — humidity modifier on effective_temp
3. `engine/environment_propagation.py` — `propagate_air()`, `propagate_flooding()`
4. `engine/tick_manager.py` — item drying tick, humidity vitals effects
5. `engine/effects.py` — `set_environment` / `adjust_environment` support `humidity` key
6. `engine/serialization.py` — save/load `humidity`
7. `engine/area_description.py` — humidity descriptions

## Dependencies

- **Blocked by**: task-227 (forecast provides humidity), task-231 (wind affects drying)

## Testing

- Humid area feels +2°C warmer than actual temp
- Wet items in humid air dry 2x slower than in dry air
- Smoke from fire room spreads through open door over 5–10 ticks
- Flooding drains to lower-connected areas through open doors
- Humidity persists through save/load
