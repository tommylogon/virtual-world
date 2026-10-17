---
type: task
status: review
area: gameplay
priority: low
wiki: "[[Character Pursuits]]"
related: [task-691, task-714, task-809, task-810, task-812]
blocked_by: [task-807]
---

# task-811: GIMP: achievement log and goal replay

**Filed:** 2026-10-12
**Related:** task-714

<!-- deps:start -->
**Blocked by:** [[task-807-gimp-the-goal-model-and-its-serialization]]
**Related:** [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-809-gimp-create-goals-at-runtime-from-verbs-and-free-actions]], [[task-810-gimp-the-goal-graph-links-blocks-and-chaining]], [[task-812-mosiac-per-character-context-assembly-m-o-s-i-a-c]]
<!-- deps:end -->

## What

Record what a character achieved: which goals were reached and when, what was blocked, what was dropped, what changed over time - replayable.

## Why

Because the goal chain is data, a character's life can be played back. This is the payoff of the graph, and a debugging tool for the whole layer.

## How

An append-only `Player.goal_log` (character-private, like `goals`): each entry is `{goal_id, what, status, tick}`. The transition functions (`set_goal`, `set_status`) append to it when the caller passes the log and the world tick, so the verb path records automatically. The Mind panel shows it newest-first as "Goal history - replay". A goal that is *blocked* is derived from live world state (task-810), not an event, so the log records the transitions the character actually makes: created (active), changed, reached, dropped.

## Steps to verify

1. In the 🧠 Mind panel (`InspectorMindView`), open a character's goal history.
   - expected: the recorded transitions, in order, with ticks.
   - observed: VERIFIED 2026-10-12, live on localhost:4444. `goal set Hold the eastern gate` then `goal complete hold_the_eastern_gate` produced two log entries (active, then reached, both tick 59); the panel showed "GOAL HISTORY - REPLAY" with both, newest first.

## Acceptance

- [x] Every goal transition is logged with a tick.
- [x] A character's goal history can be read back in order.

## Files

- `engine/goals.py`
- `engine/serialization.py`
- `player.py`
- `routes/action_handlers.py`
- `static/js/inspector/mind-view.ts`

## Progress (2026-10-12)

- `engine/goals.py`: `_event`, `history`, and optional `tick`/`log` on `set_goal` / `set_status`.
- `Player.goal_log`; serialized in the players block, normalised on load, stripped in `lite`.
- `routes/action_handlers.py`: the `goal` verb passes `world.time_ticks` and `player.goal_log`.
- Mind panel: a "Goal history - replay" section (newest first).
- `tests/test_goals.py`: log append on create/update, malformed-row dropping, a scenario round-trip, and a wiring test through the dispatcher.
