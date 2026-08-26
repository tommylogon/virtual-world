# Time & Weather

## Overview

VirtualWorld has an in-game clock driven by a tick-based time system. Each player action consumes time ticks, and the world state advances accordingly. Environment properties (weather, wind, humidity, light, temperature, air, noise, smell) are managed through a forecast schedule system with GM override capability.

## Terminology

| Term | Definition |
|------|-----------|
| **tick** | A unit of game time. Each tick = `time_per_tick_minutes` (default: 5 minutes). `time_ticks` is a monotonically increasing counter. `advance_clock(1)` advances time by 1 tick. |
| **tick_turn()** | The full processing cycle that runs when a turn ends. Calls `conditions.process_tick()`, vitals decay, environmental effects, heat propagation, sound sources, NPC behavior, then `advance_clock(1)`. This is what `/api/turn/apply` invokes. |
| **turn** | One complete player action cycle: player takes action → `tick_turn()` runs → `/api/turn/clear` increments `turn_number`. One turn = one `tick_turn()` call = +1 tick = +5 game minutes. |
| **turn_number** | An integer incremented by `clear_turn_events()` AFTER `tick_turn()` completes. Used for logging, event tracking, and turn-gated conditions. |
| **step** | An NPC movement step or activity progress step. Not a global time concept — NPCs may take multiple steps per turn. |

## Game Clock

Managed by `TickManager` in `engine/tick_manager.py`.

### Tick System

- **Each turn** = 1 time tick
- **Time per tick**: `time_per_tick_minutes = 5` (configurable in `virtual_world_engine.py:47`)
- **Clock start**: 08:00 by default (`clock_start_hour = 8`, `clock_start_minute = 0`)

### Time Calculation

`get_current_time()` (`tick_manager.py:69-81`):

```python
total_minutes = time_ticks * time_per_tick_minutes
total_minutes += clock_start_hour * 60 + clock_start_minute
total_minutes = total_minutes % (24 * 60)
hours = total_minutes // 60
minutes = total_minutes % 60
seconds = total_seconds % 60
return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
```

Time wraps at midnight (24-hour clock). Output format: `"HH:MM:SS"` (seconds always 0).

### Date Tracking

`game_day`, `game_month`, and `game_year` are derived from `time_ticks` (task-228). Calendar config (`minutes_per_day`, `days_per_month`, `months_per_year`) is stored in world state and exposed via `/api/state`.

### Time Advancement

- **`advance_clock(ticks=1)`** (`tick_manager.py:63`): Advances `time_ticks` counter only. Does not apply vital decay.
- **`tick_turn()`** (`tick_manager.py:83`): Advances clock AND applies all vital decay, environmental effects, condition processing, and NPC behavior. This is the main "end turn" method.
- **`apply_action(action_name)`** (`tick_manager.py:24`): Consumes time and energy based on action type's `ACTION_COSTS`.

### Action Costs

Defined in `virtual_world_engine.py:83-92`:

| Action | Time | Energy |
|--------|------|--------|
| `move` | 1 | 1 |
| `open` | 0 | 1 |
| `close` | 0 | 1 |
| `look` | 1 | 0 |
| `use` | 1 | 1 |
| `take` | 1 | 1 |
| `drop` | 1 | 0 |
| `fumble` | 2 | 3 |

Action costs are multiplied by time ticks consumed. Trait modifiers are applied additively via `TraitSystem.get_action_cost_mods()`.

### Time Advance Per Turn

`tick_turn()` always calls `advance_clock(1)` at the end (`tick_manager.py:448`). So each completed turn advances time by 5 minutes.

### Rest Mechanic

`rest(minutes=10)` (`tick_manager.py:541`) sets player state to `"sleeping"`, then runs `tick_turn(skip_npcs=True)` for the duration. Each rest tick advances the clock by 1 tick and recovers Energy at +3/tick.

## Forecast Schedule & Weather

