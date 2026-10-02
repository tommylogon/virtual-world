---
type: task
status: review
area: gameplay
priority: medium
---

# task-473: Item stacks and relational piles (grouped world items)

**Filed:** 2026-09-23
**Related:** task-471, task-470, task-424, task-9

## Goal

Group world items so a camp can hold a 50-use pile of raw meat or a herb pile of distinct herbs without hundreds of nodes. Two models: (a) HOMOGENEOUS STACK - one node carrying N uses; taking spawns one discrete item into the taker's inventory and decrements; placing a matching item (same key tags) adds a use and removes the node. (b) RELATIONAL PILE - a container holding distinct child items, so different herbs with different effects coexist and can be taken individually. Uses drive crafting/cooking (raw_meat + campfire -> cooked_meat, spending a use), reduce wild-item count, and keep soak search/forage output tidy. Needs: an explicit stack marker in the item schema, take-from-stack and merge-on-put in the item actions, capacity/weight interaction with containers, and save/load of uses.

## Acceptance

- [x] A world item can author `stackable: true` and carry N `uses`.
- [x] `take` from a `stackable` node spawns one discrete copy (uses 1) into the
      taker's inventory and decrements the stack; the last unit is picked up
      whole; a full pack leaves copies on the ground.
- [x] Dropping or putting a `stackable` item onto/into a matching stack merges
      (uses add, clamped at `max_uses`, weight reconciled) and destroys the
      moved node.
- [x] The merge predicate (`stackable_twins`) still refuses pools and unmarked
      props, so ordinary identical items never fuse.
- [x] A relational pile is authored via the existing `contents`/EDGE_IN model
      (`foraged_herb_pile`) and its children are individually takeable.
- [x] `combine`/`split` are surfaced in an item's available actions.
- [x] Save/load of stacked `uses` needs no schema work (item properties
      serialize verbatim, proven by test_item_quantity).

## Resolution (2026-10-02)

The two models existed only in the opposite direction before this: task-504's
`quantity` pool harvests a *world count* into copies, and task-155's `combine`
merges two *carried* `uses` copies. What was missing was a world-side
homogeneous stack you draw from, and merge-on-put.

- `engine/items/stacking.py`: `is_stackable()` (explicit opt-in marker),
  `merge_stack_into()` (merge a moved node into a matching stack at a container
  or area), `take_from_stack()` (draw k units, spawn uses-1 copies, decrement,
  remove at zero). `split_item` now uses a uuid id instead of the fixed
  `{id}_part`, which silently overwrote on a second split.
- `engine/items/take_drop_actions.py`: `take` routes a `stackable` node with
  `uses > 1` to `take_from_stack`; `_find_stack_by_name` gives a standing stack
  the same precedence over "already carrying" that a standing pool already had;
  `drop_item` merges into a matching stack in the area.
- `engine/items/place_actions.py`: `put_item_in_container` and
  `place ... in <container>` merge into a matching child stack.
- `engine/effects.py` / `engine/library_nodes.py`: carry `stackable`,
  `max_uses`, `base_weight` through hydration and library placement.
- `engine/triggers/ui.py`: expose `combine`/`split` for stackable items.
- Content: `pile_of_raw_meat` (12-use homogeneous stack) and
  `foraged_herb_pile` (relational pile of four distinct herbs).

Tests: `tests/test_item_stacks.py` (take/decrement/last-unit, merge-on-drop,
merge-on-put, split-id regression, unmarked-prop non-merge, authored content).
`python -m pytest tests/test_item_stacks.py -q` -> 11 passed.

Not done: a UI field for the `stackable` marker (inspector) — the marker is
engine-side; the item editor shows `uses`/`max_uses` already.
