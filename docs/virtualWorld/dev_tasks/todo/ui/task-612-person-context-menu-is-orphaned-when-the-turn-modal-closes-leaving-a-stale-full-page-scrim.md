---
type: task
status: done
area: ui
priority: medium
---

# task-612: Person context menu is orphaned when the turn modal closes, leaving a stale full-page scrim

**Filed:** 2026-09-30
**Related:** 

## Goal

Open a person menu in the HTC modal, then dismiss the modal. The THE WOMAN / Talk to / Examine / Attack panel stays rendered with no owner, and a transient .tsv-scrim (z-index 1390, position fixed, pointer-events auto, full viewport) swallows the next click before clearing. Symptom is a one-click tax or a double-click-to-act, not a lockout.

## Acceptance

- TODO
