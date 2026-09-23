---
type: task
status: todo
area: characters
priority: low
---

# task-490: Incorporeal undead: damage resistance and condition immunities

**Filed:** 2026-09-23
**Related:** task-309

## Goal

Complete the still-open part of task-309: D&D-style damage resistance/immunity for incorporeal undead (resistance to nonmagical weapons, immunity to cold/necrotic/poison) and condition immunities (grappled/restrained/prone/exhausted/...). Engine hooks: engine/combat.py damage resolution and engine/conditions.py application.

## Acceptance

- Incorporeal undead take reduced or no damage from nonmagical weapons and are immune to cold/necrotic/poison.
- Condition immunities: grappled/restrained/prone/exhausted (and the rest of the 5e ghost list) cannot be applied to them.
- Keyed off the incorporeal/undead identity from task-309 (`engine/combat.py`, `engine/conditions.py`).
- Tests covering resistance/immunity and condition application.
