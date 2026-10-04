---
type: task
status: todo
area: gameplay
priority: high
related: [task-409, task-426, task-90]
blocked_by: [task-700, task-701]
---

# task-702: Plan executor runtime: the engine runs typed plans for any character, with invalidation and needs-override

**Filed:** 2026-10-04
**Related:** task-409,task-426,task-90

## Goal

An executor that runs typed plan steps for ANY actor (LLM agent between turns, simple NPC, background character), built on engine/schedule.py (task-409 slice 1) and the activity registries. Constitutional rules: plans are disposable (invalidation means re-compose, never an authored on_fail chain beyond one shallow re-entry); every step and timer re-verifies its preconditions when it fires; survival needs outrank any plan (task-409's measured lesson); durations in game minutes with one sub-tick completion semantic shared with the delayed event queue. The executor must make plan state inspectable (a character can answer 'what are you doing and why').

## Acceptance
- [ ] The executor runs typed plans for all three actor kinds (LLM agent,
      simple NPC, background character) with no actor-specific forks in the
      step dispatcher.
- [ ] Invalidation: when a step's preconditions no longer resolve (checked on
      arrival and on timer fire), the plan is discarded and the actor returns
      to selection - there is no authored per-step fail script anywhere.
- [ ] Needs-override is constitutional: vitals preempt any plan (the task-409
      measured integration), and a plan cannot opt out.
- [ ] Timers share ONE completion semantic with the delayed event queue
      (task-90), including the sub-tick rule; no second timing system.
- [ ] Plan state is inspectable: a character can answer "what are you doing
      and why" (surface in the inspector and available to the LLM prompt).
- [ ] Integration with task-409's schedule.py: an HH:MM schedule step is a
      clock-triggered plan binding; the midnight-wrap and malformed-drop
      semantics survive unchanged.
- [ ] Soak/micro-scenario proof: the fisherman loop (fish until 10 or dusk ->
      return -> cook -> sleep) runs for a full game day without an LLM call
      and reads correctly in the event stream.
