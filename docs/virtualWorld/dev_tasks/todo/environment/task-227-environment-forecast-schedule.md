---
group: Environment & Climate
status: todo
priority: high
filed: 2026-08-15
supersedes: [task-85-time_weather_dates.md]
---

# Task 227: Environment Forecast Schedule Engine

## Summary

Replace ad-hoc weather with a **forecast schedule** system. The scenario designer (or GM) defines environment properties at any game time as a authored schedule — hourly detail, weekly averages, or yearly climate patterns. Triggers and API calls can temporarily override the forecast for story moments.

This is not a weather simulation. It is a **time-aware environment overlay** that `tick_turn()` applies each turn.

## Forecast Modes

The forecast engine supports three modes, selectable per scenario:

### Mode 1: Authored Schedule (default)

Explicit entries as shown below. Designer places environment overrides at specific times. Most control, most work.

### Mode 2: Deterministic State Machine

A configurable state machine where weather transitions between states with **fixed probabilities** (no randomness). Useful for predictable seasonal patterns or scripted weather arcs.

```python
{
    "mode": "deterministic",
    "transition_table": {
        "clear":   {"clear": 7, "cloudy": 2, "windy": 1},
        "cloudy":  {"clear": 2, "cloudy": 4, "rainy": 2, "foggy": 1, "windy": 1},
        "rainy":   {"clear": 1, "cloudy": 2, "rainy": 3, "stormy": 2, "foggy": 2},
        "stormy":  {"rainy": 3, "cloudy": 2, "clear": 1},
        "foggy":   {"clear": 2, "foggy": 3, "cloudy": 2, "rainy": 1},
        "windy":   {"clear": 3, "cloudy": 2, "windy": 2, "stormy": 1}
    },
    "current_state": "clear",
    "transition_interval": "hourly"
}
```

Weights sum to 10 = percentages. The engine rolls a weighted pick at each interval. GM overrides still work.

### Mode 3: Random (Stochastic)

Same transition table as deterministic, but uses `random` at each interval. Can be seeded for reproducibility:

```python
{
    "mode": "random",
    "seed": 42,
    "transition_table": { ... }
}
```

### Hybrid

Authored schedule defines base environment. State machine defines **weather variations** layered on top. E.g., authored schedule says `temperature_mod: 0`, but the state machine adds `weather: "rainy"` on top of it.

## Forecast Data Model

Stored in world state as `forecast_schedule`:

```python
{
    "mode": "authored",
    "seed": None,
    "granularity": "hourly",
    "current_state": "clear",
    "transition_interval": 1,
    "transition_table": { ... },
    "entries": [
        {
            "offset": 0,
            "weather": "clear",
            "wind": "breeze",
            "temperature_mod": 0,
            "light_mod": 0,
            "air": "fresh",
            "message": "The morning is clear and calm."
        },
    ]
}
```

Period lengths:
- `hourly`: 1440 minutes (1 day) — entries repeat daily
- `weekly`: 10080 minutes (7 days) — entries repeat weekly
- `yearly`: 525600 minutes (365 days) — entries repeat yearly (or cycle through seasons)

## Engine Module

New file: `engine/weather_forecast.py`

```python
class ForecastSchedule:
    def __init__(self, schedule: dict):
        self.granularity = schedule.get("granularity", "hourly")
        self.entries = sorted(schedule.get("entries", []), key=lambda e: e.get("offset", 0))
        self.period = {"hourly": 1440, "weekly": 10080, "yearly": 525600}[self.granularity]
        self._last_entry = None

    def get_entry_for_time(self, total_minutes: int) -> dict:
        offset = total_minutes % self.period
        for i, entry in enumerate(self.entries):
            next_off = self.entries[i + 1].get("offset", self.period) if i + 1 < len(self.entries) else self.period
            if entry.get("offset", 0) <= offset < next_off:
                return entry
        return self.entries[0] if self.entries else {}

    def get_environment_overrides(self, time_ticks: int, time_per_tick_minutes: float, game_day: int) -> dict:
        total_minutes = time_ticks * time_per_tick_minutes
        if self.granularity in ("weekly", "yearly"):
            total_minutes += game_day * 1440
        return self.get_entry_for_time(int(total_minutes))
```

## GM Override

A separate `forecast_override` dict in world state (or per-area) that **supersedes** the schedule. Can be:
- Set via API `POST /api/settings/forecast-override`
- Set via trigger effect `forecast_override`
- Timed: includes `duration_ticks` and auto-reverts when expired

## Integration with tick_turn()

In `tick_turn()`, after `advance_clock(1)`:

1. Query `ForecastSchedule` for current environment overrides
2. If active GM override exists, use that instead
3. Apply overrides to all exterior areas (or all areas, per config)
4. If forecast entry changed since last tick, fire narration event using `entry["message"]`

`set_environment` / `adjust_environment` trigger effects are **temporary** (they modify the area's static env dict for one tick or until cleared). The forecast is the **baseline** that gets re-applied each turn.

## Files Affected

1. `engine/weather_forecast.py` — new module
2. `engine/tick_manager.py` — call forecast each turn, apply overrides, fire change events
3. `virtual_world_engine.py` — initialize forecast from world state, expose helper
4. `routes/settings.py` — `GET/POST /api/settings/forecast`, `GET/POST /api/settings/forecast-override`
5. `routes/state.py` — expose `forecast_schedule` and `forecast_override` in `/api/state`
6. `engine/effects.py` — add `forecast_override` effect to trigger system
7. `engine/trigger_validator.py` — validate forecast override params
8. `static/js/world-state.js` — parse new state fields
9. `docs/virtualWorld/Environment/Time & Weather.md` — update design doc

## Dependencies

- **Blocked by**: Nothing
- **Blocks**: task-228 (date tracking), task-229 (moon phase), task-230 (outdoor lighting)

## Testing

- Hourly forecast changes ambient light at hour boundary
- Weekly forecast changes on day boundary
- Yearly forecast changes on season boundary
- GM override supersedes forecast
- Timed override reverts after duration expires
- Weather change narration fires on transition
- Forecast persists through save/load
