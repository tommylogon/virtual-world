---
group: Environment & Climate
status: review

## Implemented (2026-08-21)

- `lighting.py`: `outdoor_light_for_hour(hour)` — piecewise-linear curve (deep night ~8, dawn ramp 5-8,
  full day 9-16 at 85, dusk ramp 17-21, night again); `is_outdoor_area(area_id)` reads the area's
  `outdoor` tag; `get_ambient_light(..., hour=None)` modulates outdoor base light when an hour is
  available. An explicitly authored `environment.light` acts as a FLOOR (magically lit glade stays
  bright at midnight), not a ceiling.
- Wiring: `LightingSystem.hour_provider` callable set once in `VirtualWorld.__init__` to
  `current_game_hour()` (ticks × time_per_tick + clock start, % 24) — ALL existing
  `get_ambient_light` call sites get time-aware outdoor lighting with zero call-site changes.
- Tests: `tests/test_realism_perception.py` — curve values (5) + outdoor/indoor/floor/provider cases (6).
priority: high
filed: 2026-08-15
supersedes: [task-80-outdoor-lighting-day-night.md]
---

# Task 230: Time-of-Day Outdoor Lighting

## Summary

Outdoor rooms get their ambient light from the current game time, weather, and moon phase — not from a static `environment.light` value. Indoor rooms default to pitch black. Light spill from open/transparent doors connects interior spaces to the outside.

## Light Levels by Time of Day

Base values for outdoor rooms:

| Time | Light (clear weather) |
|------|----------------------|
| 05:00–06:00 (dawn) | 40 (dim) |
| 06:00–18:00 (day) | 80 (bright) |
| 18:00–19:00 (dusk) | 40 (dim) |
| 19:00–05:00 (night) | 15 (pitch_black) |

## Weather Modifier

Applied as a multiplier to the base outdoor light:

| Weather | Multiplier |
|---------|-----------|
| clear | 100% |
| cloudy | 70% |
| rainy | 50% |
| stormy | 30% |
| foggy | 40% |
| windy | 80% |

Stormy and foggy weather also nullify or halve the moon phase bonus.

## Moon Phase Bonus

Only at night (19:00–05:00), only for outdoor rooms:
- Full moon: +25
- Gibbous: +15
- Quarter / waning: +10
- Crescent: +5
- New moon: +0

## Implementation

### `get_time_of_day_light(hour, weather, moon_phase)`

New method in `engine/lighting.py`:

```python
def get_time_of_day_light(self, hour: int, weather: str = "clear", moon_phase: dict = None) -> int:
    if 5 <= hour < 18:
        base = 80
    elif (5 <= hour <= 6) or (18 <= hour <= 19):
        base = 40
    else:
        base = 15
        if moon_phase and moon_phase.get("light_bonus"):
            if weather in ("stormy", "foggy"):
                base += moon_phase["light_bonus"] // 2
            else:
                base += moon_phase["light_bonus"]

    weather_mult = {"clear": 1.0, "cloudy": 0.7, "rainy": 0.5, "stormy": 0.3, "foggy": 0.4, "windy": 0.8}.get(weather, 1.0)
    return min(100, max(0, int(base * weather_mult)))
```

### `get_ambient_light()` Update

In `engine/lighting.py:74`:

```python
def get_ambient_light(self, area_id: str, env: Optional[Dict] = None) -> int:
    node = self.graph.get_node(area_id)
    if not node:
        return 80

    is_outdoor = "outdoor" in node.properties.get("tags", [])
    
    if is_outdoor:
        hour = self._get_current_hour()
        weather = self._get_current_weather()
        moon = self._get_moon_phase()
        base = self.get_time_of_day_light(hour, weather, moon)
    else:
        base = self.get_light_int(env, default=0)
```

### Transparent Doors

Doors with `"transparent": true` in properties allow light spill without being open:
- Spill multiplier: `×0.3` (vs `×0.5` for open doors)
- Check `way_node.properties.get("transparent")` in the spill logic

## Files Affected

1. `engine/lighting.py` — `get_time_of_day_light()`, update `get_ambient_light()`, transparent door spill
2. `engine/tick_manager.py` — expose current hour/weather/moon to lighting system
3. `engine/weather_forecast.py` (task-227) — weather lookup
4. `engine/moon.py` or weather_forecast helper (task-229) — moon phase lookup
5. `engine/area_description.py` — outdoor light descriptions
6. `graph.py` / `way.py` — `"transparent"` property on doors
7. `engine/effects.py` — `set_environment` can set `"transparent"` on ways
8. `static/js/graph/network-manager.js` — light overlay uses computed ambient light

## Dependencies

- **Blocked by**: task-227 (forecast provides weather), task-229 (moon phase)
- **Blocks**: task-100 (graph light overlay needs computed light values)

## Testing

- Outdoor room at noon (clear) → light = 80
- Outdoor room at midnight (new moon, clear) → light = 15
- Outdoor room at midnight (full moon, clear) → light = 40
- Indoor room with no doors → light = 0
- Indoor room with open door to bright outdoor → light = 40
- Indoor room with closed transparent door to bright outdoor → light = 24
- Lit candle in indoor room → light = candle value
