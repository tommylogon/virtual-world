---
group: Environment & Climate
---
# Area Status System

**Filed**: 2026-07-30  
**Priority**: Medium  
**Status**: Design  

---

## Summary

A flexible area status/effect system that models dynamic conditions in areas — fire, smoke, poison gas, extreme temperature, slime, magical fields, etc. — and how they affect characters and items. Trigger-driven for custom behavior.

---

## Problem

Areas currently have static environment properties (temperature, light level). There's no system for dynamic, layered area effects that change over time and interact with characters. A room can be "on fire" but there's no fire system. A room can be "full of poison gas" but there's no gas system. This limits storytelling and environmental gameplay.

## Requirements

### Area Status Entries
Each area gets a `statuses` list/dict, similar to how characters have conditions:
```json
{ 
  "type": "on_fire", 
  "severity": 3,        // intensity/stack level
  "duration": null,     // null = until cleared
  "source": "fireplace_item",
  "tick_effects": {
    "temperature": 15,
    "air": "smoke",
    "damage": {"hp": 2}
  }
}
```

### Status Types (examples)
| Status | Effects | Propagation | Clear Conditions |
|--------|---------|-------------|------------------|
| `on_fire` | +temperature, smoke, hp damage | Spreads to connected areas | Extinguished with water/sand |
| `flooded` | Movement cost, items float away | Drains to lower areas | Time / pump |
| `poison_gas` | Vital damage, coughing | Spreads through open doors | Ventilation / dissipation |
| `blessed` | Minor regen, morale boost | Doesn't spread | Duration expires |
| `darkness_magic` | Light level → pitch_black | Caster concentration | Dispel magic |

### Interactions
- **Triggers**: `on_status_applied`, `on_status_tick`, `on_status_cleared`
- **Hygiene connection**: certain area statuses affect hygiene (standing in slime, smoke residue, blood)
- **Items**: items can apply/clear area statuses (fire extinguisher clears `on_fire`)
- **Characters**: area statuses affect characters just like conditions — tick damage, stat modifiers, movement restrictions
- **Lighting**: smoke reduces light, fire increases light
- **Description**: area descriptions should reflect active statuses ("The room is filled with thick, acrid smoke...")

### Implementation Notes
- Build on top of the trigger system for custom behaviors
- `area.py`: add `statuses` field
- `engine/conditions.py` or new `engine/area_statuses.py` — process status ticks
- **Mirror the condition instance schema** (see [[review/characters/task-trait-condition-system-v2|task: Trait & Condition System v2]]): `tick_effects` ≈ per-instance `periodic`, `clear conditions` ≈ `ends_on`, `severity` ≈ `level`. Area statuses can apply character conditions via the same `apply_condition` effect (poison gas → `poisoned` instance).
- `engine/trigger_system.py` — area status triggers
- Propagation tick similar to heat propagation
- UI: show active statuses in area inspector with severity indicators

## Related

- [[review/environment/task-5-heat_propagation|task-5: Heat propagation]]
- [[review/environment/task-126-tag-based-light-and-heat-sources|task-126: Tag-based light and heat sources]]
- [[todo/environment/task-130-air-vacuum-atmospheric-effects|task-130: Air levels and atmospheric effects]]
