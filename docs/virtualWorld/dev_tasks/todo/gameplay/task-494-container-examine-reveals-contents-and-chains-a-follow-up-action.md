---
type: task
status: todo
area: gameplay
priority: medium
---

# task-494: Container examine reveals contents and chains a follow-up action

**Filed:** 2026-09-23
**Related:** task-352, task-493

## Goal

Make container contents an explicit reveal and allow a two-step single turn: examine <container> marks its contents discovered (they render 'known' and become usable), and the examine can be followed by one item action (take/use) in the same turn, mirroring the dash multi-step precedent (engine/movement.py dash_to_area, tick_manager.py move/dash handling) and governed by action_costs. Decide whether carried-container contents stop being auto-listed before an examine. Belongs with the task-352 action-economy work.

## Acceptance

- `examine <container>` marks its contents discovered so they render as known (and, if decided, are only listed after the examine).
- One follow-up item action (take/use) may occur in the same turn as the examine, governed by `action_costs`, mirroring the dash multi-step path.
- Single-action turns are unchanged when no follow-up is taken.
- Tests cover: the reveal, a chained take/use, and no chaining when the follow-up is disallowed.
