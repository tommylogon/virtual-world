---
type: task
status: todo
area: characters
priority: high
related: [task-403, task-417, task-423, task-699, task-702, task-704, task-814]
wiki: "[[Characters/Background Simulation]]"
blocked_by: [task-701]
---

# task-409: Background schedules, daily reflection, and coarse social behaviour

**Filed:** 2026-09-19  
**Prerequisites:** task-399 and task-408 are complete.
**Design:** [[Character Pursuits]], [[MOSIAC]], and [[GIMP]].

<!-- deps:start -->
**Blocked by:** [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]]
**Related:** [[task-403-unified-agent-memory-and-knowledge]], [[task-417-co-presence-gate-for-coarse-meetings]], [[task-423-background-social-interactions]], [[task-699-mosiac-design-doc-schedules-plan-templates-and-recipe-activities-as-one-decision-layer]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-814-mosiac-schedules-a-character-can-edit-themselves]]
<!-- deps:end -->

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
bundled tasks authored as data.** A chore task (walk to a service area, service
several needs, return) is one activity rather than five separate journeys. The
data-authored style can resemble crafting recipe nodes, but the game meanings
stay separate: a chore describes an actor's intended activity, while a crafting
recipe defines how inputs become outputs. A chore bundle can have its own
duration, target area and steps without becoming a transformation recipe.

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

## Current scope (2026-10-15)

The old deterministic “goal-directed planner” in this card is superseded by the
MOSIAC/GIMP design and tasks 702/704. Keep the work here on the existing
calendar schedule and the still-missing capped background reflection. Do not
build another planner or selector.

## What

Finish the background schedule slice by remeasuring its authored scenario data
under the current timeframe-and-flow simulation, then decide whether that data
can ship. Complete the optional daily reflection only through existing Player
goals and memories.

The clock schedule model, schedule traversal, and coarse social pass already
exist. The co-presence meeting and coarse social work is covered by tasks 417
and 423; it is not open work in this card.

## Ownership and runtime boundaries

- The clock schedule is Player.schedule and engine/schedule.py. Schedule entries
  can make an activity or pursuit timely; they are not pursuits or activities.
- The hand-ordered background needs cascade in
  engine/background_simulation.py::_satisfy_needs remains the needs policy.
  Never replace it with a scored candidate list or the MOSIAC selector.
- Task 704 owns selecting/binding a suitable plan; task 702 owns executing that
  plan. This task must not add a parallel goal planner, action executor, clock,
  or character-private store.
- GIMP goals, motivations, and intentions are private Player data. MOSIAC
  assembles runtime context from those goals, obligations, schedules, attention,
  and available choices; the disposition chooses among them.
- A reflection may update an existing GIMP goal through the existing goal
  mutation path and may write an ordinary memory through Player.memories /
  AgentMind. It must not directly choose or execute an action. Do not add a
  reflection log or memory database as another source of truth.

## How

1. Re-run the schedule-on/off comparison using the current tick/timeframe model,
   current scenario data, a fixed starting state, and the same measured game
   duration. Record the exact scenario, seed, timeframe, and vital/activity
   results. The 2026-09 measurements below were made under the retired
   action-credit model and are historical only.
2. If the schedule data is acceptable under current behavior, author it through
   the existing scenario/character data path. If not, keep it unshipped and
   update this card with the measured blocker and the smallest supported next
   change. Do not invent a fix from the retired 96-actions-per-day arithmetic.
3. Implement the daily reflection as an optional local-provider call capped at
   one per background character per in-game day. Its bounded input may include
   the character's existing GIMP goals, relationships, and recent trace. Its
   output must be validated and applied through existing goal and memory APIs.
   With no local model, the simulation continues unchanged.
4. Keep normal needs, movement, activities, schedule timing, and plan execution
   on their existing paths. Record which runtime caller reaches each new branch.

## Acceptance

