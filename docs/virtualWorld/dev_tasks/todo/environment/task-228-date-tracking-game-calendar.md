---
group: Environment & Climate
status: todo
priority: medium
filed: 2026-08-15
supersedes: [task-85-time_weather_dates.md]
---

# Task 228: Date Tracking & Game Calendar

## Summary

Add a game calendar (day / month / year) derived from `time_ticks`. Expose it in world state and the API so other systems (moon phases, forecast schedules, scenarios with seasonal themes) can reference absolute dates.

## What Already Exists

- `TickManager.time_ticks` — monotonically increasing counter
- `time_per_tick_minutes = 5` — each tick = 5 game minutes
- `clock_start_hour = 8`, `clock_start_minute = 0` — day starts at 08:00

## Implementation

### Calendar Config

Add to world state (or `virtual_world_engine.py` defaults):

```python
calendar_config = {
    "minutes_per_day": 1440,
    "days_per_week": 7,
    "days_per_month": 30,
    "months_per_year": 12,
    "year_start_day": 1,
}
```

### Date Calculation

In `engine/tick_manager.py`:

```python
@property
def game_day(self) -> int:
    total_minutes = self.time_ticks * self.time_per_tick_minutes
    return int(total_minutes // 1440) + 1

@property
def game_month(self) -> int:
    cfg = self.player_manager.calendar_config
    day = self.game_day
    month = ((day - 1) // cfg["days_per_month"]) % cfg["months_per_year"] + 1
    return month

@property
def game_year(self) -> int:
    cfg = self.player_manager.calendar_config
    day = self.game_day
    return ((day - 1) // (cfg["days_per_month"] * cfg["months_per_year"])) + 1
```

### World State Exposure

Add `game_day`, `game_month`, `game_year`, `calendar_config` to `/api/state` response.

### UI Display

Event stream header format: `"Day {day}, Month {month}, Year {year} — {HH:MM} — {weather}"`

## Files Affected

1. `engine/tick_manager.py` — add `game_day`, `game_month`, `game_year` properties
2. `virtual_world_engine.py` — add `calendar_config` defaults
3. `routes/state.py` — expose calendar fields in `/api/state`
4. `engine/serialization.py` — save/load calendar config
5. `static/js/world-state.js` — parse new fields
6. `static/js/event-stream.js` — display date in header

## Dependencies

- **Blocked by**: Nothing
- **Blocks**: task-227 (forecast schedule uses day for weekly/yearly), task-229 (moon phase uses game_day)

## Testing

- Advance time across midnight → `game_day` increments
- Advance across month boundary → `game_month` increments
- Advance across year boundary → `game_year` increments
- Calendar persists through save/load
- Custom calendar config works
