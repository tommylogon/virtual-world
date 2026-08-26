---
id: 157
title: Put Item in Container (Verify Existing)
status: done
priority: low
created: 2026-08-02
tags: [items, containers, verify]
---

# Put Item in Container (Verify Existing)

## Summary

The "put item in container" feature already exists. This task is to verify it works end-to-end and close out the idea.

## Status

Already implemented. `put_item_in_container` exists in engine/item_actions.py:481, capacity checks in `_check_container_capacity` (engine/item_actions.py:626), and the command is parsed by `put X in Y` in routes/action.py:230.

## Verify

- [x] `put apple in backpack` moves the item into the container
- [x] Capacity error shows when the container is full
- [x] `take apple from backpack` works
- [x] Items in containers show up in examine output (reachable for examine/take)
- [x] Containers placed in the world (not just inventory) work

**Verified 2026-08-02** — all checks pass via `tests/test_item_actions.py::TestPutInContainer` (carried containers, world-placed containers, capacity enforcement, take-back, non-container rejection).

**Status: DONE** — moved to `done/items/`.
