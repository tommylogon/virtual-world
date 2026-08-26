---
id: 164
title: Size Limits on Ways
status: done
priority: low
created: 2026-08-02
tags: [graph, ways, movement, gating, stateful-actions]
---

# Size Limits on Ways

## Summary

Add size requirements to ways. A small tunnel can't fit a large character, and a normal-sized character may need to crawl — tying into stateful actions where a character is set to `busy` while passing through certain ways.

## Status — implemented 2026-08-06 via task-187

This task is **superseded by [[dev_tasks/review/gameplay/task-187-character-size-passage-movement|task-187]]**, which delivered size limits on ways with a simpler design:

- **Implemented**: way `max_size` property (tiny…titanic dropdown in the way inspector), size-gated movement in `move_to_area` (1 tier over → auto-crawl, ≥2 tiers over → blocked).
- **Variance**: size is a mutually-exclusive **trait** (`size_*`, six tiers) rather than a character property; crawling is a per-move modifier (flavor + gating, no cost scaling — the way's `cost.time` is a duration hint for task-131, not per-action clock advancement) rather than a stateful `busy` action — the stateful, interruptible mid-crawl (with rollback/stuck states) is explicitly deferred in task-187's design.
- **Tested**: `tests/test_movement.py::TestSizePassage` (10 tests).

## Original Problem

Ways have no size concept (engine/movement.py:46 `connect_areas` sets state/desc/cost only). A 2-meter character can walk through a cat tunnel like nothing. Movement gating currently only knows locked/blocked/closed states.

## Original Implementation Plan

### Way size property

- Add `size` to way properties: e.g. `tiny` (crawl), `small`, `normal`, `large`, `huge`
- Add `size` to character properties (or infer from stats/traits)
- Movement check: character can't pass if their size > way size (raise "The tunnel is too small for you to fit through.")

### Crawl stateful action

- Normal-sized character through a tiny way must crawl: a stateful action (ties into [[todo/gameplay/task-131-stateful-actions-over-time|task-131]]) that sets `player.activity` to `crawling` / state `busy` while passing
- Crawling sets the character to `prone`-like state: slower, can be interrupted, no other actions mid-crawl
- If interrupted mid-way, the "cancelled" passage may need to roll back or leave the character stuck in the tunnel

### Editor

- Add size dropdown to the way editor

## Files to Modify

1. `engine/movement.py` — size gate on move_to_area
2. `engine/movement.py` / `engine/tick_manager.py` — crawl as stateful action
3. `routes/graph.py` + way editor JS — size field
4. `player.py` — character size field

## Testing

- [x] Large character blocked by tiny way
- [x] Small character passes freely
- [x] Normal character crawls (per-move, no cost scaling — stateful busy crawl deferred)
- [ ] Interrupted crawl leaves a sensible state (deferred — no stateful crawl in v1)

## Related

- [[dev_tasks/review/gameplay/task-187-character-size-passage-movement|task-187: Character size + passage movement]]
- [[todo/gameplay/task-131-stateful-actions-over-time|task-131: Stateful actions over time]]
- [[todo/graph/task-128-one-way-ways|task-128: One-way ways]]
