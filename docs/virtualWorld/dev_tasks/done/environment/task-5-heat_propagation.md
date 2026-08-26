---
group: Environment & Climate
wiki: "[[Rules Engine/Temperature System]]"
---

# Heat Propagation Through Open Ways

**Filed**: 2026-07-17  
**Updated**: 2026-07-29  
**Priority**: Medium  
**Status**: Done (code implemented, docs updated)
**Implemented**: 2026-07-30

---

## Summary

Temperature should gradually equalize between areas connected by open ways. This creates emergent behavior:
- Lit fireplace warms adjacent areas through open doors
- Blizzard cold seeps into the house through the open front door
- Player can close doors to retain heat — strategic thermal management

**Only temperature propagation for now.** Noise, smell, and light are separate concerns.

---

## Why this matters

Without propagation, room temperature only changes via explicit trigger effects (set_environment / adjust_environment). The fireplace only warms its own room. Opening the front door to a -5°C blizzard does nothing. This breaks immersion.

With propagation, these behaviors emerge naturally from the mechanics:
- Fireplace in living room slowly warms hallway and bedroom through open doors
- Front door left open pulls house temp toward exterior temp
- Player has a reason to close doors behind them in winter
- Exterior rooms tagged `is_exterior: True` act as infinite heat sinks/sources

---

## Tick Model

**Critical**: `tick_turn()` is called **once per full turn**, not per action.

| Concept | What it means |
|---------|--------------|
| **Turn** | All characters (player + NPCs) have acted |
| **Tick** | One call to `tick_turn()` — 5 game-minutes by default |
| **Frequency** | POST `/api/turn/apply` → `tick_turn()` once |

So propagation in a 20-character scenario still runs **once per turn**, not 20 times. Each tick represents ~5 minutes of game time, which is a natural interval for temperature change.

The existing drift formulas (0.02–0.3°C per tick) are calibrated for this frequency and propagation should use the same cadence.

---

## Propagation Formula

Every tick, for each pair of areas connected by an open way:

```
diff = temp_a - temp_b
transfer = diff * exchange_rate
temp_a -= transfer      (unless is_exterior)
temp_b += transfer      (unless is_exterior)
```

### Exchange Rate

`exchange_rate = base_rate * way_insulation * area_insulation`

| Factor | Default | Source |
|--------|---------|--------|
| `base_rate` | `0.05` | Constant — calibrated for 5-min ticks |
| `way_insulation` | `1.0` | From way node properties (stone door = 0.5, window = 2.0) |
| `area_insulation` | `1.0` | From area node properties (basement = 0.3) |

### Calibration example

| Scenario | diff | rate | transfer/tick | After 1 hour (12 ticks) |
|----------|------|------|--------------|------------------------|
| Fireplace (28°C) → Hallway (21°C) | 7°C | 0.05 | 0.35°C | Hallway warms ~4°C |
| Blizzard (-5°C) → Hallway (21°C) | 26°C | 0.05 | 1.3°C | Hallway cools ~13°C |
| Near-equal rooms (22°C ↔ 21°C) | 1°C | 0.05 | 0.05°C | Negligible |

### Max change cap

Clamp per-tick transfer to prevent extreme single-tick swings:
```
transfer = max(-max_delta, min(max_delta, transfer))
```
where `max_delta = 2.0°C` per tick.

This prevents a -50°C exterior from flash-freezing a room in one tick.

---

## Infinite Reservoirs (Exterior Areas)

Areas with `properties.is_exterior: True` act as infinite reservoirs:

- Their temperature **never changes** from propagation
- They still **affect connected areas** (heat flows into/out of them)
- No `is_exterior`? Treat as normal.

This is the key mechanic. Open the front door to a blizzard and the hallway temperature gets pulled toward the exterior temp, but the blizzard area itself stays at -5°C.

---

## Implementation Plan

### 1. New file: `engine/environment_propagation.py`

