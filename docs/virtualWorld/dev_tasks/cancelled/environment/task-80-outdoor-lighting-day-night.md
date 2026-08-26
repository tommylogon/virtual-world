---
group: Environment & Climate
wiki: "[[Environment/Light System]]"
---
# Task 80: Outdoor Lighting & Day/Night Cycle

**Status**: todo
**Priority**: Medium
**Filed**: 2026-07-15 (updated 2026-07-24)

## Goal

Create a complete light model where rooms get their ambient light from:
1. **Outdoor rooms** (tagged `"outdoor"`) — get light from time of day (sunlight, moonlight, or none)
2. **Interior rooms** — pitch black by default, unless they have light sources or light spills in through open connections
3. **Light spill** — travels through open doors (and future: windows/see-through doors)
4. **Light sources** — torches, candles, fireplaces, magic spells, flashlights override ambient light
5. **Graph view** — visualize light propagation as an overlay (see task-100)

## What Already Exists

### Lighting system (`engine/lighting.py`)
- `LightingSystem` class with:
  - `light_to_level(value)` — converts numeric to enum (pitch_black/dim/normal/bright/blinding)
  - `get_light_int(env, default)` — extracts light as integer from environment dict
  - `get_ambient_light(area_id, env)` — computes effective light including spill from adjacent rooms through open doors (spill = source × 0.5)
  - `can_see_in_dark(player_manager, player_name)` — checks ghost/dark_vision traits

### Time system (`engine/tick_manager.py`)
- `get_game_time_string()` — returns "HH:MM:SS" based on `clock_start_hour/minute + time_ticks × time_per_tick_minutes`
- `rest(minutes)` — advances time by N minutes
- Time cycles through 24h modulo

### Rooms in data
- Rooms in the graph have an `environment` dict with light, temperature, air, smell, noise
- Some rooms have `tags: ["outdoor"]` in the world template (graph nodes)
- Area class has no tags field itself — tags live on graph nodes

### Task-85 (time/weather/dates)
- Currently a stub — mentions time system exists but weather/date tracking is missing

### Task-100 (graph view filters)
- Covers light/heat/sound overlay views for the graph visualization
- Light propagation view would show room light levels as colors

## What's Missing

### 1. Outdoor Light Based on Time of Day
- Rooms with tag `"outdoor"` get their base light from the current time:
  - **Daytime (06:00 - 18:00)**: `light: 80` (bright) — full sunlight, can be reduced by weather (cloudy = 55, storm = 30)
  - **Dawn/Dusk (05:00-06:00, 18:00-19:00)**: `light: 40` (dim) — transitioning
  - **Night (19:00 - 05:00)**: `light: 15` (pitch_black), unless moonlight:
    - Full moon: `light: 25` (dim)
    - Crescent moon: `light: 15` (pitch_black)
    - New moon / overcast: `light: 5` (pitch_black)
- Outdoor light overrides the room's static `environment.light` value
- Indoor rooms without light sources or open connections: `light: 0` (pitch_black)

### 2. Window / See-Through Way Concept
- New property on doors: `"transparent": true` (windows, glass doors, grates, etc.)
- Transparent doors allow light spill *without* being open
- Spill through transparent doors is reduced: `spill = source × 0.3` (vs ×0.5 for open doors)
- The `visible_in_direction` field on exits already hints at this ("Above, through the open trapdoor, you see the kitchen ceiling and the light from the room")

### 3. Light Sources
- Items with `effect_type: "set_environment"` and `effect: { light: "dim" }` already work (candles, lamps, torches)
- These persist through `_item_active_effects`
- No changes needed to the trigger system — just make sure ambient light calculation prioritizes room's own light sources over spill
- `get_ambient_light()` already does: `return max(own, best_spill)` — own light sources take priority

### 4. Ambient Light Calculation (Updated Logic)

```
get_ambient_light(area_id):
  if room has tag "outdoor":
    base = get_time_of_day_light(current_time, weather, moon_phase)
  else:
    base = room.environment.get("light", 0)  # pitch black by default for indoors

  # Add spill from adjacent rooms through open/transparent connections
  for each connected room via open door (or transparent door):
    spill = source_room.ambient_light × 0.5 (open) or × 0.3 (transparent)
    best_spill = max(best_spill, spill)

  # Add active item light sources
  item_light = max active item light contributions

  return max(base, best_spill, item_light)
```

### 5. Moon Phase System (for task-85)
- Add moon phase calculation to time system: new moon, crescent, quarter, gibbous, full
- Can be deterministic based on `time_ticks` (e.g., 30-day cycle)
- Affects outdoor night light levels

## Appendix A: Current Light Behavior Reference (July 2026)

This is the complete map of how light/visibility affects every action and the agent prompt, traced from the actual code. Use this to identify inconsistencies and decide what should change.

