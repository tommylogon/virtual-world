---
group: Environment & Climate
status: done
priority: high
filed: 2026-08-15
---

# Task 234: Trigger & GM Integration for Forecast & Environment Overrides

## Summary

Expand `set_environment` / `adjust_environment` to support all new environment keys (`weather`, `wind`, `humidity`, `transparent`). Add `forecast_override` and `adjust_forecast` trigger effects so the GM (or scenario triggers) can temporarily override the authored forecast schedule. Add time-of-day/moon trigger conditions (`on_dawn`, `on_dusk`, `on_full_moon`, `on_blood_moon`). Add `on_turn_start` / `on_turn_end` trigger types for areas/characters. Add API endpoints and a basic GM control panel.

## Terminology Glossary

These terms are used throughout the engine and trigger system. They are distinct concepts:

| Term | Definition |
|------|-----------|
| **tick** | A unit of game time. Each tick = `time_per_tick_minutes` (default: 5 minutes). `time_ticks` is a monotonically increasing counter. `advance_clock(1)` advances time by 1 tick. |
| **tick_turn()** | The full processing cycle that runs when a turn ends. Calls `conditions.process_tick()`, vitals decay, environmental effects, heat propagation, sound sources, NPC behavior, then `advance_clock(1)`. This is what `/api/turn/apply` invokes. |
| **turn** | One complete player action cycle: player takes action → `tick_turn()` runs → `/api/turn/clear` increments `turn_number`. One turn = one `tick_turn()` call = +1 tick = +5 game minutes. |
| **turn_number** | An integer incremented by `clear_turn_events()` AFTER `tick_turn()` completes. Used for logging, event tracking, and turn-gated conditions. |
| **step** | An NPC movement step or activity progress step. Not a global time concept — NPCs may take multiple steps per turn. |

### `on_tick` trigger type — clarification

`on_tick` is currently an **item trigger type** that fires during `tick_turn()`. Despite the name, it fires **once per turn**, not once per time tick. It exists so lit items (torches, embers) can burn down and fire `on_depleted` when their `uses` reach 0.

Renaming `on_tick` is not feasible (100+ references in data files). Instead:
- Keep `on_tick` as the item trigger name (documented as "fires once per turn cycle")
- Add `on_turn_start` and `on_turn_end` for areas/characters/NPCs that need turn-gated hooks

## Trigger Effect Expansions

### `set_environment` — New Keys

Currently supports: `light`, `temperature`, `air`, `smell`, `noise`.

Add support for:
- `weather` — set `environment.weather` on a area
- `wind` — set `environment.wind` (none / breeze / wind / gale / storm / hurricane)
- `humidity` — set `environment.humidity` (dry / humid / wet / flooding)
- `transparent` — set `"transparent": true/false` on a way node

### `adjust_environment` — New Keys

Same additions as `set_environment`, but incrementally:
- `adjust_weather` — cycle weather by N steps
- `adjust_wind` — cycle wind by N steps
- `adjust_humidity` — cycle humidity by N steps

### `forecast_override` Effect

Temporarily lock the forecast (globally or per-area):

```json
{
    "type": "forecast_override",
    "params": {
        "weather": "stormy",
        "wind": "gale",
        "temperature_mod": -5,
        "duration_ticks": 60,
        "target": "global"
    }
}
```

- `duration_ticks`: auto-reverts after this many turns. `null` = permanent until manually cleared.
- `target`: `"global"` applies to all areas; `"area:<id>"` applies to one area.

### `adjust_forecast` Effect

Shift the current forecast entry:

```json
{
    "type": "adjust_forecast",
    "params": {
        "temperature_mod_delta": +3,
        "light_mod_delta": -10,
        "duration_ticks": 120
    }
}
```

## Time-of-Day & Moon Trigger Conditions

### `on_dawn`

True when current hour is 05:00–06:00. Fires once per dawn.

### `on_dusk`

True when current hour is 18:00–19:00. Fires once per dusk.

### `on_day`

True during daytime (06:00–18:00).

### `on_night`

True during nighttime (19:00–05:00).

### `on_full_moon`

True when `moon_phase.name == "full_moon"` (game_day % 30 in 20–24). Fires once per full moon night.

### `on_blood_moon`

A rare lunar event. True when a blood moon is active. Can be:
- **GM-triggered**: `forecast_override` sets `blood_moon: true`
- **Random**: state machine has low-probability transition (e.g., 5% on full moon night)
- **Scenario-scripted**: trigger sets it for a specific night

When active: red moonlight (`light_bonus: 30`, red-tinted description), undead aggression bonus.

All time/moon conditions fire **once per transition** using a last-fired cache.

