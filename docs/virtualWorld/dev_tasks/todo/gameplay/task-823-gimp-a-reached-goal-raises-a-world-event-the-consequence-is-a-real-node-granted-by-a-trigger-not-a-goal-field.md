---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Character Pursuits]]"
blocked_by: [task-822]
---

# task-823: GIMP: a reached goal raises a world event - the consequence is a real node granted by a trigger, not a goal field

**Filed:** 2026-10-13
**Related:** task-822, task-807, task-810, task-811, task-714

<!-- deps:start -->
**Blocked by:** [[task-822-gimp-goal-data-reason-carrying-refs-achievement-predicates-and-auto-reached]]
<!-- deps:end -->

## What

When a goal is reached (task-822), the engine raises a **world event** - `goal_reached`, carrying the actor and the goal id. An **ordinary trigger** answers it: for `become_chief`, a trigger on `goal_reached` nests `item_chiefs_staff` to the actor. The staff is then a normal node - stealable, covetable, tradeable - by the mechanics that already exist.

The goal carries only the *hope* in prose (`hoped_for`). It carries **no** `grants`, no reward table, no effect list.

## Why

"Becoming chief gives you the chief's staff" is a real and good consequence - and it only means anything if the staff is an actual node another character can steal or want. The design forbids the other shape: [[Character Pursuits]] states *"a character's hoped-for consequence is prose/motive; actual consequences are determined by world and relationship rules"* and *"neither representation turns a pursuit into a forced script or an artificial reward contract."* A `grants:` list on the goal would be exactly that contract - and a second effect system living beside triggers.

## How

- `sync_reached` (task-822), on a flip to `reached`, dispatches `goal_reached` with `{actor, goal_id, what}` through the existing event path, so triggers can fire on it.
- Consequence = a normal trigger: condition `event: goal_reached` + a goal filter (id/what) + an effect that grants/nests an item to the actor - the same effect item triggers already use. No new effect, no economy code.
- The granted item is a plain node: containment / `EDGE_IN` to the actor, then steal/covet/trade work unchanged.
- One event type, filtered by goal id and actor. Decide the scope (world event vs per-actor) once, keep it one mechanism.

## Steps to verify

1. Author a goal `become_chief` whose `achieve` can be met, plus a trigger on `goal_reached` for that goal that nests `item_chiefs_staff` to the actor. Satisfy it, run a turn.
   - expected: the goal is `reached`; the staff node exists with a containment edge to the actor; a second character can take it.
   - observed: TODO
2. Remove the trigger and repeat.
   - expected: the goal still completes; nothing is granted. The consequence is the world's, not the goal's.
   - observed: TODO

## Acceptance

- [ ] A reached goal dispatches a `goal_reached` event an ordinary trigger can fire on.
- [ ] The consequence (a granted item) is a real world node - stealable / covetable / tradeable by existing mechanics - not a field on the goal.
- [ ] No `grants` / reward data on the goal; the goal carries only prose `hoped_for`.
- [ ] Removing the trigger removes the consequence while the goal still completes.
- [ ] No second effect system: consequences use the existing trigger effects, and no new economy code is added.

## Files

- `engine/goals.py` (dispatch the event on the reached flip)
- `engine/background_simulation.py` / the tick event path
- (content) a trigger on `goal_reached` in the exercising scenario
- `tests/test_goals.py` or a trigger-wiring test
