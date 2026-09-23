---
type: task
status: todo
area: gameplay
priority: medium
---

# task-426: Plan archetypes and group goals (hunt, raid, gather, haul)

**Filed:** 2026-09-21  
**Depends on:** task-409 (deterministic planner + schedule model), task-403
(knowledge base — a plan can only use facts the character knows), task-417
(co-presence).  
**Relates:** task-425 (novelty), task-410 (sources to gather from).

## Gap

task-409 specifies a **per-step** goal-directed planner: given schedule + goals +
needs + traits + relationships, pick the next step (work/wait/travel/consume/
social) and execute it. That covers a *timetable* and a *reactive chooser*.

It does **not** cover either of the two things that make the world feel alive:

1. **Multi-step plans** — "go to the area with X → take X → go to the target area
   → drop X". Three or four steps to reach a state, not one.
2. **Group goals** — a leader's goal *assigned* to members with a shared rally
   point and time. A raid, a hunting party, a work gang.

## Design: authored templates, algorithmic selection

The plan is **data**, not reasoning: a small library of templates, each a short
ordered step list with preconditions. Selection is the algorithmic part — who can
do it, when, with whom, where — scored from needs, traits, relationships, role,
and *known* facts.

| archetype | shape |
|---|---|
| `haul` | here → take target item → travel to sink → drop |
| `gather` | travel to a source (task-410) → take/forage → return |
| `hunt` | travel to known game → hunt (skill check) → take carcass → return |
| `raid` | recon → gather participants → march → strike → carry loot → disperse |
| `build`, `cook` | fetch inputs → combine at a station |

Author the first two well (`haul` = Mikka's scrap run, `gather` = the
foragers) rather than sketching all six.

**Group goals** are a record, not a plan: `{leader, goal, participants[],
rally_area, rally_time}`. The leader's plan assigns members a goal ("be at the
rally area by T"); each member plans *locally* to satisfy it. Emergence comes
from goal propagation plus shared knowledge, not from the planner being clever —
most of the interesting behaviour falls out of one participant starving mid-march
and peeling off.

## Constraints

- **Plans are stored and executed, not recomputed per tick.** Plan once (or on
  invalidation), advance a step each action. Replan on completion, a broken
  precondition, or a critical need. This is what keeps it affordable at scale.
- **Determinism**: seeded selection, reproducible replay.
- **Bounded**: max steps per plan, max participants, and a hard fallback to the
  task-409 per-step planner if a plan cannot be built or completed.
- **Knowledge-gated**: a plan may only use facts the character knows (task-403) —
  you cannot raid a place you have never seen, or fetch from an area you do not
  know holds the thing.
- **Own the set-pieces.** A raid is a story beat and must be reliable; do not let
  it be fully emergent. Search/templates for the small stuff, authored shape for
  the big stuff.

## Acceptance

- Mikka's scrap run works end to end as a `haul`: plan → travel → take → travel →
  drop, visible in the trace with the plan's identity.
- A plan survives a *repeated* need interruption (eat, then resume) rather than
  being lost.
- A plan is abandoned cleanly when its precondition breaks (the item is gone),
  with a replan, not a freeze.
- A group goal produces several characters converging on a rally area, and the
  party degrades visibly when one participant drops out.
- Same seed → same plans and same sequence.

## Non-goals

- Full GOAP search over the whole action set. Templates first; search only if a
  goal genuinely cannot be expressed as a template.
- LLM-authored plans in the tick loop.
- Negotiation, politics, or multi-faction strategy.
