---
type: task
status: todo
area: ui
priority: medium
---

# task-679: React-phase result is one wall of text ending in a raw way listing

**Filed:** 2026-10-04
**Related:** 

## Goal

The turn panel's react-phase result renders as a single prose blob that mixes the movement outcome, the room description, and a machine-formatted tail: 'You head through the grand_stairs. -- you're in upstairs hall. The light is dim... [grand_stairs_back] foyer is visible beyond (dimly lit, cool). [master_bedroom_door] a large oak door ... It is currently closed. [guest_room1_door] ...'. The trailing way enumeration duplicates data the scene view already renders as Ways out chips. Split the result into movement / prose / exits, clamp it, and drop or collapse the redundant tail.

## Acceptance

- TODO