### Light Levels
| Numeric | Enum | Visual |
|---------|------|--------|
| ≤20 | pitch_black | Nothing visible |
| 21-40 | dim | Only large objects |
| 41-70 | normal | Normal visibility |
| 71-90 | bright | Clear |
| >90 | blinding | Overwhelming |

### Actions: What's Blocked vs Allowed in Pitch Black

| Action | Light Check? | File:Line | Notes |
|--------|-------------|-----------|-------|
| `go [dir]` | ❌ No check | `engine/movement.py:91-240` | Can freely walk in dark |
| `look` | ✅ Blocks | `engine/area_description.py:97-99` | Returns "pitch black" message |
| `examine [target]` | ✅ Blocks | (via `get_item_desc`) | Returns dark error |
| `take [item]` | ✅ Blocks | `engine/item_actions.py` (traced) | Too dark to see items |
| `drop [item]` | ❌ No check | (inventory action) | You know your own inventory |
| `use [item]` (no target) | ❌ No check | `engine/item_actions.py:519-615` | Can light torch, drink potion, etc. blind |
| `use [item] on [target]` | ✅ Blocks | `engine/item_actions.py:628-632` | "too dark to see what you're doing" |
| `inventory` | ❌ No check | (reads player data) | You know what you carry |
| `stats` | ❌ No check | (reads player data) | Always accessible |
| `fumble` | ✅ Designed for dark | `engine/narration.py:263-350` | Perception DC 12 — finds hidden exits or bumps into items |
| `toggle [item]` | ❌ No check | (uses same path as `use`) | Can toggle things in dark |
| `rest` | ❌ No check | (time advance) | Always works |

### The Fumble Gap (Inconsistency)

Fumble can reveal an item ("you bump into something — it might be: candle"), but:
- `take candle` → ❌ blocked (too dark)
- `use candle` → ✅ works (no light check) but game doesn't tell you this
- `examine candle` → ❌ blocked (too dark)

**Suggestion**: If a player fumble-discovers an item, temporarily bypass the light check for that specific item for one action. Or make `use` work on fumble-discovered items even in dark.

### Agent Prompt Behavior (`prompt-builder.js:391-471`)

The LLM agent's room context is light-aware:

| Light Level | Items Listed | Warning | Exits | Inventory |
|-------------|-------------|---------|-------|-----------|
| pitch_black | None | "⚠️ PITCH BLACK — try to use a light source" | Always listed | Always shown |
| dim | Only weight >= 3 | "⚠️ Dim light — only large objects visible" | Always listed | Always shown |
| normal+ | All non-hidden | None | Always listed | Always shown |
| dark_vision trait | All (overrides) | None | Always listed | Always shown |

The agent **knows** they're in the dark and is prompted to use a light source. Exits are always shown (you can feel walls). Inventory is always shown (you know your own stuff).

### Current Light Source Mechanism

- Items with `effect_type: "set_environment"` and `effect: { light: "dim" }` (candles, lamps) already work
- These persist via `_item_active_effects` system
- `get_ambient_light()` uses `max(own, best_spill)` — own light sources beat spill
- After lighting a torch, the room light updates immediately within the same tick via active effects
- `use [item]` works in dark → light source fires → `look` then shows the room — the torch scenario works end to end

Related Tasks

- **Task-85**: Time/weather/dates — need to add moon phase, time-of-day light levels, weather effects on light (clouds reduce sunlight)
- **Task-100**: Graph view filters — light propagation overlay uses the computed ambient light values
- **Task-98**: Tags as core query system — `tag: "outdoor"` is how we identify outdoor rooms

## Implementation Order

1. **Phase 1**: Add `get_time_of_day_light()` to `engine/lighting.py` — returns light level based on current game time
2. **Phase 2**: Update `get_ambient_light()` to check for `tag: "outdoor"` and use time-of-day light instead of room's static light
3. **Phase 3**: Add `"transparent"` property to doors, update spill logic to handle transparent doors
4. **Phase 4**: Move interior room default light from 80 to 0 (pitch black), test everything breaks appropriately
5. **Phase 5**: Moon phase calculation + moonlight light levels

## Files Affected

- `engine/lighting.py` — `get_ambient_light()`, new `get_time_of_day_light()`, transparent door spill
- `engine/tick_manager.py` — moon phase calculation (or route helper)
- `graph.py` — room tags access (or use existing graph tag queries)
- `door.py` / door properties — `"transparent"` flag
- `routes/state.py` — expose moon phase in API state
- `static/js/graph/network-manager.js` — light overlay color mapping

## Testing

- Outdoor room at noon → light = 80 (bright)
- Outdoor room at midnight (new moon) → light = 5 (pitch_black)
- Indoor room with no doors → light = 0 (pitch_black)
- Indoor room connected to outdoor via open door → light = 40 (dim, 80 × 0.5)
- Indoor room connected to outdoor via closed transparent door → light = 24 (dim, 80 × 0.3)
- Indoor room with lit candle AND open door to bright room → max(candle_light, spill) = own light wins
- Close the door → candle alone keeps the room lit
