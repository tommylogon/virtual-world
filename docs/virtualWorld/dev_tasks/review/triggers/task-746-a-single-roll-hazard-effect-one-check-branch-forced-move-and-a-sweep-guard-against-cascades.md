---
type: task
status: todo
area: triggers
priority: medium
wiki: "[[Triggers/Trigger System Overview]]"
---

# task-746: A single-roll hazard effect: one check, branch, forced move, and a sweep guard against cascades

**Filed:** 2026-10-09
**Related:** task-716 task-475 task-72

## What

The river/bridge/cliff vision needs one primitive the trigger system cannot compose today. skill_check is a CONDITION (engine/triggers/condition_tree.py:427), so a success trigger and a fail trigger roll twice; and push_actor calls movement.move_to_area directly, which fires on_enter again, so fail -> push -> on_enter -> fail cascades forever. Add one effect (e.g. hazard / current_push) that: rolls the check ONCE, runs a fail branch or a success branch, moves the actor via push_actor along a direction/way, sets a per-character sweep guard with an expiry tick so it cannot re-fire within the sweep, and records traversal.note_refusal (AVOID_MINUTES) so the soak path routes around it. Register in EFFECT_TYPES (engine/triggers/constants.py). Note flag_equals reads char.flags but the writer (set_flag, engine/triggers/behaviors.py:275) is NPC-behaviour-only and not an item/way effect, so the guard belongs inside the effect. Tests: a failed Athletics on a river pushes exactly one cell and does NOT re-trigger; a success narrates and stands.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: trigger/behavior authoring surface → define one hazard check with success/fail outcomes and a forced movement → place the character on that way/area in the game view → inspect the event stream and resulting location.

Current availability: the card identifies that `skill_check` is a condition that can roll twice and that `push_actor` can re-enter `on_enter`, causing a cascade. The one-roll hazard effect and sweep guard are planned; no new hazard authoring control is claimed.

Live steps when available:
1. Author a hazard that checks once and pushes the actor on failure. Trigger it with a character whose check result is controlled by the fixture.
   - expected: the event records exactly one roll, then the selected success or failure branch; the failure branch moves the actor along the chosen way.
2. Inspect the event stream and character location after the forced movement re-enters the destination's `on_enter` trigger.
   - expected: the sweep guard prevents a second roll within the same sweep and prevents a push cascade; the actor's final position matches the one forced move.
3. Repeat with a successful check.
   - expected: the success branch runs once and no forced move occurs.
4. Repeat the failure after the guard's expiry tick.
   - expected: a later independent entry may roll again; the guard is per-character and expires as authored rather than permanently suppressing hazards.
5. Inspect refusal/traversal notes for a blocked forced route.
   - expected: `traversal.note_refusal` records the actual refusal and the character is not teleported through an invalid way.

This section is not a claim that the planned hazard effect exists or works today.
