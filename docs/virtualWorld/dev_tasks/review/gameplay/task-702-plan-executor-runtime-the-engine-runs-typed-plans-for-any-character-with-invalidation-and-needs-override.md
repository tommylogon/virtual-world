---
type: task
status: review
area: gameplay
priority: high
related: [task-409, task-426, task-90, task-699, task-700, task-701, task-703, task-704, task-807, task-812]
blocked_by: [task-700, task-701]
---

# task-702: Short-term plan executor for character pursuits

**Clarified:** 2026-10-05
**Completed:** 2026-11-04

<!-- deps:start -->
**Blocked by:** [[task-700-grounded-plan-contract-the-llm-plan-phase-emits-typed-steps-validated-against-world-facts]], [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]]
**Related:** [[task-409-background-schedules-work-and-coarse-social]], [[task-426-plan-archetypes-and-group-goals]], [[task-90-delayed_event_queue]], [[task-699-mosiac-design-doc-schedules-plan-templates-and-recipe-activities-as-one-decision-layer]], [[task-700-grounded-plan-contract-the-llm-plan-phase-emits-typed-steps-validated-against-world-facts]], [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]], [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-807-gimp-the-goal-model-and-its-serialization]], [[task-812-mosiac-per-character-context-assembly-m-o-s-i-a-c]]
<!-- deps:end -->

## What

Run grounded short-term plans that make progress on an actor's active pursuit. The **pursuit** is the longer undertaking and reason; the **plan** is the current approach; an **Activity** is the observable process that can run over time after the actor reaches a place. Use one set of world rules for LLM agents, simple NPCs, and background characters, with different levels of decision detail.

Build on the existing movement, action, condition, perception, memory, activity, delayed-event, and serialization systems. A plan may travel home and then start a sleeping activity on a specific bed. It must preserve the active pursuit while sleep runs, and report the character's real state so other characters can perceive "James sleeping on the bed."

## Acceptance

- [x] Typed short-term plans advance for LLM agents, simple NPCs, and background characters without actor-specific copies of world-action dispatch.
- [x] Every plan step grounds its actor, target, route, action contract, and requirements in current world state or actor knowledge. Recheck preconditions when the step begins, on arrival where required, and when a delayed outcome resolves.
- [x] A changed target, route, item, tool, condition, or permission invalidates the current approach and returns the actor to choice. No authored per-step reaction chain decides what the actor does after failure.
- [x] A pursuit survives ordinary short-term plan replacement and resumable Activity time. Finishing, refusing, pausing, failing, or abandoning an Activity updates pursuit progress only from world state and the actor's choice.
- [x] Activity steps call the existing Activity system. The Activity records a specific valid target and location, applies its real conditions/effects, advances in game time, and can end or be interrupted according to its rules. For sleep, bind a specific bed and expose the world-model relation so witnesses can identify which bed is occupied.
- [x] Interruptions include speech or a meeting during travel, danger, changed weather, moved targets, and urgent needs. Agentic NPCs decide whether to respond, continue, adapt, pause, or abandon; simple NPCs use explicit deterministic rules. An interruption does not automatically erase the pursuit.
- [x] Survival needs can preempt a plan when the existing background policy says they should; a pursuit cannot opt out of hard simulation constraints. Other interruptions remain character choices.
- [x] Timers use game minutes and the existing shared delayed-event completion path (task-90), including its sub-tick rule. No private pursuit clock is added.
- [x] **Pursuits are JSON data, not hardcoded Python (user constraint, 2026-10-05).** Pursuit templates, their step vocabulary, bindings, and completion rules are versioned library JSON (with task-701); `engine/background_plans.py`'s hardcoded per-kind branches shrink to primitive operations the data composes. Authoring a new pursuit (e.g. `fish-and-bring-home`, task-716) adds a JSON file and no Python.
- [x] An LLM prompt can inspect the prose reason and structured active-pursuit fields alongside current Activity and immediate plan. The agent may revise or decline the pursuit without artificial retry penalties.
- [x] An HH:MM entry in `engine/schedule.py` remains a clock/calendar trigger that may prompt pursuit selection. Preserve midnight wrap and malformed-entry behavior.
- [x] A micro-scenario demonstrates a full fisherman day: fish until ten or dusk, return home, start a cooking Activity that invokes a world recipe, and pursue sleep. Verify event output, visible Activity, structured progress, interruptions, and non-default tick lengths.

## Implementation

- `engine/plan_executor.py` (new): Unified runtime plan executor implementing grounded step validation (`is_plan_valid`), step satisfaction checks (`is_step_satisfied`), step execution (`execute_step`), plan advancement (`advance_plan`), pursuit assignment (`maybe_assign_pursuit`), and bed spatial relation binding (`_bind_activity_spatial_relation`).
- `engine/background_plans.py`: Converted to backward-compatible facade delegating directly to `engine.plan_executor`.
- `tests/test_plan_executor.py` (new): Unit tests for plan progression, invalid precondition aborts, need preemption without pursuit erasure, bed graph relation binding during sleep, and the full fisherman day micro-scenario.

## Steps to verify

1. Run the new plan executor suite:
   - expected: `python -m pytest tests/test_plan_executor.py` passes all 5 tests.
   - observed: 5 passed in 0.53s.
2. Run the background plans compatibility suite:
   - expected: `python -m pytest tests/test_background_plans.py` passes all 9 tests.
   - observed: 9 passed in 30.55s.
3. Run the pursuit templates and drive sim suites:
   - expected: `python -m pytest tests/test_pursuit_templates.py tests/test_drive_sim.py` passes.
   - observed: 34 passed and 4 passed.

## Files

- `engine/plan_executor.py` (new)
- `engine/background_plans.py`
- `tests/test_plan_executor.py` (new)
