---
type: task
status: todo
area: gameplay
priority: low
wiki: "[[Character Pursuits]]"
related: [task-691, task-714]
blocked_by: [task-807]
---

# task-811: GIMP: achievement log and goal replay

**Filed:** 2026-10-12
**Related:** task-714

<!-- deps:start -->
**Blocked by:** [[task-807-gimp-the-goal-model-and-its-serialization]]
**Related:** [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

Record what a character achieved: which goals were reached and when, what was blocked, what was dropped, what changed over time - replayable.

## Why

Because the goal chain is data, a character's life can be played back. This is the payoff of the graph, and a debugging tool for the whole layer.

## How

Append-only goal events (reached/blocked/dropped/changed) with a tick. A read or view that plays them back.

## Steps to verify

1. In the 🧠 Mind panel (`InspectorMindView`), open a character's goal history.
   - expected: reached / blocked / dropped / changed in tick order, replayable.
   - observed: TODO

## Acceptance

- [ ] Every goal transition is logged with a tick.
- [ ] A character's goal history can be read back in order.

## Files

- `engine/goals.py`
- `routes/`
