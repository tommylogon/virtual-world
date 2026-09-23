# Bug 25 — take/wear no-ops read as failures and duplicate-wear stacks

**Status:** Done — reframed and closed 2026-09-22. The engine-side messaging fix
was already in place; the remaining live repro was a duplicate-item-instances
data problem, split out to task-450.

## Original defect (2026-08-24, taco_bell)

1. miki, already carrying the Mystery Cream Sauce, submitted `take` again and got
   a *search-failure* string ("You search for ... but can't find it here. Items
   you can see: ..."), with the hint listing **characters**.
2. miki spawned wearing one Blue Butterfly Earring and carrying a second; `wear`
   appended the found copy to the worn stack → "Blue Butterfly Earring over Blue
   Butterfly Earring".

## Fix (shipped)

- `engine/items/take_drop_actions.py` — `take_item` checks carried/equipped roots
  first and returns a soft no-op ("You're already carrying/wearing the X."); the
  not-found hint lists items only, never characters.
- `engine/equipment.py` — `equip_item` refuses a second instance of the same-named
  worn item ("You're already wearing the X.").
- Tests: `TestTakeAlreadyHeld`, `test_cannot_wear_second_copy_of_same_item`,
  `test_equip_same_item_twice_refused`.

## Why it was reopened, and the reframe (2026-09-22)

The 2026-08-30 reopen repro was:

```
[Tick 3] John two > take jumpsuit
[Tick 4] World You're already carrying the Jumpsuit.
[Tick 5] John two > equip jumpsuit
[Tick 6] World You're already wearing the Jumpsuit.
```

Those are the *fixed* messages — the code path is not the bug. The contradictory
carrying-then-wearing sequence can only occur when the character holds **two
same-named instances** (one carried, one worn) or one node with both a `CARRYING`
and an `EQUIPPED` edge. `equip_item` removes the `CARRYING` edge, so in normal
play a node cannot hold both; the state comes from duplicate spawns/dressing and
from load/legacy paths that add `CARRYING` without clearing `EQUIPPED`.

Two follow-ups landed here:

- **Engine hardening:** `take` now scans `EQUIPPED` before `CARRYING`, so a worn
  item with a stale carry edge reports the truthful "already wearing" (test:
  `test_take_worn_item_with_stale_carry_edge_prefers_wearing`).
- **Give transfer:** handing over a **worn** item now also removes its dangling
  `EDGE_EQUIPPED` edge (and multi-slot markers), not just `CARRYING`
  (`engine/items/transfer_actions.py`).

The remaining data-side root cause (two same-named item nodes on one character)
is split out to **task-450** (`todo/items/`), which also adds a carried+equipped
invariant at the load boundary.

## Verification

- `tests/test_item_actions.py::TestTakeAlreadyHeld` (carried / worn / worn+stale
  carry edge), `tests/test_equipment_system.py` layering tests.
- `tests/test_item_actions.py::TestGiveItem::test_give_worn_item_transfers_and_unequips`.
