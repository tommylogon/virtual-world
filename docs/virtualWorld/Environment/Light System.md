# Light System

## Overview

The Light System manages room visibility through a numeric 0-100 scale, converted to a 5-level enum for gameplay restrictions. It lives in `engine/lighting.py` (class `LightingSystem`, ~80 lines). Light levels affect what actions are possible in a room and contribute to sanity decay.

## Numeric Scale

Light is stored as an integer 0-100 in each room's `environment` dict:

```python
env = {"light": 80}  # bright
```

Default light for indoor areas created without explicit setting is 0 (pitch black). Outdoor areas (tagged `"outdoor"`) compute their light from the current game time, weather, and moon phase (task-230).

## Light Level Enum

`LightingSystem.light_to_level(value)` (`engine/lighting.py:13`) converts numeric values to a 5-level string enum:

| Range | Level | Gameplay Effect |
|---|---|---|
| ≤20 | `pitch_black` | look blocked, examine blocked, take blocked, use blocked |
| ≤40 | `dim` | look shows dim description (fumble around works) |
| ≤70 | `normal` | Normal visibility, no restrictions |
| ≤90 | `bright` | No additional restrictions |
| >90 | `blinding` | No additional restrictions (no blindness mechanic) |

The mapping also handles string enum values directly (e.g., `"dim"` → `"dim"`) and defaults unknown values to `"normal"`.

### Reverse Mapping

`get_light_int()` (`engine/lighting.py:32`) converts string enums back to approximate integers:

| Level | Approx. Value |
|---|---|
| `pitch_black` | 10 |
| `dim` | 30 |
| `normal` | 55 |
| `bright` | 80 |
| `blinding` | 95 |

## Gameplay Restrictions

From `AGENTS.md` and enforced by the backend action handlers:

### `pitch_black` (≤20)
- `look` — Blocked. Player must use `fumble_around()` instead
- `examine` — Blocked
- `take` — Blocked
- `use` — Blocked

The backend checks light level in `area_description.py` (for look/examine) and `item_actions.py` (for take/use). When blocked, the system returns a contextual message.

### `dim` (21-40)
- `look` — Shows a reduced "dim" description (room is visible but details are unclear)
- `fumble_around()` — Works to find hidden items/ways

### `normal` (41-70)
Standard visibility, all actions available.

### `bright` (71-90)
Standard visibility. No special bonuses.

### `blinding` (>90)
Standard visibility. No special penalties currently implemented.

## Ambient Light Calculation

`get_ambient_light(area_id, env)` (`engine/lighting.py:74`) computes a room's effective light level considering:
1. **Outdoor rooms**: computed from time of day + weather + moon phase (task-230)
2. **Indoor rooms**: static `environment.light` value (default 0 = pitch black)
3. **Light spill** from adjacent areas through open/transparent ways
4. **Light-producing items** in the area or carried/equipped

### Time-of-Day Light (Outdoor Rooms)

For rooms tagged `"outdoor"`, `get_time_of_day_light()` returns a base value:

| Time | Light (clear weather) |
|------|----------------------|
| 05:00–06:00 (dawn) | 40 (dim) |
| 06:00–18:00 (day) | 80 (bright) |
| 18:00–19:00 (dusk) | 40 (dim) |
| 19:00–05:00 (night) | 15 (pitch_black) |

Weather modifier (task-227): clear = 100%, cloudy = 70%, rainy = 50%, stormy = 30%, foggy = 40%, windy = 80%.

Moon phase bonus (task-229): only at night, only outdoor. Full moon = +25, gibbous = +15, quarter/waning = +10, crescent = +5, new moon = +0. Stormy/foggy weather halves or nullifies the bonus.

### Light Spill

For each adjacent room connected via an open door:
```
spill = source_light * 0.5
```

Transparent doors (windows, glass doors) allow light spill without being open:
```
spill = source_light * 0.3
```

The effective light is `max(own_light, best_spill)`. Only the brightest spill is used. Light only travels through ways with `current_state == "open"` (or `"transparent": true` for glass).

> **Tunable (task-304):** the spill multiplier is the `light.spill_factor` engine-config key
> (default `0.5`), changeable live via Settings → **Engine Config** — no code edit needed. See
> [[UI & Settings/Engine Config]].

## Dark Vision

`can_see_in_dark(player_manager, player_name)` (`engine/lighting.py:67`) checks if a player can ignore light restrictions:

Returns `True` when any of:
1. **Player is dead** (ghost state) — `player.state == "dead"`
2. **Player has `dark_vision` trait** — checked via `TraitSystem.has_effect(player, "dark_vision")`
3. **Player is a slasher** — slasher trait includes `dark_vision`

## Fumble Around