Weather is managed through a **forecast schedule** (task-227) stored in world state as `forecast_schedule`. This is not a weather simulation — it is an authored schedule that `tick_turn()` applies each turn as the environmental baseline.

### Forecast Modes

| Mode | Description |
|------|-------------|
| `authored` | Designer places explicit entries at specific times. Most control. |
| `deterministic` | Weighted state machine with fixed probabilities (no randomness). E.g., `"clear": 70% → "cloudy": 20% → "windy": 10%`. |
| `random` | Same transition table, but uses `random()` each interval. Optional `seed` for reproducibility. |
| `hybrid` | Authored schedule defines base temperature/light; state machine layers weather on top. |

### Forecast Data Model

```python
{
    "mode": "authored",             # "authored" | "deterministic" | "random"
    "seed": None,                   # optional seed for reproducible random
    "granularity": "hourly",        # "hourly" | "weekly" | "yearly"
    "current_state": "clear",       # for state machine modes
    "transition_interval": 1,       # ticks between state rolls
    "transition_table": { ... },    # for state machine modes
    "entries": [
        {
            "offset": 0,            # minutes from period start
            "weather": "clear",     # clear | cloudy | rainy | stormy | foggy | windy
            "wind": "breeze",       # none | breeze | wind | gale | storm | hurricane
            "temperature_mod": 0,   # +N / -N degrees
            "light_mod": 0,         # +N / -N applied to ambient light
            "air": "fresh",         # optional air override
            "message": "The morning is clear and calm."
        },
    ]
}
```

Period lengths:
- `hourly`: 1440 minutes (1 day) — entries repeat daily
- `weekly`: 10080 minutes (7 days) — entries repeat weekly
- `yearly`: 525600 minutes (365 days) — entries repeat yearly

### GM Override

A separate `forecast_override` dict in world state supersedes the schedule. Can be:
- Set via API `POST /api/settings/forecast-override`
- Set via trigger effect `forecast_override` (task-234)
- Timed: includes `duration_ticks` and auto-reverts when expired

### Integration with tick_turn()

In `tick_turn()`, after `advance_clock(1)`:
1. Query `ForecastSchedule` for current environment overrides
2. If active GM override exists, use that instead
3. Apply overrides to areas (globally or per-area)
4. If forecast entry changed since last tick, fire narration event using `entry["message"]`

Trigger effects (`set_environment` / `adjust_environment`) are temporary overlays. The forecast is the **baseline** that gets re-applied each turn.

## Moon Phases

A deterministic 30-day cycle based on `game_day` (task-229):

| Days (mod 30) | Phase | Night Light Bonus |
|---------------|-------|-------------------|
| 0–4 | new_moon | +0 |
| 5–9 | crescent | +5 |
| 10–14 | quarter | +10 |
| 15–19 | gibbous | +15 |
| 20–24 | full_moon | +25 |
| 25–29 | waning | +10 |

Moon phase affects outdoor night ambient light (task-230). Full moon makes outdoor nights visibly brighter; new moon keeps them pitch black.

## Time-of-Day Lighting

Outdoor rooms (tagged `"outdoor"`) get ambient light from the current game time, weather, and moon phase — not from a static `environment.light` value (task-230).

### Light Levels by Time of Day

| Time | Light (clear weather) |
|------|----------------------|
| 05:00–06:00 (dawn) | 40 (dim) |
| 06:00–18:00 (day) | 80 (bright) |
| 18:00–19:00 (dusk) | 40 (dim) |
| 19:00–05:00 (night) | 15 (pitch_black) |

### Weather Modifier

| Weather | Multiplier |
|---------|-----------|
| clear | 100% |
| cloudy | 70% |
| rainy | 50% |
| stormy | 30% |
| foggy | 40% |
| windy | 80% |

Stormy and foggy weather nullify or halve the moon phase bonus.

### Indoor Rooms

