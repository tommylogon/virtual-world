---
group: Agent AI & Behavior
wiki: "[[Characters/NPC Behavior System]]"
---
# NPC Behavior Movement Enhancement (Go / Random / Patrol)

**Filed**: 2026-07-15
**Priority**: High
**Status**: In Review — implemented 2026-08-13. `go` modes in `engine/npc_behaviors.py`; patrol state on `Player`; inspector mode dropdown; 7 tests in `tests/test_npc_behaviors.py`.

---

## Summary

The `go` action in the behavior system currently teleports an NPC directly to a named room — no pathfinding, no door checks, no randomness. It needs to support three movement modes: pathfinding to a specific room via ways, moving to a random connected room, and cycling through a patrol route.

## Implemented

### Backend (`engine/npc_behaviors.py`)

- `execute_go_action(char_name, action)` dispatches on `mode`:
  - **`goto`** (default): `_get_path_to_area()` + `movement.move_to_area()` — one step, respects doors/locks/costs
  - **`random`**: random open exit (legacy wander logic)
  - **`patrol`**: reads/writes `player.patrol_route` + `patrol_index`; advances on arrival
- `_execute_behavior_actions` `go` handler delegates to `npc_behaviors.execute_go_action()`
- Backward compat: `area` or `room` field, default mode `goto`

### Player model (`player.py`, `engine/serialization.py`)

- `patrol_route: list`, `patrol_index: int` — serialized in saves/templates

### Frontend (`static/js/inspector/behaviors-view.js`)

- `go` action: mode dropdown (goto / random / patrol)
- Conditional fields: target area (goto), comma-separated areas (patrol)
- `toggleGoModeFields()` for field visibility

### Tests

- `tests/test_npc_behaviors.py`: goto via way, random, patrol cycle, locked door blocked

## Verification

```powershell
python -m pytest tests/test_npc_behaviors.py -q
node --check static/js/inspector/behaviors-view.js
```

Browser E2E: rat Kitchen ↔ Cellar via trapdoor after reset — pending manual check.

## Original design (reference)

See git history / prior `todo/characters/task-8-npc_behavior_movement.md` for full design notes.