`fumble_around()` (via `NarrationSystem`, delegated from `virtual_world_engine.py:593`) provides an alternative action for dark areas. This allows players to:
- Discover hidden ways (Perception DC 12)
- Get a tactile description of the room
- Find items by touch

This is the primary way to interact with `pitch_black` areas.

## Sanity Decay

In `TickManager.tick_turn()` (`tick_manager.py:213-215`):

```python
light = self.lighting.get_ambient_light(area_node.id, env)
if light < 20:
    p.vitals["Sanity"] = max(0, p.vitals["Sanity"] - 1)
```

Each tick, characters in areas with ambient light below 20 lose 1 Sanity. This applies to all alive, non-slasher players.

## Ghost Immunity

Ghosts (dead characters) completely ignore light level:

- `can_see_in_dark()` returns `True` for dead players
- The sanity decay check is skipped for dead players (they skip the whole vitals block due to `if p.state == "dead": continue`)
- Ghosts can see, move, and interact in complete darkness

## Light-Producing Items (Graph Scan)

Light contribution is determined by **graph scanning** (`lighting.py:get_item_light_contribution()`). Items in the area or carried/equipped by characters in the area are scanned for:

1. `"light_source"` tag — marks the item as capable of emitting light
2. `current_state == "lit"` — whether the item is currently on
3. `light_level` property — numeric (0–100) or string enum (`"dim"`, `"normal"`, etc.)

The system sums all matching items' `light_level` values (capped at 100). This replaces the old per-player `item_statuses` + `item_active_effects` system.

### Toggleable Items

Items with the `"toggleable"` tag can be turned on/off via `use <item>` or `toggle <item>`:

- `engine/toggleable_items.py:toggle_item_status()` flips `current_state` between `"unlit"` and `"lit"`
- On turn-on: checks `uses > 0`, decrements uses by 1
- Fires `on_toggle_on` / `on_toggle_off` triggers
- If uses hit 0: flips back to `"unlit"`, fires `on_depleted`
- Verb adapts by tag: `electric`/`synthetic` → "turn on/off", default → "light/extinguish"

Example item properties for a hand lamp:
```json
{
  "name": "hand lamp",
  "uses": 60,
  "light_level": "normal",
  "current_state": "unlit",
  "tags": ["light_source", "toggleable", "oil_lamp"],
  "triggers": [
    {"trigger_type": "on_tick", "effects": [{"type": "adjust_uses", "params": {"node_id": "self", "delta": -1}}]},
    {"trigger_type": "on_depleted", "effects": [{"type": "message", "params": {"message": "Your lamp goes out."}}]}
  ]
}
```

### Per-Tick Fuel Drain

`tick_manager.py:283-308` scans carried/equipped items with `current_state == "lit"` each tick. For each lit item:
1. Fires `on_tick` triggers (which should contain `adjust_uses` to drain fuel)
2. When `uses` reaches 0: sets `current_state = "unlit"`, fires `on_depleted`

## Trigger Integration

Triggers can modify light through effects:

### `set_environment`
```python
{"type": "set_environment", "params": {"light": "bright"}}
# or numeric: handles int or enum strings
```
Note: `set_environment` converts light values through `_light_to_level()` (`effects.py:266`).

### `adjust_environment`
```python
{"type": "adjust_environment", "params": {"light": -20}}
```
Incrementally adjusts light, clamped to -50 to 100 range.

## Environment Properties

Light is stored alongside other environment properties on room nodes:

```python
area_node.properties["environment"] = {
    "light": 80,           # 0-100 integer
    "temperature": 21,     # Celsius
    "air": "fresh",        # fresh, stale, humid, toxic
    "smell": "neutral",    # neutral, mold, rot, etc.
    "noise": "quiet",      # quiet, loud, dripping, etc.
}
```

## UI Representation

- Light level is shown in the room description
- Inspector shows current light value for the room
- Agent engine JS uses `_lightToLevel()` to filter what items/actions to include in LLM prompts (the interest attention list sorts *within* the resulting light branch — see Agent Engine.md → Room Context)
- The frontend conditionally enables/disables action buttons based on light level

## Related tasks

- [[dev_tasks/todo/environment/task-229-moon-phase-system|task-229: Moon Phase]]
- [[dev_tasks/todo/environment/task-230-outdoor-lighting-time-of-day|task-230: Time-of-Day Lighting]]
- [[dev_tasks/todo/environment/task-233-area-status-system|task-233: Area Status System]]
- [[dev_tasks/todo/environment/task-234-trigger-environment-forecast-overrides|task-234: Trigger & GM Integration]]
- [[dev_tasks/review/environment/task-18-fireplace_lighting_recipe|task-18: Fireplace lighting recipe]]
- [[dev_tasks/done/environment/task-110-see-through-windows|task-110: See-through Windows]]
- [[UI & Settings/Engine Config|Engine Config (task-304)]] — light spill factor is now a live tunable
