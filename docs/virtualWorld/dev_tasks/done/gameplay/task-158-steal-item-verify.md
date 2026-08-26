---
id: 158
title: Steal Item from Character (Verify Existing)
status: done
priority: low
created: 2026-08-02
tags: [characters, stealth, combat, verify]
---

# Steal Item from Character (Verify Existing)

## Summary

The "steal item from another character" feature already exists with a Sleight of Hand vs Perception contest. This task is to verify it works end-to-end and close out the idea.

## Status

Already implemented. `steal_item` in engine/item_actions.py:556 does a `Sleight of Hand` roll vs the target's `Perception` roll, moves the item on success, and raises "X notices you!" on failure. Command parsed by `steal X from Y` in routes/action.py:239. Review task [[review/gameplay/task-132-steal-command|task-132: steal command]] is also in the review queue.

## Verify

- [x] Steal succeeds when Sleight of Hand beats Perception
- [x] Failure produces a notice message and doesn't move the item
- [x] Can't steal from characters in other areas
- [x] Stealing equipped items works (EDGE_EQUIPPED is checked)

**Verified 2026-08-02** — all checks pass via `tests/test_item_actions.py::TestStealItem`. One bug found and fixed: the success path did not remove the `EDGE_EQUIPPED` edge when stealing an equipped item (item ended up equipped on the victim AND carried by the thief). Fixed in `engine/item_actions.py` — success now removes both `EDGE_CARRYING` and `EDGE_EQUIPPED`.

**Status: DONE** — moved to `done/gameplay/`.
