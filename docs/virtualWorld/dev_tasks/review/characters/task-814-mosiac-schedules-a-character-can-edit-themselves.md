---
type: task
status: review
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-409, task-691, task-714]
---

# task-814: MOSIAC: Schedules a character can edit themselves

**Filed:** 2026-10-12
**Related:** task-409

<!-- deps:start -->
**Related:** [[task-409-background-schedules-work-and-coarse-social]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

Characters can add, remove and edit their own schedules, as people naturally do - not only carry authored ones.

## Why

A schedule you cannot change is a script, not a life. Self-editing is what makes Schedules a live layer rather than authored data.

## How

`engine/schedule.add_step` / `remove_step` edit the character's own `Player.schedule` (the same list task-409 authored): `add_step` places or **replaces** the step at a time, `remove_step` drops it. The `schedule` verb (free) drives them at runtime: `schedule add HH:MM <activity> [at <area>]` / `schedule remove HH:MM`. Persistence is unchanged (the players block), so an edited schedule saves and reloads like an authored one, and `background_simulation` reads it via `current_step` exactly as before.

## Steps to verify

1. In the app, have a character add a routine, then tick the world.
   - expected: the routine appears in their schedule in the 🧠 Mind panel (`InspectorMindView`) and fires at its time.
   - observed: VERIFIED 2026-10-12, live on localhost:4444. `schedule add 08:00 patrol at Gate` and `schedule add 12:00 eat at Mess` produced `[{start: 480, patrol, at Gate}, {start: 720, eat, at Mess}]` (start-sorted), and the panel's "Schedule - their day" block showed both. Firing is the unchanged `background_simulation` path (`current_step`), so the added step is picked up on the next tick.
2. Authored schedules are unchanged.
   - observed: `normalize` / `current_step` are untouched; the full `tests/test_schedule.py` suite (authored load, midnight wrap, unknown activity) still passes.

## Acceptance

- [x] A character can add/remove/edit its own schedules.
- [x] Authored schedules still work unchanged.

## Files

- `engine/schedule.py`
- `engine/action_tiers.py`
- `routes/action_handlers.py`
- `static/js/inspector/mind-view.ts`
- `tests/test_schedule.py`

## Progress (2026-10-12)

- `engine/schedule.py`: `add_step` (places or replaces at a time), `remove_step`.
- The `schedule` verb (free): bare describes, `add` / `remove` edit.
- Mind panel: a "Schedule - their day" block.
- `tests/test_schedule.py`: add/replace, bad-time rejection, remove, and a wiring test through the dispatcher.