- Current-model schedule-on/off evidence is recorded; any schedule data that
  ships improves or preserves the chosen vital and activity measures, and the
  decision is explained. Old measurements are not treated as current evidence.
- A fixed seed with reflection disabled reproduces the same schedule/plan
  behavior.
- The reflection call is capped at one per character per in-game day, uses only
  the configured local provider, and leaves the simulation unchanged when no
  local model is configured.
- Reflection changes only existing Player GIMP goals and/or ordinary
  Player.memories through their existing mutation paths. It never selects an
  immediate action, writes a duplicate mind, or bypasses normal action
  validation.
- Schedule and any supported reflection changes survive save/load in the
  existing Player record.
- The completed coarse-social behavior from tasks 417 and 423 is preserved.

## Browser UI and intended live verification

Intended UI home: Character Inspector → 🧠 Mind → **Schedule — their day**,
Goals section, and Memories tab.

Current availability: schedule, goal, and memory readouts exist in Mind;
schedule rollout and daily reflection still need the current acceptance work
described here.

Live steps when available:

The schedule belongs in the character Inspector's existing **🧠 Mind** panel,
under **Schedule — their day**. Goals and motivations remain in the existing
Goals section; any authored memory remains in the existing **Memories** tab.
Do not add a second schedule or mind screen. If a code change adds or changes
schedule/reflection state, it must be visible in these existing character
surfaces; API or test output alone does not satisfy UI acceptance.

1. Open a scratch scenario with a background character whose schedule is
   authored, then select that character in the graph and open **🧠 Mind**.
   - expected: the character's actual schedule entries appear under
     **Schedule — their day**, with the authored time, activity, and area.
2. Advance the game clock through one scheduled transition using the normal
   game controls. Reopen/refresh the character's Mind panel and inspect the
   character in the graph/room.
   - expected: the visible schedule remains the authored routine and the
     character's observed location/activity agrees with the schedule and
     current simulation rules.
3. When reflection is enabled in a local test setup, inspect the same character's
   Goals section and Memories tab after the reflection day.
   - expected: any accepted change appears in the existing GIMP goal or normal
     memory UI; no second panel or hidden state store is required to find it.
4. Compare the panel with the same character's values in /api/state.
   - expected: the panel displays the Player-owned values, not a graph-node copy.

These are intended access and live acceptance steps, not a claim that planned
behavior works today. No new browser run is recorded for this updated card.

## Steps to verify

1. Run targeted mechanism coverage in tests/test_schedule.py and
   tests/test_background_simulation.py for schedule clock lookup and branch,
   reflection call cap/provider, validation path, deterministic no-model
   behavior, and Player save/load.
   - expected: the asserted value read and branch taken match the current
     schedule/reflection contract.
   - observed: not run for the updated scope.
2. Produce the current-model schedule-on/off soak report.
   - expected: report names the scenario, seed, timeframe, game duration, and
     vital/activity results.
   - observed: not run; old measurements used the retired model.
3. Follow the browser path in Browser UI and intended live verification when
   the relevant behavior is available.
   - expected: existing Mind sections show the character's Player-owned
     schedule, GIMP goals, and any reflection memory.
   - observed: not run for this updated scope.

## Completed prerequisites and related work

- task 399 (background runner) and task 408 (scenario data integrity) are done.
- The schedule model and traversal already exist in engine/schedule.py and
  engine/background_simulation.py.
- Coarse meetings are scoped to co-present characters by task 417; broader
  background social behavior is recorded in task 423.
- Current plan selection/execution work belongs to tasks 704/702.

## Historical measurement

The original 2026-09 schedule comparison and failed co-location/committed-journey
experiments remain above as historical evidence. They used the retired
action-credit model. Re-measure before relying on those numbers or changing
scenario data.

## Files

- Existing background schedule and reflection implementation, if changes are
  needed
- Scenario/character schedule content only after current-model measurement
- tests/test_schedule.py and tests/test_background_simulation.py
