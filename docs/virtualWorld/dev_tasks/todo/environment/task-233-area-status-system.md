---
group: Environment & Climate
status: todo
priority: medium
filed: 2026-08-15
supersedes: [task-138-area-status-system.md]
---

# Task 233: Area Status System

## Summary

Add a general-purpose `statuses` list to area nodes, mirroring the character condition instance schema. This is the framework for dynamic environmental effects: `on_fire`, `flooded`, `poison_gas`, `blessed`, `darkness_magic`, etc. Statuses can tick damage to characters, modify environment properties, and propagate through open connections.

## Why Area Statuses Are Separate from Character Conditions

The character condition system (`engine/conditions.py`) is tightly coupled to character state management. Area statuses look similar on the surface (type, severity, duration, tick_effects) but have fundamentally different requirements:

| Concern | Character Conditions | Area Statuses |
|---------|---------------------|---------------|
| State hierarchy | `awake` → `sleeping` → `unconscious` → `dead` | No state hierarchy |
| Gate system | `blocks_speech`, `drops_held_items`, `blocks_movement` | No action gates |
| Stack behavior | `accumulate` / `refresh` / `noop` | Simple: stack severity up to 5 |
| Spatial propagation | None | Spreads through open ways |
| Environment mutation | None | Modifies env.temperature, env.air, env.light |
| Damage types | Vital-specific | HP + condition application to everyone |

Forcing area statuses into conditions would require inventing fake "area states" and meaningless gates. Keep them separate. Share the pattern (registry, instance schema) but not the code. Area statuses can apply character conditions via the existing `apply_condition` effect.

## Status Schema

Each status instance on an area:

```json
{
    "type": "on_fire",
    "severity": 3,
    "duration": null,
    "source": "fireplace_item",
    "tick_effects": {
        "temperature": 15,
        "air": "smoke",
        "light": 20,
        "damage": {"hp": 2, "fire": 1}
    },
    "propagation": {
        "type": "through_open_ways",
        "rate": 0.05,
        "target_statuses": ["on_fire", "smoke"]
    },
    "clear_conditions": ["extinguished", "duration_expired"]
}
```

## Status Type Definitions

Stored in `engine/area_statuses.py` as a registry:

```python
AREA_STATUS_DEFINITIONS = {
    "on_fire": {
        "name": "On Fire",
        "default_tick_effects": {"temperature": 10, "air": "smoke", "light": 15, "damage": {"hp": 1}},
        "clear_on": ["extinguished", "duration_expired"]
    },
    "flooded": {
        "name": "Flooded",
        "default_tick_effects": {"movement_cost": 1},
        "propagation": {"type": "through_open_ways", "rate": 0.02, "target_statuses": ["flooded"]}
    },
    "poison_gas": {
        "name": "Poison Gas",
        "default_tick_effects": {"damage": {"hp": 2}, "condition": "poisoned"},
        "propagation": {"type": "through_open_ways", "rate": 0.03, "target_statuses": ["poison_gas"]}
    }
}
```

## Engine Module

New file: `engine/area_statuses.py`

```python
class AreaStatusSystem:
    def __init__(self, graph):
        self.graph = graph

    def apply_status(self, area_id: str, status_type: str, severity: int = 1, duration: int = None, source: str = None) -> None:
        area = self.graph.get_node(area_id)
        if not area:
            return
        statuses = area.properties.setdefault("statuses", [])
        for s in statuses:
            if s["type"] == status_type:
                s["severity"] = min(5, s["severity"] + severity)
                if duration and s.get("duration") is not None:
                    s["duration"] = max(s["duration"], duration)
                return
        definition = AREA_STATUS_DEFINITIONS.get(status_type, {})
        new_status = {
            "type": status_type,
            "severity": severity,
            "duration": duration,
            "source": source,
            "tick_effects": dict(definition.get("default_tick_effects", {})),
            "propagation": definition.get("propagation"),
            "clear_conditions": list(definition.get("clear_on", []))
        }
        statuses.append(new_status)

    def process_tick(self) -> None:
        for area in self.graph.nodes.values():
            if area.type != "area":
                continue
            statuses = area.properties.get("statuses", [])
            if not statuses:
                continue
            env = area.properties.setdefault("environment", {})
            alive = []
            for status in statuses:
                effects = status.get("tick_effects", {})
                if "temperature" in effects:
                    env["temperature"] = float(env.get("temperature", 21)) + effects["temperature"]
                if "air" in effects:
                    env["air"] = effects["air"]
                if "light" in effects:
                    env["light"] = max(0, min(100, int(env.get("light", 0)) + effects["light"]))
                if "damage" in effects:
                    self._apply_area_damage(area.id, effects["damage"])
                if "condition" in effects:
                    self._apply_area_condition(area.id, effects["condition"])
                if status.get("duration") is not None:
                    status["duration"] -= 1
                    if status["duration"] <= 0:
                        continue
                alive.append(status)
            area.properties["statuses"] = alive
            for status in alive:
                if status.get("propagation"):
                    self._propagate_status(area.id, status)
```

## Trigger Integration

New trigger conditions:
- `area_has_status` — checks if area has a status type
- `on_status_applied` — fires when a status is added
- `on_status_tick` — fires each tick a status is active
- `on_status_cleared` — fires when a status expires or is cleared

New trigger effects:
- `apply_area_status` — adds a status to a area
- `clear_area_status` — removes a status type from a area

## Files Affected

1. `engine/area_statuses.py` — new module
2. `engine/tick_manager.py` — call `area_statuses.process_tick()` each turn
3. `engine/trigger_system.py` — add status conditions/effects
4. `engine/trigger_validator.py` — validate status params
5. `engine/effects.py` — `apply_area_status`, `clear_area_status` effect handlers
6. `engine/area.py` — ensure `statuses` field is initialized
7. `engine/serialization.py` — save/load `statuses`
8. `engine/area_description.py` — render active statuses in description

## Dependencies

- **Blocked by**: task-227 (forecast drives base environment; statuses layer on top)
- **Blocks**: task-232 (humidity could be a status or env property)

## Testing

- `on_fire` raises room temp +10/tick, deals 1 HP/tick, produces smoke
- `flooded` propagates to adjacent areas through open doors
- `poison_gas` spreads and applies `poisoned` condition to characters
- Status with `duration: 10` expires after 10 ticks
- `clear_area_status` removes status immediately
- Statuses persist through save/load
