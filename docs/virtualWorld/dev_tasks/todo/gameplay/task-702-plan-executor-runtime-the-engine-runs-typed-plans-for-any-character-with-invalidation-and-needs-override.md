---
type: task
status: todo
area: gameplay
priority: high
related: [task-409, task-426, task-90, task-699, task-700, task-701, task-703, task-704]
blocked_by: [task-700, task-701]
---

# task-702: Short-term plan executor for character pursuits

**Clarified:** 2026-10-05

## Goal

Run grounded short-term plans that make progress on an actor's active pursuit. The **pursuit** is the longer undertaking and reason; the **plan** is the current approach; an **Activity** is the observable process that can run over time after the actor reaches a place. Use one set of world rules for LLM agents, simple NPCs, and background characters, with different levels of decision detail.

Build on the existing movement, action, condition, perception, memory, activity, delayed-event, and serialization systems. A plan may travel home and then start a sleeping activity on a specific bed. It must preserve the active pursuit while sleep runs, and report the character's real state so other characters can perceive “James sleeping on the bed.”

## Acceptance

- [ ] Typed short-term plans advance for LLM agents, simple NPCs, and background characters without actor-specific copies of world-action dispatch.
- [ ] Every plan step grounds its actor, target, route, action contract, and requirements in current world state or actor knowledge. Recheck preconditions when the step begins, on arrival where required, and when a delayed outcome resolves.
- [ ] A changed target, route, item, tool, condition, or permission invalidates the current approach and returns the actor to choice. No authored per-step reaction chain decides what the actor does after failure.
- [ ] A pursuit survives ordinary short-term plan replacement and resumable Activity time. Finishing, refusing, pausing, failing, or abandoning an Activity updates pursuit progress only from world state and the actor's choice.
- [ ] Activity steps call the existing Activity system. The Activity records a specific valid target and location, applies its real conditions/effects, advances in game time, and can end or be interrupted according to its rules. For sleep, bind a specific bed and expose the world-model relation so witnesses can identify which bed is occupied.
- [ ] Interruptions include speech or a meeting during travel, danger, changed weather, moved targets, and urgent needs. Agentic NPCs decide whether to respond, continue, adapt, pause, or abandon; simple NPCs use explicit deterministic rules. An interruption does not automatically erase the pursuit.
- [ ] Survival needs can preempt a plan when the existing background policy says they should; a pursuit cannot opt out of hard simulation constraints. Other interruptions remain character choices.
- [ ] Timers use game minutes and the existing shared delayed-event completion path (task-90), including its sub-tick rule. No private pursuit clock is added.
- [ ] An LLM prompt can inspect the prose reason and structured active-pursuit fields alongside current Activity and immediate plan. The agent may revise or decline the pursuit without artificial retry penalties.
- [ ] An HH:MM entry in `engine/schedule.py` remains a clock/calendar trigger that may prompt pursuit selection. Preserve midnight wrap and malformed-entry behavior.
- [ ] A micro-scenario demonstrates a full fisherman day: fish until ten or dusk, return home, start a cooking Activity that invokes a world recipe, and pursue sleep. Verify event output, visible Activity, structured progress, interruptions, and non-default tick lengths.

## Current slice

`engine/background_plans.py` currently advances typed haul/gather/rally plans for background characters and can resume a multi-step plan after a need action. The actor-bound pursuit survives in `Player.active_pursuit`; its immediate steps live in `Player.plan`. The runner does not yet start ongoing Activities from pursuit steps or supply the active pursuit to an LLM prompt.