## Turn Trigger Types

New trigger types that fire at the start/end of each turn cycle:

### `on_turn_start`

Fires at the beginning of `tick_turn()`, before conditions, vitals decay, or environmental effects are applied. Use for:
- Applying forecast overrides to areas
- Setting up area statuses that should affect the coming turn
- Pre-turn narration

### `on_turn_end`

Fires at the end of `tick_turn()`, after the clock has advanced and NPC behavior has run. Use for:
- Cleanup triggers
- Post-turn narration
- Triggering area status propagation after environmental changes settle

### Implementation

In `engine/tick_manager.py`:

```python
def tick_turn(self, skip_npcs=False):
    # ── on_turn_start ──
    self._fire_turn_triggers("on_turn_start")
    
    # ... existing tick_turn logic ...
    
    # ── on_turn_end ──
    self._fire_turn_triggers("on_turn_end")
```

`_fire_turn_triggers()` iterates all area nodes and fires the given trigger type on any node that has it registered. This is separate from the item `on_tick` loop — `on_turn_start`/`on_turn_end` fire on **areas, characters, and ways**, not just items.

## API Endpoints

### `GET /api/settings/forecast`

Returns current forecast schedule + active overrides.

### `POST /api/settings/forecast`

Update the entire forecast schedule.

### `POST /api/settings/forecast-override`

Set or clear a forecast override:

```json
{
    "weather": "stormy",
    "wind": "gale",
    "duration_ticks": 60,
    "target": "global"
}
```

Pass `null` values to clear specific keys. Pass `"clear_all": true` to remove all overrides.

### `GET /api/settings/weather`

Legacy endpoint — returns current effective weather.

## GM Control Panel (UI)

In `static/js/settings-view.js`, add a **Weather & Forecast** tab:
- Current effective weather display
- Forecast schedule editor
- Quick-set buttons
- Override timer
- Moon phase display
- Wind speed gauge

## Forecast Revert Logic

In `tick_turn()`, after applying forecast:

```python
override = world_state.get("forecast_override")
if override:
    if override.get("duration_ticks") is not None:
        override["duration_ticks"] -= 1
        if override["duration_ticks"] <= 0:
            world_state.pop("forecast_override", None)
```

## Files Affected

1. `engine/effects.py` — add `forecast_override`, `adjust_forecast`, expand `set_environment` keys
2. `engine/trigger_system.py` — register new effect types + time/moon conditions + `on_turn_start`/`on_turn_end` trigger types
3. `engine/trigger_validator.py` — validate new params + time/moon conditions
4. `engine/tick_manager.py` — forecast override revert logic, `_fire_turn_triggers()` for turn start/end
5. `engine/weather_forecast.py` — expose override-aware lookup, moon phase helper
6. `routes/settings.py` — new forecast endpoints
7. `routes/state.py` — expose forecast + override in state
8. `static/js/settings-view.js` — weather/forecast GM panel
9. `static/js/world-state.js` — parse new fields

## Dependencies

- **Blocked by**: task-227 (forecast engine), task-228 (calendar), task-229 (moon phase), task-231 (wind), task-232 (humidity), task-233 (area statuses)

## Testing

- `set_environment weather=stormy` changes area weather immediately
- `forecast_override weather=stormy duration_ticks=60` locks global weather for 60 turns then reverts
- `adjust_forecast temperature_mod_delta=+3` shifts current forecast entry
- Per-area override `target: "area:room_42"` only affects that room
- `adjust_weather +1` cycles weather forward one step
- `on_dawn` triggers once at 05:00
- `on_full_moon` triggers on game_day % 30 in 20–24 range
- `on_blood_moon` triggers when GM sets `blood_moon: true`
- `on_turn_start` fires before vitals decay
- `on_turn_end` fires after clock advance
- API endpoints return correct current state

## Implemented (audit 2026-09-02)

Mostly implemented before this audit: `set_environment` new keys
(weather/wind/humidity/transparent), adjust cycling, `forecast_override` /
`adjust_forecast` handlers, `on_turn_start`/`on_turn_end`
(`_fire_turn_triggers`), time/moon triggers (`_fire_time_triggers`: on_dawn,
on_dusk, on_day, on_night, on_full_moon, on_blood_moon — one-shot per
game-day cache), and the GM panel (SkyScape World Sky panel: override
weather/wind/humidity/duration + Set/Clear against
`/api/settings/forecast-override`).
This audit registered all of those trigger types + effects in
`TRIGGER_TYPES` / `EFFECT_TYPES` (they fired engine-side but were unregistered,
so the validator and both editors rejected them), and added the full param
blocks to the form and graph editors.
