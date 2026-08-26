# Body Temperature

## Core Temp Vital

Each player has a `Temperature` vital tracked separately from room temperature:

```python
player.vitals["Temperature"] = 37.0  # default: 37°C (human body temp)
```

Distinct from Hunger/Thirst/Energy vitals — uses floating-point values instead of 0-100 integers.

### Range

| Limit | Value | Effect |
|-------|-------|--------|
| Normal | 37.0°C | Baseline |
| Min | 25.0°C | Hard clamp |
| Max | 45.0°C | Hard clamp |

## Temperature Drift (Per Tick)

In `TickManager.tick_turn()` (`tick_manager.py:232-244`), body temperature drifts toward the effective (equipment-adjusted) temperature:

```python
area_temp = float(effective_temperature(float(env.get("temperature", 21)), bonuses))
core_temp = p.vitals.get("Temperature", 37.0)

if area_temp < 5:
    drift = (5 - area_temp) * 0.02
    p.vitals["Temperature"] = max(25.0, core_temp - drift)
elif area_temp > 35:
    drift = (area_temp - 35) * 0.02
    p.vitals["Temperature"] = min(45.0, core_temp + drift)
else:
    # comfortable range — drift back toward 37°C
    if core_temp < 36.5:
        p.vitals["Temperature"] = min(37.0, core_temp + 0.1)
    elif core_temp > 37.5:
        p.vitals["Temperature"] = max(37.0, core_temp - 0.1)
```

### Drift Thresholds

| Effective Temp | Drift Calculation | Direction | Notes |
|----------------|-------------------|-----------|-------|
| **< 5°C** | `(5 - eff_temp) × 0.02` per tick | Cooling | Body temp drops toward 25°C |
| **5–35°C** | `±0.1` per tick | Toward 37°C | Comfort zone — body self-regulates |
| **> 35°C** | `(eff_temp − 35) × 0.02` per tick | Warming | Body temp rises toward 45°C |

### Time-to-Danger Examples

| Effective Temp | Drift Rate | Time to Dangerous (from 37°C) |
|----------------|-----------|------------------------------|
| -20°C | (5-(-20))×0.02 = 0.50°C/tick cooling | 8 ticks to 33°C hypo |
| 0°C | (5-0)×0.02 = 0.10°C/tick cooling | 40 ticks to 33°C |
| 5–35°C | 0.1°C/tick toward 37°C | Never (stays comfortable) |
| 40°C | (40-35)×0.02 = 0.10°C/tick warming | 30 ticks to 40°C stroke |
| 50°C | (50-35)×0.02 = 0.30°C/tick warming | 10 ticks to 40°C, 17 to 42°C death |

Drift rate is **constant per tick** (not proportional to core temp) — time-to-threshold calculations are linear.

## Core Temperature Damage Table

After drift, the **new** core temp value causes damage each tick:

| Core Temp | Effect | Condition |
|-----------|--------|-----------|
| 35.0–36.9°C (mild cold) | Energy -1 | Shivering |
| 33.0–34.9°C (severe cold) | Energy -2, HP -1 | Hypothermia onset |
| < 33°C (critical cold) | HP -3 | Severe hypothermia |
| 37.1–38.0°C (mild heat) | Thirst -1 | Sweating |
| 38.1–40.0°C (severe heat) | HP -1 | Heat exhaustion |
| > 40°C (critical heat) | HP -3 | Heat stroke |

## Death Check

| Core Temp | Cause of Death |
|-----------|----------------|
| < 30°C | Hypothermia |
| > 42°C | Heat stroke |

Death also triggers `spawn_body_item` — a body item appears in the area with a death cause description.

From `tick_manager.py:174-177`:

```python
if p.vitals.get("Temperature", 37) < 30:
    cause_parts.append("hypothermia")
if p.vitals.get("Temperature", 37) > 42:
    cause_parts.append("heat stroke")
```

## HP Regeneration Gate

HP regeneration (natural healing) is blocked unless:
- Energy > 25, Hunger > 25, Thirst > 25, Sanity > 25
- **AND** core temp is 35–39°C

Being too cold or too hot prevents healing entirely, even with food and rest.

## Indirect Cold Death (Exhaustion)

Even if core temp stays above 30°C, cold drains Energy. When Energy hits 0:
1. Player falls unconscious (`p.state = "unconscious"`)
2. `exhaustion_count` increments
3. After 3 exhaustion cycles → death from **exposure**

Cold can kill without reaching hypothermia temps if you can't warm up (`tick_manager.py:132-137`):

```python
if p.exhaustion_count >= 3:
    p.state = "dead"
```

## Key Code Locations

| Concern | File | Lines |
|---------|------|-------|
| Player initialization | `player.py` | 71-78 |
| Core drift + damage | `tick_manager.py` | 196-275 |
| Death check | `tick_manager.py` | 185-192 |
| Exhaustion death | `tick_manager.py` | 138-149 |
| HP regen gate | `tick_manager.py` | 288-293 |
| Vital detail API | `routes/players.py` | 361-432 |
