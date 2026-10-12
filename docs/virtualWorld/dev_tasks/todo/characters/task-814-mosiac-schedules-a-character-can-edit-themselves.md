---
type: task
status: todo
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

Extend engine/schedule.py with runtime add/remove/edit driven by goals and events. Persist per character.

## Steps to verify

1. In the app, have a character add a routine, then tick the world.
   - expected: the routine appears in their schedule in the 🧠 Mind panel (`InspectorMindView`) and fires at its time.
   - observed: TODO

## Acceptance

- [ ] A character can add/remove/edit its own schedules.
- [ ] Authored schedules still work unchanged.

## Files

- `engine/schedule.py`
- `engine/serialization.py`
- `player.py`