Indoor rooms default to `light: 0` (pitch black) unless they have light sources or open connections to lit areas.

### Transparent Doors

Doors with `"transparent": true` allow light spill without being open:
- Spill multiplier: `×0.3` (vs `×0.5` for open doors)

## Wind System

Wind is an area environment property (`environment.wind`) with values: `none` / `breeze` / `wind` / `gale` / `storm` / `hurricane` (task-231).

### Wind Effects

| Effect | Description |
|--------|-------------|
| Heat propagation | Wind accelerates heat exchange between connected areas (1.0× to 3.0× based on strength) |
| Wind chill | Lowers effective temperature, resisted by item `wind_resistance` (0–100%) |
| Wet penalty | Wet items lose insulation, resisted by item `water_resistance` (0–100%) |
| Energy drain | Strong wind drains extra Energy per move in exterior areas |
| Extinguishing | Gale+ can extinguish lit items (10–60% chance per tick) |

Items can declare:
- `"wind_resistance": 50` — resists 50% of wind chill
- `"water_resistance": 30` — resists 30% of wet insulation penalty

## Humidity & Atmosphere

`environment.humidity` values: `dry` / `humid` / `wet` / `flooding` (task-232).

| Humidity | effective_temp modifier | Drying speed | Stealth |
|----------|------------------------|--------------|---------|
| dry | 0 | fast | 0 |
| humid | +2 (hot) / -1 (cold) | slow (2x) | -5 |
| wet | +3 / -2 | very slow (4x) | -10 |
| flooding | +4 / -3 | no drying | -15 |

Air propagation spreads smoke, poison gas, and other atmospheric conditions through open connections (slower than heat propagation).

## Area Statuses

Areas can have a `statuses` list with dynamic effects: `on_fire`, `flooded`, `poison_gas`, `blessed`, `darkness_magic`, etc. (task-233).

Each status has:
- `type`, `severity` (1–5), `duration` (null = permanent), `source`
- `tick_effects`: temperature deltas, air changes, light changes, HP damage, condition application
- `propagation`: spread rules through open ways
- `clear_conditions`: what ends the status

Area statuses are separate from character conditions (different requirements: spatial propagation, environment mutation, no state hierarchy). They can apply character conditions via the existing `apply_condition` effect.

## Trigger Integration

Time-based trigger conditions (task-234):
- `on_dawn`, `on_dusk`, `on_day`, `on_night`
- `on_full_moon`, `on_blood_moon`
- All fire once per transition using a last-fired cache

Turn-based trigger types:
- `on_turn_start` — fires at beginning of `tick_turn()`
- `on_turn_end` — fires at end of `tick_turn()`

Note: `on_tick` is an item trigger that fires during `tick_turn()` — once per turn, not once per time tick. It exists so lit items can burn down. `on_turn_start`/`on_turn_end` are the hooks for areas/characters/NPCs.

## Tick Manager Module

`TickManager` (`engine/tick_manager.py`) orchestrates:

| Method | Purpose |
|--------|---------|
| `__init__` | Injects graph, player_manager, lighting, toggleable_items, trigger_system, npc_behaviors |
| `apply_action` | Deducts action costs from player vitals |
| `advance_clock` | Increments `time_ticks` counter (pure time advance) |
| `get_current_time` | Returns formatted game clock string |
| `tick_turn` | Full turn processing: conditions → vitals decay → env effects → temperature drift → item tick triggers → NPC processing → clock advance |
| `tick` | Legacy wrapper — only advances clock |
| `rest` | Multi-tick rest sequence with NPC processing skipped |

## Turn Events

`GameLogger` (`engine/logging_events.py`) manages per-turn event tracking:
- `turn_number` — monotonically increasing counter
- `turn_events` — list of event dicts for the current turn
- `clear_turn_events()` — advances turn counter and clears buffer
- `get_turn_events_for_area(area_name)` — returns events in a specific room (used by NPC awareness)

