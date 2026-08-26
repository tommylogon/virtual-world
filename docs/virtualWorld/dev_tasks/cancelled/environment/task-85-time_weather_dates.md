---
group: Environment & Climate
wiki: "[[Environment/Time & Weather]]"
---
# Task 85: Time, Weather, Dates, and Moon Phases

**Status**: todo
**Priority**: Medium
**Filed**: 2026-07-24 (updated from stub)

## Summary

The time system already tracks hours/minutes in a 24h cycle. This task adds:
- Date tracking (day/month/year)
- Weather system (clear, cloudy, rainy, stormy, foggy)
- Moon phase cycle (affects outdoor night light)
- Weather effects on outdoor light levels (cloudy = dimmer, storm = much dimmer)
- Integration with light spill system (task-80)

## What Already Exists

- `TickManager.get_game_time_string()` — returns "HH:MM:SS"
- `clock_start_hour`, `clock_start_minute` — configurable start time
- `time_per_tick_minutes` — configurable tick duration
- Time cycles through 24h modulo

## What's Missing

### 1. Date Tracking
- Add to world state: `game_day`, `game_month`, `game_year`
- Calculate from `time_ticks` elapsed (e.g., day = time_ticks × time_per_tick_minutes / 1440)
- Expose in `/api/state` response
- Display in game UI (event stream header or status bar)

### 2. Weather System
- New module `engine/weather.py` or add to `engine/tick_manager.py`
- Weather types: `clear`, `cloudy`, `rainy`, `stormy`, `foggy`, `windy`
- Weather affects outdoor light levels:
  - `clear`: 100% of time-of-day light
  - `cloudy`: 70% of time-of-day light
  - `rainy`: 50% of time-of-day light
  - `stormy`: 30% of time-of-day light
  - `foggy`: 40% of time-of-day light
- Weather changes randomly per tick with configurable probability
- Or weather is set manually via settings (for GM control)
- Weather affects room environments (rain adds water, fog reduces visibility)
- API endpoint: `/api/settings/weather` — GET current weather, POST to change

### 3. Moon Phases
- Deterministic cycle based on `game_day` (30-day cycle)
- Phases: `new_moon`, `crescent`, `quarter`, `gibbous`, `full_moon`
- Each phase affects outdoor night light differently (see task-80)
- Expose in `/api/state` response as `moon_phase`

### 4. Integration with Light System (task-80)
- Outdoor rooms get `get_time_of_day_light(hour, weather, moon_phase)`
- This replaces the static `environment.light` for outdoor rooms
- Light spill uses the *computed* outdoor light, not the static value
- Moon phase only matters at night

### 5. UI Display
- Show date in event stream header: "Day 3, Month 2, Year 1246 — 14:30 — Clear"
- Moon phase icon in sidebar (🌑🌒🌓🌔🌕)
- Weather display with simple icon (☀️🌤️☁️🌧️⛈️🌫️)
- Weather change events in event stream: "The sky darkens as storm clouds roll in."

## Files Affected

- `engine/tick_manager.py` — date calculation, weather tick, moon phase
- `engine/weather.py` — new module (or add to tick_manager)
- `engine/lighting.py` — `get_time_of_day_light()` uses weather + moon phase
- `routes/settings.py` — `GET/POST /api/settings/weather`
- `routes/state.py` — expose date, weather, moon_phase in `/api/state`
- `static/js/world-state.js` — parse new state fields
- `static/js/event-stream.js` — weather change events
- `static/js/ui/settings-view.js` — weather override control
- `static/css/style.css` — weather icons styling

## Dependencies

- **Blocked by**: Nothing
- **Blocks**: Task-80 (light spill), Task-100 (graph light overlay)
- **Related**: Task-80 (needs this for time-of-day light), Task-98 (tags for weather areas)

## Testing

- Advance time from 06:00 to 18:00 — outdoor light stays bright
- Advance to 19:00 — outdoor light drops to night level
- Set weather to stormy — outdoor light drops further
- Full moon at midnight — outdoor light = 25 (dim, can see shapes)
- New moon at midnight — outdoor light = 5 (pitch_black)
- Weather change fires event in stream
- Date increments correctly over multiple in-game days
