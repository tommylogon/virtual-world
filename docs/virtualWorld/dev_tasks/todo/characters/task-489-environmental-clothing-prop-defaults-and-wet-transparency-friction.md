---
type: task
status: todo
area: characters
priority: low
---

# task-489: Environmental clothing: prop defaults and wet transparency/friction

**Filed:** 2026-09-23
**Related:** task-215

## Goal

Finish task-215: give item nodes default comfort/friction/coverage/opacity (opacity 0.8, coverage 0.8 when absent), and couple the existing wet state (condition 'wet', equipment_bonuses.py:107) to clothing opacity/friction so rain/swimming makes layers more see-through and changes friction, then triggers description regeneration. Friction->arousal trickle already ships (engine/tick_manager.py:1028) as does weather/wind/humidity.

## Acceptance

- Item nodes expose `comfort`/`friction`/`coverage`/`opacity`, with `opacity`/`coverage` defaulting to 0.8 when absent, surfaced by `_equipment_detail_lines()` (`engine/equipment.py:645`).
- The `wet` condition raises clothing `opacity` (more see-through) and changes `friction`.
- The state change retriggers the equipment description when `world.auto_generate_descriptions` is on (coordinate with task-486).
- Arousal coupling stays `mature_content`-gated; wetness/transparency itself is generic.
- Tests for the prop defaults and the wet coupling.
