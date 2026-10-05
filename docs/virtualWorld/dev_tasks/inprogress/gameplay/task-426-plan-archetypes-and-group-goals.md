---
type: task
status: inprogress
related: [task-704, task-701]
area: gameplay
priority: medium
---

# task-426: Pursuit templates and group goals (hunt, raid, gather, haul)

**Filed:** 2026-09-21  
**Depends on:** task-409 (deterministic planner + schedule model), task-403
(knowledge base — a plan can only use facts the character knows), task-417
(co-presence).  
**Relates:** task-425 (novelty), task-410 (sources to gather from).

## Progress (2026-09-30) — the carry/refill substrate landed

The precondition an expedition plan needs now exists in
`engine/background_simulation.py`:

- `_fill_waterskin` — at a water area, top up carried water containers
  (`CARRIED_WATER_FILL = 3`). Natural water is an area tag, so a filled skin is
  what lets a character drink *away* from the water.
- `_stock_food` — at a food area, pocket one movable, non-fixture food item.
- `_carry` — re-home an item from its area into the character's hands
  (`EDGE_CARRYING`); `_find_consumable` already prefers carried items, so a need
  is then answered from the pack.
- Wired as a low-priority `prepare` step in `_act` (after survival needs, before
  schedule/work). `TASK_MINUTES["take"] = 2`.
- `tests/test_background_preparation.py` (3). 3-day background soak: 23/23 alive,
  Hunger avg 28.6 → 22.7 (rations carried and eaten en route), no regression.

**Content gaps this exposed (camp provisioning is not authored):**
- `Food Storage` carries the `food` area tag but holds **no food item** — the
  camp's larder is an empty room that need-travel still sends characters to.
- There are **no water containers anywhere in the camp**, so `_fill_waterskin`
  has nothing to fill until one is authored/placed.
- Food exists only as two finite stacks in `Cooking Area` (Mushrooms, Berries,
  2 uses each); foraging (`task-410`) is the only renewable in-camp supply.

Authoring those (a stocked larder + a waterskin or two + a renewable camp source)
is a prerequisite for `gather`/`haul` templates to mean anything; tracked here
rather than as a separate task.

## Gap

task-409 specifies a **per-step** goal-directed planner: given schedule + goals +
needs + traits + relationships, pick the next step (work/wait/travel/consume/
social) and execute it. That covers a *timetable* and a *reactive chooser*.

It does **not** cover either of the two things that make the world feel alive:

1. **Multi-step plans** — "go to the area with X → take X → go to the target area
   → drop X". Three or four steps to reach a state, not one.
2. **Group goals** — a leader's goal *assigned* to members with a shared rally
   point and time. A raid, a hunting party, a work gang.

## Design: authored pursuit templates, algorithmic selection

The **pursuit template** is data, not reasoning: a small library of reusable
undertakings with requirements and possible steps. Selection is the algorithmic
part — who can take it on, when, with whom, and where — scored from needs,
traits, relationships, role, and *known* facts. The short-term plan is the
current executable approach and may be recomposed while the pursuit remains.

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

- Mikka's scrap run works end to end as a `haul` pursuit: plan → travel → take → travel →
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

## Progress (2026-10-01) — the plan mechanism, haul + gather + rally

Landed `engine/background_plans.py`: a plan is **stored on `Player.plan`** and
advanced one step per action, so it survives a need interruption (the survival
ladder runs first, the plan is untouched, the next satisfied action resumes it).
Templates are **data** — a `plan` graph node declares the template and its
parameters; selection is deterministic (plan nodes in id order) and
knowledge-gated (the source must be reachable). It currently uses the same
graph-node storage shape as a crafting `recipe`, but its meaning is an actor's
multi-step activity; the recipe's meaning is a world transformation.

| template | shape |
|---|---|
| `haul` | `travel(source) -> take(item) -> travel(sink) -> drop(item)` |
| `gather` | `travel(area-with-tags) -> take(item) -> travel(home) -> drop(item)` |
| `rally` | `travel(rally_area)` — a group goal: every `participants` member walks to one place |

- Traces: each step writes `why="plan:<label>"`; completion `plan:<label>:done`,
  a broken precondition `plan:<label>:failed` — so `soak_telemetry` groups a run
  under `plan`. A `repeat: true` node re-arms after completion/failure (the
  "replan" case); a one-shot marks itself in `completed_plans`.
- `Player.plan` and `Player.completed_plans` serialize and round-trip.
- `_act` runs the plan **below every survival need and above `prepare`**, and it
  is deliberately not added to `served`, so a coarse timeframe can take several
  steps.

**Authored content (kraktooth).** `tools/add_scrap_run.py` (idempotent) adds the
one inert prop and the plan node that make **Mikka's scrap run** real:
`Scrap Pile -> take Scrap -> Workshop -> drop`. The scrap item carries no
food/water/recreation tag, so it cannot move where any survival need travels —
the failure mode that sank the 2026-09-29 co-location pass.

**Evidence.**

- `tests/test_background_plans.py` (7): haul end to end, resume after a need,
  clean failure on an empty source, save/load, gather, rally convergence, rally
  degradation when a participant cannot reach.
- Kraktooth run: Mikka starts the plan at tick 2 (start → travel ×3 → take →
  travel → deliver → done); `item_scrap` ends `in area_workshop`.
- 3-day background soak, before vs after authoring: **23/23 alive, 0 dead**, and
  survival vitals unchanged (Hunger 28.6 / Thirst 19.5 / Energy 68.4 / HP 93.4 /
  Hygiene 71.5 / Social 22.7 / Sanity 50.2 / Entertainment 53.3). No degradation.
- Backsim suites: 183 passed.

**Still open (follow-ups, not this slice).** Authoring `gather` and `rally`
content into a scenario; an explicit same-seed replay test (determinism is by
construction here — id-sorted, no RNG in plans); and a fresh replan *within* a
plan (the task's "replan, not a freeze") beyond the `repeat` retry.

## Pursuit terminology correction (2026-10-05)

The background plan archetypes are an early slice of **pursuit execution**.
Their reusable definitions belong in the pursuit-template library (task-701);
their current steps remain short-term plans; an ongoing process such as
sleeping or cooking must use the separate Activity system. Do not call those
Activities “schedule activities.” The calendar scheduler in task-409 remains a
timing/reminder layer.

The current actor-bound assignment node is now `type: "pursuit"`, and its
`pursuit_template` property selects `haul`, `gather`, or `rally`. Actor state is
stored as `Player.active_pursuit`; executable steps remain `Player.plan`. The
serializer promotes older saved plan-template nodes into the pursuit shape
while keeping their opaque node ids. The
Kraktooth scrap example is still the authored pursuit case. This runner does
not yet start a persistent Activity or inject the pursuit into an LLM prompt;
those are task-702/task-704 work.
