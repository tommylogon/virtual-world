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

## Update (2026-09-24) — the action-budget arithmetic is superseded

The "96 actions/day" figure above comes from the retired *action credit* model
(`DECISION_MINUTES = 10`, one decision per 10 game minutes). That model is gone:
`engine/background_simulation.py` now gives every character **one action per
turn**, where a turn is a *timeframe* (default `time_per_tick_minutes = 1`, so
~1440 turn-minutes per in-game day) and each action consumes its authored
`TASK_MINUTES` duration. A task longer than the timeframe spans turns (the
overdraft fix in `_begin_task`), and the count of actions per turn is emergent,
not budgeted — `MAX_ACTIONS_PER_TICK` no longer exists. A background character and
the live character now spend the same turn the same way.

So options (a)/(b)/(c) collapse. (a) "more actions per day" is already true and is
not a knob to turn; the fix is **(b), and it is decided: background characters use
bundled tasks, authored the same way as crafting recipes.** A chore task (walk to
a service area, service several needs, return) is one action rather than five
separate journeys. `engine/crafting.py` is the model — recipe nodes whose
properties declare inputs/conditions/outputs (task-2) — and the same declarative
shape gives a chore bundle an authored duration, target area and effect list.

The measured collapse in the tables above was real **under the old clock** and is
kept as evidence; it must be re-measured under the one-action-per-turn model before
any decision to ship schedule data. Slice 2 (the capped daily reflection) is
unaffected and still open.

## Update (2026-09-29) — Social collapse re-measured; three unrelated backsim bugs fixed

Ran a fresh headless background soak of `kraktooth_goblin_camp` (23 characters,
135 areas) after fixing several backsim defects (see below). With schedules still
unshipped, the Social collapse predicted here reproduces exactly:

| horizon | alive | Social avg/min/max | Sanity avg/min |
|---|---|---|---|
| 3 days | 23/23 | 20.2 / 0 / 45 | 74.9 / 33 |
| 7 days | 23/23 | **4.7 / 0 / 15** | **48.0 / 7** |

Social decays to near-zero over a week even though the survival ladder is healthy
(Hunger max 49, Thirst max 42, Energy min 38). Instrumented pairing tally for one
day: **581 area-frames had ≥2 available background characters, but only 24 were
pairable** — 1441 rejections were the 90-minute cooldown and 714 were areas left
with <2 after the cooldown/cap filter. So the binder is **co-location + cooldown,
not the 6/day cap**, and company only offsets the baseline drain (never fills), so
Social can only fall. This is the same arithmetic the 2026-09-24 note describes;
bundled chore tasks (option b) remain the decided fix, and schedules stay unshipped.

Fixes landed this pass (all committed, all separate from the Social question):

- **Area-node resolution (tick_manager).** `current_area` is a display name, but
  `tick_manager` resolved it by id only, so `"Chief's Pit"` → `area_chief's_pit`
  (no such node) and generated coordinate areas resolved to `None`. For 5 of 23
  characters this skipped the *entire* per-area block — environment effects AND the
  company Social gain. Added `_resolve_area_node` (id, then name via
  `room_perception`). `tests/test_tick_area_resolution.py`.
- **Sleep vs noise.** A loud room applied a raw `-1` Energy/tick (a legacy per-tick
  value) against a `+0.30/min` sleep regen, and the noise *wake* ran before the
  regen block, so a sleeper woken every tick lost that tick's regen and drained to
  0 (the `Training Pit` / `dripping water` exhaustion deaths). Scaled the penalty
  to per-minute `ENV_LOUD_ENERGY` and captured `was_sleeping` at tick start.
  `tests/test_backsim_sleep.py`. 3-day soak: deaths 5 → **0**.
- **Fauna.** Animals (bear/boar/wolf/frog/worg/raven) ran the human social
  economy: they drained Social to 0, took `social_breakdown`, and were paired by
  the social pass. `engine/vitals.is_animal` now excludes them from
  Social/Sanity/Entertainment decay, the company gain/drain, the sanity-breakdown
  conditions, and the social pair/approach passes. `tests/test_fauna_needs.py`.
- **Company-seeking (task-409 slice).** Added `SOCIAL_THRESHOLD` +
  `_seek_company`: a lonely background character walks toward where others are.
  Social avg 0.7 → 20.2 over 3 days; it does not solve the week-long equilibrium
  above, but it is the coarse-social half of slice 1 and is orthogonal to chores.

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

## Dependency reality (2026-09-24)

- **`Depends on: task-399` is satisfied** (background runner + promotion seam,
  `engine/background_simulation.py`, `engine/promotion.py`); `task-408` is only
  partly done (consolidation + folder compiler landed; dedupe/`high_metabolism`
  open).
- **Most of this task already shipped**: the schedule model/planner
  (`engine/schedule.py`), schedule pursuit
  (`engine/background_simulation.py:838-868 _pursue_schedule`) and the coarse
  social pass (`engine/background_social.py:717 run_social_pass`) are live.
  Section 4 ("coarse meetings") was amended and completed by task-417/task-423.
- **Only the capped daily reflection LLM call (≤1/char/day) is genuinely
  missing** — no reflection code exists in `engine/`.
- The plan's action-budget arithmetic is superseded by the timeframe-and-flow
  model (`docs/virtualWorld/Simulation Model.md`); options now collapse to
  "background characters use bundled tasks authored like crafting recipes".
