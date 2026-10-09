---
type: bug
status: review
area: world
priority: medium
---

# bug-530: Compiled open outdoor ways miss prevent_close so a road into the forest can be hand-closed

**Filed:** 2026-10-08
**Related:** task-522 task-223

## Goal

engine/world_compile.py sets prevent_close only in _apply_way_blocking (line 415), so of 378 generated ways in data/scenarios/kraktooth_goblin_camp.json only the 32 blocked ones carry it and the 345 open outdoor ways do not. That contradicts engine/movement.py:1045-1053, whose comment states a compiled outdoor way carries prevent_close because you cannot close a road into a forest by hand; today a character can close one. Set prevent_close: True on outdoor ways (kind 'open'/'stairs') in way_props, but not on kind 'door' (a building door must still close). Regression test: a character close is refused on an open outdoor way and allowed on a door way.

## Acceptance

- [x] `way_props` sets `prevent_close: True` for `kind in ("open", "stairs")`, not for `door`.
- [x] `tests/test_way_blocking.py::test_a_compiled_open_outdoor_way_carries_prevent_close` (4x4 grid) and `::test_a_compiled_open_outdoor_way_refuses_a_hand_close` (3x3 grid → movement refusal).
- [x] Full `tests/test_way_blocking.py` (35) + `tests/test_world_compile.py` + `tests/test_way_property_index.py` (121) pass.

**Landed 2026-10-08:** `engine/world_compile.py`, one branch in the way builder before `nodes.append`. A blocked way was already covered by `_apply_way_blocking`, so this only closes the gap for the open/stairs subset. No save-format change; existing saves pick the flag up on the next compile.
