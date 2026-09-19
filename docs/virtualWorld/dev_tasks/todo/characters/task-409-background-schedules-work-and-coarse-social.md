---
type: task
status: todo
area: characters
priority: high
---

# task-409: Background schedules, daily reflection, and coarse social behaviour

**Filed:** 2026-09-19  
**Depends on:** task-399 (background runner), task-408 (clean scenario data).  
**Spec:** task-399 §"Background runner (v1)"; `docs/design/reversibility-contract.md`.

## Goal

Background characters behave like **supercharged simple NPCs**: a deterministic,
action-oriented planner pursues their goals every tick, with **one local LLM
reflection call per character per in-game day** to check direction and set what
to reach toward.

## Division of labour (decided)

- **Deterministic backend (non-LLM)** does the action planning and execution:
  schedule steps, work, travel, consume, coarse meetings — goal-directed, no
  LLM, seeded and reproducible.
- **Local LLM, ≤1 call/character/in-game day** answers a reflection prompt:
  *"Am I doing what I should? What do I want to reach toward?"* and proposes
  goals/adjustments. It runs through the local LM Studio provider only, never
  decides an individual action, and its output is written as goals/plan/memory
  so the deterministic planner is what acts.

This keeps cost proportional to population × game-days, not ticks, and keeps
behaviour auditable.

## Changes

1. **Schedule model.** Authored per character
   (`{start, activity, destination_scope_or_area, fallback, vital_policy}`),
   serialized, with `fallback: wait`. The due scheduler advances schedule steps
   as well as needs.
2. **Goal-directed planner (deterministic).** Given schedule + goals + needs +
   traits + relationships, pick the next step (work/wait/travel/consume/social)
   and execute coarsely, reusing existing movement/item rules where exact
   resolution is needed.
3. **Daily reflection (local LLM, capped).** Once per in-game day per background
   character, one call to the local model over a bounded context (goals,
   relationships, recent trace). Output updates goals/plan; it never chooses the
   immediate action. Hard cap enforced and logged; failures fall back to the
   existing goal unchanged.
4. **Coarse meetings.** Deterministic from relationships + traits + vitals +
   seeded RNG; apply symmetric relationship deltas; never fabricate items.
5. **Deferral rules.** Combat, ambiguous theft/trade, a blocked/locked route, a
   trigger needing precise surroundings, or an encounter marked
   `requires_active` stop and request scope activation.

## Acceptance

- A fixed seed replays a schedule/plan span identically **with reflection
  disabled**.
- At most one reflection LLM call per character per in-game day, local provider
  only; with no local model configured the sim runs unchanged.
- Reflection writes goals/plan/memory and never a direct action.
- Meetings produce symmetric relationship deltas on both sides.
- Deferred outcomes never invent facts; they surface as activation requests.
- Save/load preserves schedules, goals, `next_due_tick`, and seeded RNG state.
- Background characters visibly move through distinct day activities over a
  multi-day soak (not just eat/drink/sleep loops).

## Non-goals

- A general economy, relationship simulation, or full offscreen combat.
- Replacing the existing foreground LLM loop.

## Verification

- Extend `tests/test_background_simulation.py`: seed determinism (reflection
  off), reflection cap, goal-planner selection, deferral, symmetric
  relationships, schedule serialization.
- A multi-day soak report showing distinct activities per character.
