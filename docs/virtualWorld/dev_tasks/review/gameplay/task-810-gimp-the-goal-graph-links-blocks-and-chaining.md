---
type: task
status: review
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

Relations are id-references inside the goal record, not graph edges: a goal is character-private data, so it cannot be a node (the 2026-10-12 decision, and [[Character Pursuits]]). A goal carries `blocks` (refs that gate it) and `links` (related refs). A ref is `prefix:value`, where the prefix is `goal` (another goal of the same character), `item`, `character` or `event`; a bare ref is a goal id. `blocks` is resolved on read against live world state (`engine/goals.world_resolvers`), and the derived `blocked_by` is a projection on the payload, never persisted.

## Steps to verify

1. In the 🧠 Mind panel (`InspectorMindView`), a goal blocked by an item shows that blocker, and one whose item the character holds does not.
   - expected: the blocker appears for an item the character lacks, and clears for one they hold.
   - observed: VERIFIED 2026-10-12, live on localhost:4445. `item:lost_relic_xyz` (missing) and `item:area_cooking_area` (a room, not an item) both showed outstanding; `item:item_shiny_coin`, which Arix wears, resolved satisfied with no `blocked_by`.
2. Chain: goal A blocked by goal B.
   - expected: reaching B unblocks A without a bespoke script.
   - observed: VERIFIED 2026-10-12. `Reach the chief` (blocks `b`) showed `⛔ blocked by b` in the Mind panel; after `goal complete b` the `blocked_by` cleared on the next read.

## Acceptance

- [x] A goal can be blocked and unblocked by world state.
- [x] Chains resolve without a script per goal.

## Files

- `engine/goals.py`
- `engine/serialization.py`
- `static/js/inspector/mind-view.ts`
- `static/js/inspector/agent-view.ts`

## Progress (2026-10-12)

- `engine/goals.py`: `TERMINAL_STATUSES`, `_ref_list`, `_split_ref`, `goal_resolver`, `resolve_blocks`, `is_blocked`, `outstanding_blocks`, `with_blockers`, `world_resolvers`. A goal ref is met when the referenced goal is reached or dropped; an unknown prefix holds the goal rather than freeing it.
- `engine/serialization.py`: `_goals_payload` derives `blocked_by` for the payload, skipping work when there are no goals.
- Mind panel: a `⛔ blocked by …` line on a blocked goal. Editor: a `blocks` field per goal row.
- `tests/test_goals.py`: chain resolution, comma-string refs, unknown-prefix hold, and `with_blockers` marking only the blocked goal.
