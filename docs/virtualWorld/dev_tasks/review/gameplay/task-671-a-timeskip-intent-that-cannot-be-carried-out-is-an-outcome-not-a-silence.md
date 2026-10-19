---
type: task
status: review
area: gameplay
priority: high
---

# task-671: A timeskip intent that cannot be carried out is an outcome, not a silence

**Filed:** 2026-10-02
**Related:** task-670, task-464, task-475

## What

Measured 2026-10-02 on data/scenarios/kraktooth_goblin_camp.json. (a) travel by heading with no exit that way: full 30 min elapse, no interrupt, character does not move, summary reads 'travel for 30 min @ Animal Pens'. (b) same exit but the way is blocked: identical, and the refusal only reaches logger.info. (c) search for a named target that exists nowhere: the character NEVER leaves the room (a name with no tag only looks in the current area, then falls through to maintenance), runs the whole span, and never says not-found. Fix: a blocked/no-exit interrupt naming the obstacle, a named search that actually routes toward the target, and a conclusive 'there is no X' when the world holds no such node.

## Acceptance

- [x] (a) travel by heading with no exit that way stops and says so - interrupt
      `kind="no_exit"`, names the bearing, character does not move
      (`engine/timeskip.py:543 _move_heading`, wired at `:293-303`; test
      `tests/test_timeskip.py::test_a_heading_with_no_exit_that_way_stops_and_says_so`).
- [x] (b) a blocked passage stops and names the obstacle - interrupt
      `kind="passage"` with a detail that reaches the player, not just
      `logger.info` (`tests/test_timeskip.py::test_a_blocked_passage_stops_and_names_the_obstacle`).
- [x] (c) a named search the world does not hold is conclusive - interrupt
      `kind="notfound"`, "There is no X to be found." (`_policy_step:453-457`,
      `_not_found_detail`; `tests/test_timeskip.py::test_a_search_for_something_the_world_does_not_hold_says_it_is_not_there`).
- [x] a named search routes toward the area that actually holds the target
      instead of looking only in the current room (`_areas_holding`,
      `_policy_step:458-464`; `tests/test_timeskip.py::test_a_named_search_walks_toward_where_the_target_actually_is`).
- [x] `advance()` converts `PolicyStep.blocked` into a salient interrupt and
      hands control back (`engine/timeskip.py:293-303`).

**Verified 2026-10-08:** `python -m pytest tests/test_timeskip.py` - **58 passed**.

## Why

When an intended timeskip action (such as traveling along a heading with no exit, traveling through a locked/blocked passage, or searching for a nonexistent item) could not be executed, the engine previously swallowed the failure silently while consuming the full duration (e.g. 30 minutes). The player was presented with a misleading summary claiming the task was performed while the character stood still. Surfacing these failures as salient interrupts with descriptive feedback gives players actionable knowledge and hands control back immediately.

## How

1. In engine/timeskip.py, detect when a heading has no valid exit in _move_heading and trigger an interrupt (kind='no_exit').
2. Surface passage refusals (kind='passage') with specific blocker details in the user-visible interrupt summary instead of logging to logger.info.
3. In _policy_step, check if named search targets exist anywhere in the world; if not, trigger a conclusive kind='notfound' interrupt ('There is no X to be found.') rather than falling back to endless idle maintenance.
4. Route named searches toward candidate areas identified by _areas_holding.
5. Update advance() to convert PolicyStep.blocked into a salient interrupt returning control to the caller.

## Steps to verify

1. Execute a heading timeskip toward a direction with no exit.
   - expected: Timeskip halts immediately with no_exit interrupt naming the bearing; character remains at starting room.
   - observed: Tested via test_a_heading_with_no_exit_that_way_stops_and_says_so.
2. Attempt timeskip travel through a blocked way.
   - expected: Timeskip interrupts with passage and details describing the obstacle.
   - observed: Tested via test_a_blocked_passage_stops_and_names_the_obstacle.
3. Search for a nonexistent item in a timeskip.
   - expected: Timeskip halts with notfound interrupt stating target cannot be found.
   - observed: Tested via test_a_search_for_something_the_world_does_not_hold_says_it_is_not_there.

## Files

- engine/timeskip.py
- 	ests/test_timeskip.py
