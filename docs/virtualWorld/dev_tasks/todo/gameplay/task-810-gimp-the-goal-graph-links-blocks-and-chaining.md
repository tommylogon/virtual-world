---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-426, task-691, task-714]
blocked_by: [task-807]
---

# task-810: GIMP: the goal graph - links, blocks and chaining

**Filed:** 2026-10-12
**Related:** task-426

<!-- deps:start -->
**Blocked by:** [[task-807-gimp-the-goal-model-and-its-serialization]]
**Related:** [[task-426-plan-archetypes-and-group-goals]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

Goals linked and blocked by other goals, characters, events or items, so goals chain up.

## Why

A goal's fate usually depends on another (waiting on an item, blocked by a character, gated by an event). Without the graph, replay and blocking cannot be tracked.

## How

Goal <-> goal/character/event/item relations as edges, in the manner of the world graph. Blocked-by evaluated against world state each tick.

## Steps to verify

1. In the 🧠 Mind panel (`InspectorMindView`), a goal blocked by an item shows that blocker.
   - expected: acquiring the item clears the block there (and in state).
   - observed: TODO
2. Chain: goal A blocked by goal B.
   - expected: reaching B unblocks A without a bespoke script.
   - observed: TODO

## Acceptance

- [ ] A goal can be blocked and unblocked by world state.
- [ ] Chains resolve without a script per goal.

## Files

- `engine/goals.py`
- `graph.py`