```python
def propagate_temperature(graph):
    """Spread temperature between areas connected by open ways."""
    edges_processed = set()

    # Walk all connection edges
    for edge in graph.edges:
        if edge.type != "connection":
            continue

        # Avoid processing both directions
        pair = tuple(sorted([edge.source, edge.target]))
        if pair in edges_processed:
            continue
        edges_processed.add(pair)

        source_area = graph.get_node(edge.source)
        target_area = graph.get_node(edge.target)
        if not source_area or not target_area:
            continue

        # Find the way node that connects these (matches source+target)
        way_node = _find_way_between(graph, edge.source, edge.target)
        if not way_node:
            continue

        # Only propagate through open ways
        if way_node.properties.get("current_state") != "open":
            continue

        temp_a = source_area.properties.get("environment", {}).get("temperature", 21)
        temp_b = target_area.properties.get("environment", {}).get("temperature", 21)

        diff = temp_a - temp_b
        if abs(diff) < 0.5:
            continue  # Skip negligible differences

        insulation = way_node.properties.get("insulation", 1.0)
        rate = 0.05 * insulation

        transfer = max(-2.0, min(2.0, diff * rate))

        if not source_area.properties.get("is_exterior"):
            source_env = source_area.properties.setdefault("environment", {})
            source_env["temperature"] = temp_a - transfer

        if not target_area.properties.get("is_exterior"):
            target_env = target_area.properties.setdefault("environment", {})
            target_env["temperature"] = temp_b + transfer


def _find_way_between(graph, area_a_id, area_b_id):
    """Find a way node that has connections to both area_a and area_b."""
    for node in graph.nodes.values():
        if node.type != "way":
            continue
        conns = graph.get_edges_for_source(node.id, "connection")
        targets = {e.target for e in conns}
        if area_a_id in targets and area_b_id in targets:
            return node
    return None
```

### 2. Hook into `TickManager.tick_turn()`

In `engine/tick_manager.py`, at the **end** of `tick_turn()` (after all player temperature drift/damage):

```python
from engine.environment_propagation import propagate_temperature

def tick_turn(self, skip_npcs=False):
    # ... existing code: baseline decay, temp drift, damage ...
    
    # ── Temperature propagation ──
    propagate_temperature(self.graph)
```

### 3. Tag exterior areas in world data

Find all exterior areas in `world_template.json` and add `"is_exterior": true` to their properties. Also add reasonable insulation values on doors between interior/exterior.

### 4. Add insulation to way creation UI (optional)

The way inspector in `area-view.js` or `way-view.js` should have an editable `insulation` field for fine-tuning propagation rates.

---

## Integration Points

- **Fireplace** ([[review/environment/task-18-fireplace_lighting_recipe]]) — lit fireplace heats its room via `on_tick` + `adjust_environment`; propagation spreads warmth through open doors
- **Door mechanics** — open/close state directly controls whether heat flows
- **Temperature conditions** — triggers using `temperature_below`/`temperature_above` will fire based on propagated temps
- **Exhaustion death from cold** — cold propagation can indirectly kill through Energy drain even without hypothermia
- **NPC behavior** — NPCs could be set to close doors when temperature drops (future enhancement)

---

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| Room connects to 3 exterior areas | Heat bleeds out rapidly (like an open pavilion) |
| Player closes all doors | Propagation stops, rooms maintain their temps |
| Multi-room chain (A↔B↔C) | Heat flows stepwise: A→B then B→C each tick |
| Room with no open connections | Temperature stable (only changes via triggers) |
| `is_exterior` room connected to another exterior | Neither changes (both skip) |

---

## What this does NOT cover

- **Weather/sunlight** — outdoor temperature doesn't cycle ([[todo/environment/task-227-environment-forecast-schedule]])
- **Noise propagation** — separate concern
- **Smell propagation** — separate concern
- **Visual heat flow UI** — could be added to graph overlay later

---

## Files to touch

| File | Change |
|------|--------|
| `engine/environment_propagation.py` | **New** — propagation logic |
| `engine/tick_manager.py` | Import and call `propagate_temperature()` at end of `tick_turn()` |
| `world_template.json` | Add `is_exterior: true` to outdoor areas, insulation to doors |
| `data/scenarios/` | Same for scenario files |

## Non-goals (for this pass)

- Visualizing heat flow on the graph (future)
- NPCs reacting to temperature changes (future)
- Dynamic insulation from player-built structures (future)
- Fire spread (future -- task-5 was originally scoped for this but it's too much)