---
type: task
status: todo
area: ui
priority: high
---

# task-610: Human turn modal exposes 3 of ~23 backend character-to-character actions

**Filed:** 2026-09-30
**Related:** [task-602]

## Goal

The HTC person menu offers only Talk to / Examine / Attack. The backend supports ~23: attack, approach, grab, release, escape, lead, give, steal, name, teach, shout, whisper, scream, sing, wake, relieve, plus 8 intimate verbs in engine/pleasure_actions.py (kiss, lick, suck, bite, caress, pinch, blow, tickle) each with an authored default body region, plus the grapple subsystem with per-hand targeting. 8 of those verbs are body-part-targeted, so they depend on the same region mechanism task-602 fixes.

## Acceptance

- TODO
