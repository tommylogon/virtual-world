---
status: done
type: bug
area: bugs
priority: medium
---

# bug-509: drop_item only scans the carrying edge, so a hand-held item cannot be dropped

**Filed:** 2026-09-28
**Related:** task-493

## Symptom

Take anything, then drop it:

```
> take bread
You take the bread with your right hand.
> drop bread
ValueError: You aren't carrying 'bread'.
```

## Cause

Two halves of the same contract disagree.

`TakeDropActionsMixin.take_item` puts every non-intrinsic item into a **hand**
(task-146): `if not is_intrinsic and not hand_slots: hand_slots = ["hand_right",
"hand_left"]`, so an item that declares no `equip_slots` still gets
`EDGE_EQUIPPED`.

`TakeDropActionsMixin.drop_item` resolves its target by scanning **only**
`EDGE_CARRYING` off the player node:

```python
for edge in self.graph.get_edges_for_target(player_id, EDGE_CARRYING):
    node = self.graph.get_node(edge.source)
    if node and node.name == item_name:
        item_node_id = node.id
        break
else:
    raise ValueError(f"You aren't carrying '{item_name}'.")
```

`EDGE_EQUIPPED` is never consulted, so the item the player is visibly holding
is "not carried" as far as drop is concerned. Only an intrinsic ability
(spell, talent), which skips the hand step, or an item dropped straight onto
the `carrying` edge by some other path, can be dropped at all.

## Impact

Dropping is effectively unavailable for anything picked up by hand — which is
most things. The failure message is also actively misleading: the character is
holding the item.

## Fix

Scan `EDGE_CARRYING` **and** `EDGE_EQUIPPED` when resolving the drop target,
and pop the item id from the player's `equipped` slot list (the unequip loop
just below the resolution already does this once the node is found, so it
mostly needs to run in both cases). Carry-capacity/weight accounting is
unaffected: the item is moving, not being destroyed.

## Verification

```
python -m pytest tests/test_item_actions.py -q
```

Add a regression test: take an item that declares no hand slots, drop it, and
assert the `equipped` edge is gone and the item is in the area. Note that
`tests/test_item_parts.py::test_an_ordinary_item_is_still_put_and_taken`
deliberately exercises put→take rather than take→drop, and says why — this
test can be simplified once the bug is fixed.

## Fix — 2026-10-02

The engine half was already fixed by commit `ac35ac0` (task-633): `drop_item`
now scans `(EDGE_CARRYING, EDGE_EQUIPPED)` and matches the name
case-insensitively, and the unequip loop already pops the `equipped` slot. What
was missing was the regression proof this task asked for.

- `tests/test_item_actions.py::TestDropItem` — `test_take_then_drop_a_hand_held_item`
  runs the real take → drop loop on an item with no declared `equip_slots`, and
  asserts the `equipped` and `carrying` edges are gone, the hand slot is
  emptied, and the item is back in the area.
  `test_drop_resolves_an_equipped_item_by_case_insensitive_name` pins the
  lowercased-verb path.
- `tests/test_item_parts.py` — the stale docstring claiming the carrying-only
  gap was "deliberately not fixed" was corrected; the test still exercises
  put → take, with the take → drop counterpart now covered in
  `test_item_actions.py`.
- `engine/items/take_drop_actions.py` — comment now names bug-509 alongside
  task-633 for traceability (no behaviour change).

Evidence: `python -m pytest tests/test_item_actions.py tests/test_item_parts.py -q`
→ 102 passed. Live-browser take → drop check still pending for `done`.

## Live verification — 2026-10-02 (port 4471, real commands)

Through `POST /api/action` as Kaelen Voss (Blizzard Forest Clearing), on the
item "Lumber Axe":

| command | output | area items after |
|---|---|---|
| `take Lumber Axe` | "You take the lumber axe with your hand right." | `[]` (in hand) |
| `drop Lumber Axe` | **"You drop the lumber axe."** | `["Lumber Axe"]` |

The drop succeeds because `drop_item` now resolves the `equipped` edge the take
created; before the fix it scanned only `carrying` and would have answered that
the character did not have it. No page errors. Moving to `done`.
