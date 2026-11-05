---
type: task
status: todo
area: gameplay
priority: high
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
   - observed: Not run. This task is blocked by task-822; the event and trigger fixture are not implemented.
2. Remove the trigger and repeat.
   - expected: the goal still completes; nothing is granted. The consequence is the world's, not the goal's.
   - observed: Not run. This task is blocked by task-822; the event and trigger fixture are not implemented.

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

## Browser UI and intended live verification

Intended UI home: Select the goal owner → Inspector → Bio → 🧠 Mind to read goal status; inspect the owner's Inventory and the world graph to observe an item granted by the ordinary trigger.

Current availability: The event-on-reached behavior is planned and blocked by task-822. The intended test item `item_chiefs_staff` is not present in `data/`; a filename scan covered all 2,000 files in `data/library/items/` and found no staff/chief item. The scratch scenario must author a real item node before this browser check; do not treat that ID as already available. This card does not add reward fields to goals or a new grant UI.

Live steps when available:
1. In a scratch scenario, author a real chief's staff item node (the planned id is `item_chiefs_staff`), give one character an achievable `become_chief` goal, and add an ordinary `goal_reached` trigger filtered to that goal that nests that node to the actor.
   - expected: after the goal becomes `reached`, Mind shows that status, the staff appears as a real item in the character's Inventory, and the world state contains its normal containment relationship.
2. Remove only the trigger, reset the scratch scenario, and satisfy the same goal again.
   - expected: the goal still becomes `reached`, but no staff node or inventory item is created.
3. Have a second character attempt to take the granted staff through the ordinary item action.
   - expected: normal ownership, containment, and action rules decide the result; the goal record itself contains no `grants` or reward table.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
