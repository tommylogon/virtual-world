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

## Progress (slice 1)

**The schedule model and the planner are implemented and tested; the schedule
DATA is deliberately not shipped, because measurement showed it degrades the camp.**

Engine landed (`engine/schedule.py`, `tests/test_schedule.py` — 39 tests):

- Steps are `{start: "HH:MM", activity, area, fallback}`, sorted, wrapping at
  midnight; before the first step the *last* step stays in force, so a day
  starting at 06:00 does not leave anyone idle or wandering from midnight.
- Malformed steps are **dropped, not guessed** — a step with no usable start
  cannot be placed in a day, and inventing one would make a character behave in a
  way nobody authored. An unknown activity degrades to `wait` rather than freeing
  the character to wander. An empty schedule is a valid state: exactly how every
  character behaved before this task.
- `minutes_of_day` reads the engine's own clock (`total_game_minutes`), so a step
  at 07:00 happens at 07:00 at any tick length.
- `normalize` also runs on load, so a hand-edited or legacy file cannot put a bad
  step into somebody's day.
- `background_simulation._pursue_schedule` walks to the step's area — reusing
  `_target_step`, which gains an explicit `areas` override for a *named*
  destination — then starts a short `working` block. It runs **after every
  survival need and before boredom**, so a character works with time no need
  claims and still breaks off to eat. `working` is registered in all five activity
  registries including `ACTIVITY_INTERRUPTIBLE` (the omission that once made
  `conversing` never expire), and the block is deliberately short
  (`WORK_MINUTES = 30`) because `_act` skips anyone mid-activity — the duration is
  the longest a character can go without eating or relieving itself.
- `tools/add_schedules.py` authors schedules idempotently (dry-run default) from a
  per-role table: 16 of 23 characters have a role, derived from the area each
  already starts in. The 6 animals and the player character get none on purpose.

**Why the data is not shipped.** Authored and measured over 3 days at 15 min/tick,
schedules on vs off, same seed:

| vital | avg on | avg off | min on | min off |
|---|---|---|---|---|
| Hygiene | 48.8 | **69.2** | 0.0 | 45.0 |
| Social | 40.3 | **61.6** | 0.0 | 4.0 |
| Entertainment | 19.8 | **42.2** | 0.0 | 8.0 |
| Energy | **72.3** | 55.4 | 40.0 | 31.0 |
| Hunger / Thirst / Sanity | same | same | same | same |

Schedules genuinely work — traces show Thrazz at the Chief's Den working at 09:30,
Mikka at the Workshop, and `schedule:work` firing — and Energy is *better* with
them, because the night step puts characters in the Sleeping Halls so they sleep
properly. But Hygiene, Social and Entertainment collapse: **388 schedule-travels
against 53 work blocks.** Schedule travel competes for the same action budget as
the need ladder and drags characters to work sites that hold **no facilities**, so
the lower-priority needs never get their turn. Priority starvation via travel, not
a broken schedule — and not a regression worth shipping.

**Next, in the order the evidence suggests:**

1. **Co-locate facilities with work.** The work sites (Workshop, Scouting Rooms,
   Training Pit, Chief's Den, Scrap Pile, Cooking Area) have no food, water,
   latrine, wash spot or recreational fixture, so every need is a cross-camp round
   trip. `tools/add_renewable_sources.py` already places fixtures by tag, so this
   is a data pass with an existing tool and the most likely fix.
2. **Only yield to a pressing need.** The ladder interrupts for any need past its
   threshold, so a working character abandons the job for a top-up; a work block
   should ignore non-critical needs and finish.
3. Re-measure, then author the data into the scenario (one idempotent command).

Slice 2 (the capped daily reflection) is unaffected and still open.

**Second round — both attempted fixes failed, and the reason is arithmetic.**

1. **Committing the errand.** Hypothesis: journeys are walked one hop per decision
   and every routine need crossing restarts them, so characters never arrive. Added
   `CRITICAL_*` levels and a committed-journey guard (a scheduled errand runs to
   arrival unless a need is critical). **Result: 388 → 381 travels, 53 → 45 work
   blocks.** No effect — the hypothesis was wrong, and the change was reverted
   rather than kept as unproven complexity.

2. **Co-locating facilities with work.** Hypothesis: work sites have no food,
   water, latrine or wash, so every need is a cross-camp round trip. Added
   `latrine`/`water`/`recreation` area tags to 11 work areas and 4 wash basins
   (`tools/add_workplace_facilities.py`). **This made things worse, including the
   no-schedule baseline** — Hygiene 69.2 → **24.4** with schedules *disabled*, and
   48.8 → **7.9** with them on, and two characters died of exhaustion. Reverted.

   The lesson is worth more than the change: **area tags are not neutral.** They
   are what `_areas_with` consults for *every* need search, so tagging the work
   areas `water` and `latrine` changed where the entire camp travels for every
   need — not just where workers drink. A "co-locate the facilities" pass cannot
   be evaluated as a local data tweak.

**The actual blocker is the action budget.** A background character takes one
action per `DECISION_MINUTES` (10 game minutes), so a day is about **96 actions**
per character. Survival need service is not cheap in actions: each is a *journey*
of one hop per action, and the camp's food, water, latrine and wash are in
different corners. A working day of twelve 30-minute blocks cannot fit beside
those errands — and once schedule travel competes for the same budget, the
errands slow down too, which is exactly what the numbers show (Hygiene and
Entertainment collapse; `schedule:work` fires about once per character per day).

So this is a **design decision, not a data tweak**:

- **(a) More actions per day** — shorten `DECISION_MINUTES` or raise
  `MAX_ACTIONS_PER_TICK`. Straightforward, but multiplies tick CPU across 23+
  characters, and it treats the symptom: it makes the character *finer*-grained
  when the goal is "supercharged simple NPCs".
- **(b) Coarser need service** — bundle the errands. At 10-minute granularity a
  character should not walk to the river, drink, walk back, then walk to the
  latrine as three separate decisions; it makes **one "chores" trip** to a service
  area and services several needs in a single action. This is what a coarse
  simulation should already be doing, and it collapses roughly five errands into
  one, freeing the budget for work. The camp's existing latrine/wash/food/water
  areas already identify where a chores trip would go.
- **(c) Drop the working day** — keep schedules only for *placement* (where a
  character is by day and night, which is already an improvement and measured as
  Energy-positive) and accept no work blocks.

(b) is the recommended one: it fits 409's own "supercharged simple NPCs" framing,
it is the change that makes the budget arithmetic work, and it does not trade CPU
for the problem. It is also a change to the *survival model's granularity*, so it
should be decided rather than assumed. Until then the schedule data stays out of
the scenario and the engine remains as committed in slice 1.

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
   **Amended by task-417:** the pairing pass runs **per area over co-present
   characters**. As written here the rule has no spatial constraint and would
   pair characters in different areas. task-417 is authoritative for this step.
   Deltas are written through `apply_relationship_delta` (task-420).
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
