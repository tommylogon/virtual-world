---
group: Environment & Climate
status: todo
priority: medium
filed: 2026-08-15
supersedes: [task-85-time_weather_dates.md, task-80-outdoor-lighting-day-night.md]
---

# Task 229: Moon Phase System

## Summary

Add a deterministic moon phase cycle (30-day) based on `game_day`. Moon phase affects outdoor night ambient light. Full moon makes outdoor nights visibly brighter; new moon keeps them pitch black.

## Moon Phases

30-day cycle, mapped from `game_day % 30`:

| Days (mod 30) | Phase | Night Light Bonus |
|---------------|-------|-------------------|
| 0–4 | new_moon | +0 |
| 5–9 | crescent | +5 |
| 10–14 | quarter | +10 |
| 15–19 | gibbous | +15 |
| 20–24 | full_moon | +25 |
| 25–29 | waning | +10 |

## Implementation

### Calculation

In `engine/weather_forecast.py`:

```python
def get_moon_phase(game_day: int) -> dict:
    cycle_day = game_day % 30
    if cycle_day < 5:
        return {"name": "new_moon", "light_bonus": 0, "icon": "🌑"}
    elif cycle_day < 10:
        return {"name": "crescent", "light_bonus": 5, "icon": "🌒"}
    elif cycle_day < 15:
        return {"name": "quarter", "light_bonus": 10, "icon": "🌓"}
    elif cycle_day < 20:
        return {"name": "gibbous", "light_bonus": 15, "icon": "🌔"}
    elif cycle_day < 25:
        return {"name": "full_moon", "light_bonus": 25, "icon": "🌕"}
    else:
        return {"name": "waning", "light_bonus": 10, "icon": "🌖"}
```

### Integration with Lighting

`get_time_of_day_light()` (task-230) adds `moon_phase["light_bonus"]` to night light **only when**:
- Current hour is night (19:00–05:00)
- Room has tag `"outdoor"`
- No weather that obscures sky (stormy/foggy = moon bonus halved or zero)

## Exposure

- `/api/state` returns `moon_phase` (name + icon + light_bonus)
- UI sidebar shows moon icon
- Area descriptions mention moonlight when relevant

## Files Affected

1. `engine/weather_forecast.py` — `get_moon_phase()` helper
2. `engine/lighting.py` — `get_time_of_day_light()` consumes moon phase
3. `routes/state.py` — expose `moon_phase`
4. `engine/area_description.py` — mention moonlight in outdoor night descriptions
5. `static/js/world-state.js` — parse `moon_phase`
6. `static/css/style.css` — moon icon styling

## Dependencies

- **Blocked by**: task-228 (needs `game_day`)
- **Blocks**: task-230 (outdoor lighting uses moon bonus)

## Testing

- `game_day` 0 → new_moon, night outdoor light = base night value
- `game_day` 22 → full_moon, night outdoor light = base + 25
- Stormy weather halves or nullifies moon bonus
- Moon phase persists correctly across month/year boundaries
