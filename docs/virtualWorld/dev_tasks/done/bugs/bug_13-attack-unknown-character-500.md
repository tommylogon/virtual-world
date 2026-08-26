# Bug 13: Attack on an unknown character → 500 (`get_player` AttributeError)

**Found**: 2026-08-06 (mansion sim — The Butcher `attack the man`)
**Fixed**: 2026-08-06 — verified live + regression tests
**Status**: Done

## Symptom

`attack the man` (target by stranger label) returned `500 Internal server error`, and the
event stream showed the action bubble with no output.

## Root cause

Two wiring bugs in `virtual_world_engine.py` `__init__` (line 102):

```python
self.combat = CombatSystem(self.graph, self, self.ghost_system, self)
```

1. Combat's 2nd arg (`skills`) received the `VirtualWorld` facade, which lacked
   `get_player` → `AttributeError: 'VirtualWorld' object has no attribute 'get_player'`
   at `combat.py:54` (`self.skills.get_player(attacker_name)`).
2. Combat's 4th arg (`npc_behaviors`) also received the facade, which lacks
   `process_npcs_on_combat` → second crash at `combat.py:73` once #1 was fixed.

Both real subsystems (`self.skills`, `self.npc_behaviors`) were created *after* combat in
`__init__`, which is why the facade was passed as a stand-in.

## Fix

- Added `VirtualWorld.get_player(name)` delegating to `player_manager.get_player`
  (`virtual_world_engine.py`, Player Management section).
- Moved `self.combat = CombatSystem(...)` to after `self.npc_behaviors` and pass the real
  subsystem: `CombatSystem(self.graph, self, self.ghost_system, self.npc_behaviors)`.
- The facade-as-`skills` design stays (combat already used `self.skills.roll_dice`,
  `.is_slasher`, `.time_ticks` through the facade).

The unknown-name resolution itself already worked: `attack the man` →
`_match_character_name("the man")` → "Jake Halloway" (by description), which the route
did before calling combat. Verified live: `The Butcher attacks Jake Halloway! (N damage)`.

## Regression tests

- `tests/test_combat.py::TestWorldFacadeWiring::test_player_attack_via_world_facade`
- `tests/test_combat.py::TestWorldFacadeWiring::test_world_facade_exposes_get_player`

Suite: 513 passed, 1 skipped.