## Vitals Decay Over Time

Every `tick_turn()` call applies baseline vitals decay:

| Vital | Decay/tick |
|-------|-----------|
| Energy | 1 |
| Hunger | 1 |
| Thirst | 1 |
| Social | 1 |
| Hygiene | 1 |
| Bladder | — (fills +1/tick) |
| Sanity | 1 |
| Entertainment | 1 |

Sleeping doesn't prevent decay (except Energy gains +3/tick while sleeping).

## Environmental Vitals Effects

Applied each tick in `tick_turn()` (`tick_manager.py:246-323`):

| Property | Value | Effect |
|----------|-------|--------|
| `air` | `"stale"` | Energy -1/tick |
| `air` | `"humid"` | Social -1/tick |
| `air` | `"toxic"` | HP -3/tick |
| `noise` | `"loud"`/`"chaotic"`/`"dripping"`/`"scratches"` | Prevents restful sleep |
| `smell` | `"mold"`/`"rot"`/`"rotting food"`/`"ferment"`/`"urine"` | Hygiene -1/tick |
| `smell` | `"perfume"` | Social +1/tick |
| `light` | <20 | Sanity -1/tick |
| `temperature` | <5°C effective | Core temp drift → Energy/HP loss → hypothermia |
| `temperature` | >35°C effective | Core temp drift → Thirst/HP loss → heat stroke |

## Related Tasks

- [[dev_tasks/todo/environment/task-227-environment-forecast-schedule|task-227: Forecast Schedule Engine]]
- [[dev_tasks/todo/environment/task-228-date-tracking-game-calendar|task-228: Date Tracking]]
- [[dev_tasks/todo/environment/task-229-moon-phase-system|task-229: Moon Phase]]
- [[dev_tasks/todo/environment/task-230-outdoor-lighting-time-of-day|task-230: Time-of-Day Lighting]]
- [[dev_tasks/todo/environment/task-231-wind-system|task-231: Wind System]]
- [[dev_tasks/todo/environment/task-232-humidity-atmospheric-conditions|task-232: Humidity & Atmosphere]]
- [[dev_tasks/todo/environment/task-233-area-status-system|task-233: Area Status System]]
- [[dev_tasks/todo/environment/task-234-trigger-environment-forecast-overrides|task-234: Trigger & GM Integration]]
- [[dev_tasks/review/gameplay/task-48-time_advancement_per_turn|task-48: Time advancement per turn]]
- [[dev_tasks/review/ui/task-36-inspector_game_time|task-36: Inspector game time]]
- [[dev_tasks/todo/gameplay/task-90-delayed_event_queue|task-90: Delayed event queue]]

## Sound Propagation

Sound spreads through the graph each tick (speech via `engine/narration.py`, item sound sources
via `engine/sound.py` + `tick_manager._process_sound_sources()`): speech penetration, door way
barriers, and ambient-noise dampening.

The exact tuning values (speech penetration, open/closed/locked door barriers, noise levels) are
now live **engine-config keys** — editable in Settings → **Engine Config** without code changes
(`sound.*` keys, see [[UI & Settings/Engine Config]]). The BFS propagation logic itself is
documented in `dev_tasks/done/environment/task-149-sound-propagation-system.md` and
`task-12-sound_propagation.md`.

### Per-door override: `sound_barrier` (task-329)

Any way node can set a custom `sound_barrier` property (float) in the inspector — it replaces
the state-derived barrier while the way is in a solid state (`closed`, `blocked`, `locked`),
so a vault door can be 4 while a thin cottage door is 0.5. Unset → per-state Engine Config
defaults as before. Open (0.5), hidden (2), and see_through (0.75) paths are untouched; when
the property is absent, see_through still wins over state lookup. Implemented in
`engine/sound.py get_way_barrier()`; editable via the way inspector's 🔇 Sound Barrier field.
