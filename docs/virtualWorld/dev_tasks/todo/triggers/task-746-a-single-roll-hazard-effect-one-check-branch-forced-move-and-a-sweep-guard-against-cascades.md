---
type: task
status: todo
area: triggers
priority: medium
---

# task-746: A single-roll hazard effect: one check, branch, forced move, and a sweep guard against cascades

**Filed:** 2026-10-09
**Related:** task-716 task-475 task-72

## Goal

The river/bridge/cliff vision needs one primitive the trigger system cannot compose today. skill_check is a CONDITION (engine/triggers/condition_tree.py:427), so a success trigger and a fail trigger roll twice; and push_actor calls movement.move_to_area directly, which fires on_enter again, so fail -> push -> on_enter -> fail cascades forever. Add one effect (e.g. hazard / current_push) that: rolls the check ONCE, runs a fail branch or a success branch, moves the actor via push_actor along a direction/way, sets a per-character sweep guard with an expiry tick so it cannot re-fire within the sweep, and records traversal.note_refusal (AVOID_MINUTES) so the soak path routes around it. Register in EFFECT_TYPES (engine/triggers/constants.py). Note flag_equals reads char.flags but the writer (set_flag, engine/triggers/behaviors.py:275) is NPC-behaviour-only and not an item/way effect, so the guard belongs inside the effect. Tests: a failed Athletics on a river pushes exactly one cell and does NOT re-trigger; a success narrates and stands.

## Acceptance

- TODO
