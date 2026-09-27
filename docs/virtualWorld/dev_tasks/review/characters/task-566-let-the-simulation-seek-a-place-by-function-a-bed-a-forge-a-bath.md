---
type: task
status: todo
area: characters
priority: medium
---

# task-566: Let the simulation seek a place by function (a bed, a forge, a bath)

**Filed:** 2026-09-27
**Related:** task-561 task-563

## Goal

A painted town is a service directory (The Stag Inn for travellers, The Crooked Mug for locals, the Silver Lily, a smithy, a bathhouse, a ferry), but nothing in the sim asks where any of that is: there is no venue concept at all, so a tired traveller walks the streets instead of seeking a bed. This is the difference between a painted map and a living town, and it is the item that makes a settlement matter to the simulation rather than to the eye. Needs a place lookup by kind (task-561's building types) and a need->venue mapping, then a decision about how a character chooses among several inns. Deliberately separate from the authoring tasks: it touches needs/background_sim, not the compiler.

## Acceptance

- TODO
