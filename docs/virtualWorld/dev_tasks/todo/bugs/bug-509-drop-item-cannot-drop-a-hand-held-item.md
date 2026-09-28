---
status: todo
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
