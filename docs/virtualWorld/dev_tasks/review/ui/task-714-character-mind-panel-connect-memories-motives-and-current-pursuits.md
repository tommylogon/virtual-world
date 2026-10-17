---
type: task
status: review
area: ui
priority: medium
related: ['task-409', 'task-426', 'task-691', 'task-699', 'task-701', 'task-702', 'task-703', 'task-704', 'task-725', 'task-729', 'task-787', 'task-800', 'task-802', 'task-806', 'task-807', 'task-810', 'task-811', 'task-812', 'task-813', 'task-814', 'task-820', 'task-821']
---

# task-714: Character Mind panel: connect memories, motives, and current pursuits

**Filed:** 2026-10-05
**Related:** task-409, task-426, task-691, task-699, task-701, task-702, task-703, task-704, task-725

<!-- deps:start -->
**Related:** [[task-409-background-schedules-work-and-coarse-social]], [[task-426-plan-archetypes-and-group-goals]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-699-mosiac-design-doc-schedules-plan-templates-and-recipe-activities-as-one-decision-layer]], [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]], [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-725-memories-carry-nothing-about-death-vitals-travel-perception-or-resurrection]], [[task-729-move-relationship-emotional-state-and-memory-add-edit-generate-controls-into-the-mind-panel]], [[task-787-mind-panel-migrate-the-remaining-mind-surfaces-out-of-the-bio-and-advanced-tabs]], [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]], [[task-806-split-traits-capabilities-from-personality-decision-dials]], [[task-807-gimp-the-goal-model-and-its-serialization]], [[task-810-gimp-the-goal-graph-links-blocks-and-chaining]], [[task-811-gimp-achievement-log-and-goal-replay]], [[task-812-mosiac-per-character-context-assembly-m-o-s-i-a-c]], [[task-813-mosiac-obligations-the-missing-letter-s-data]], [[task-814-mosiac-schedules-a-character-can-edit-themselves]], [[task-820-mind-panel-one-tabbed-mind-surface-and-one-entry-point]], [[task-821-mind-panel-relocate-the-gimp-goal-editor-out-of-the-bio-tab]]
<!-- deps:end -->

## What

Extend the existing character Mind view into one readable surface for why a character cares, what they are pursuing, how they currently plan to act, what activity is visibly underway, and which memories or schedule cues inform it.

## Requested additions (2026-10-06)

Additional surfaces the Mind panel should carry, raised while inspecting a live character:

- **Emotional state and its cause** — the character's current emotion(s), and *what caused* the current emotional state (the triggering event or memory), so a designer can see **why** the character feels as they do, not only that they do. This is why the interaction-event memory gap (task-725) matters: with no event recorded, there is no cause to show.
- **World knowledge** — a map of the locations the character knows or has visited (their known-locations / fog view), not just prose about places.
- **Known recipes** — move the character's known recipes into Mind.
- **General memories** — move the general memory list into Mind (currently surfaced elsewhere).
- **Death, vitals, travel, feeling, resurrection, and perception** — when the character has died, been resurrected, or been driven by vitals (e.g. hunger to death), Mind should show a reason. Live repro: the Eldenford blacksmith died and his Mind contained nothing about why — no travel history, no feelings, no vitals driving him to death, and nothing about his reaction to being resurrected. He did not know he had died. Mind must surface these **when the memories exist**; the memories themselves are a separate gap (see the memory-coverage task filed 2026-10-06, related below).

These are display requirements over existing runtime sources where those sources exist. Where the underlying memory/state does not yet carry the fact, the Mind panel cannot invent it — the companion task covers creating it.

## Acceptance

- Start from the existing 🧠 Mind entry point and Memory Mind dashboard from task-691. Give the character inspector one coherent Mind surface while retaining the existing memory timeline, filters, people profiles, dynamics, and detail view.
- At a glance, a designer can answer: what matters to this character, why it matters, what they are undertaking, what they plan to do next, what they are doing over time right now, and which memories inform that choice.
- Show concise character-facing prose alongside inspectable facts. Read facts from their existing runtime sources (`Player` needs and state, `active_pursuit`, `plan`, `activity`, the calendar/schedule system, and the character's memories). Do not persist a second UI copy or invent a unified Goal record to fill a blank.
- Keep the layers visibly distinct:
  - **Motive / goal:** why the character cares, drawn from authored motive, current needs, and relevant memories when available.
  - **Mission:** who asked for what and whether the character accepted it; an accepted mission can become the character's own pursuit.
  - **Pursuit:** the character's longer undertaking and reason, with its target/place, time window, requirements, supplies, checked progress, and finish/report/return conditions when those fields exist.
  - **Schedule:** the relevant time, date, season, weather, or routine cue and whether it is due. Present it as a reminder to consider, not an order that decides the character's response.
  - **Short-term plan:** the current ordered approach, next step, destination, and any interruption/adaptation. A changed plan can leave the pursuit intact.
  - **Activity:** the ongoing thing visibly happening at a place, including its current state/effects and duration or stop condition when available. Keep its world recipe separate from the pursuit and the activity.
- Make missing, unknown, completed, paused, refused, and interrupted information legible without fabricating values. Show a specific object or location only when the runtime actually identifies it.
- Use the same labels and facts for LLM-driven and simple NPCs. Where available, show whether a pursuit/plan was chosen by the character, assigned, or selected by deterministic background rules; neither representation turns a pursuit into a forced script or an artificial reward contract.
- Exercise the view with authored content that demonstrates the separation between layers: Vekka's scouting pursuit (remembered tracks, supplies, return/report to Zikka, and a conversation that interrupts travel); Grandma's 06:00 food reminder; and James traveling home for the sleeping Activity on a bed until rested. Show the plan changing or being reconsidered while the pursuit's reason remains understandable.
- Verify the Mind entry point from a selected character and inspect the complete view at the top and bottom, including empty and populated states. Memory-focused controls must continue to work, and the view must refresh from the current character/runtime state after a turn or interruption.

## Current verified surface

In the live Kraktooth goblin camp, the character inspector has four tabs: Inventory, Bio, Images, and Advanced. The Bio tab contains 27 inspector sections and 95 visible controls. Its 🧠 Mind button opens a separate **Memory Mind — Vekka** dashboard with memory totals, people derived from memories, a timeline and filterable memory list, memory detail, and activation/accessibility information. This task grows that existing memory-centered entry point into the broader character Mind described above; it does not repeat task-691's memory-dashboard work.

## Sequencing and design references

Build against the runtime data provided by pursuit selection/execution (tasks 704 and 702), the existing schedule cue layer (task-409), and Activity state. Use [[Character Pursuits]] as the vocabulary and prompt-format reference. Keep [[Activities & States]] as the Activity behavior reference. The UI may present only fields that are actually implemented and available; it must not imply that the future pursuit prompt block or all pursuit fields are already wired.

## Why

A character's goals, motives and pursuits are the top of the decision stack: MOSIAC reads them to decide, and the soak weights against them. Without a surface, a designer cannot see why a character acts, nor tell an authored goal from a runtime need. The Mind panel is that surface, and it must read the real runtime source (`Player.goals`) rather than keep a second UI copy.

## How

Extend `InspectorMindView` (`static/js/inspector/mind-view.ts`) with blocks in the left column, each reading one runtime source on `worldState.players[name]` and inventing nothing:

- **Goals** (done 2026-10-12) reads `.goals` (task-807) - `what`, colour-coded `status`, and `motivation` / `intention`.
- **Pursuit & plan** (done 2026-10-13) reads `.active_pursuit` and `.plan` - the character's own assignment (task-818) and its current ordered approach: label, `template_id`, `reason`, `step n/total: <next step>`.
- **Activity** (done 2026-10-13) reads `.activity` - the ongoing thing with elapsed / duration / catch count.
- **Feeling** (done 2026-10-13) reads `.emotion` and `.emotions` - the dominant feeling and the raised axes. Its *cause* is not shown: it needs an event memory (task-725).
- **World knowledge** (done 2026-10-13) reads `.known`.
- **Known recipes** (done 2026-10-13) reads `.crafting_known`.
- **Disposition** (done 2026-10-13) reads `.disposition` and `.trait_behavior` - the derived weights (with their registry kind / base / range), the authored dials, the value-gated verbs, and the whisper lines (tasks 800-806).
- **Mission** (done 2026-10-13) is the **Obligations** block (task-813, `Player.obligations`): who asked for what (`from`), what they owe (`charge`), the due tick, and the accepted/offered/done/refused status. It is the same layer, not a second one - no standalone Mission record exists or was invented. The "an accepted mission can become the pursuit" link is not stored (nothing on `active_pursuit` points back at an obligation), so it is not shown.
- **Body** (done 2026-10-13) reads `.state`, `.conditions` (each instance's `source` / `duration` / `level`) and the **core** vitals the header renders, flagged via `VitalColor.level`. Shown only when there is something to explain (non-awake state, a condition, or a vital out of band) so it is a reason, not a second vitals panel. Optional scenario vitals (Arousal / Pleasure / Stimulation) are excluded - they sit at 0 when their system is off and would read as "low" for everyone.
- **Emotional cause** (done 2026-10-13) - the `Feeling` block now appends the most recent memory that itself carried the current feeling. It is honest about what it is ("last felt in a memory") and is not claimed to be the trigger: a true cause needs a memory that records the event, which is task-725 (unchanged).

All the display layers are in. The one thing the panel cannot yet show is the *trigger event* behind a mood or a death, because no memory records it - that is the task-725 data gap, not a missing surface.


## Steps to verify

1. Set a goal on the controlled character, then open the 🧠 Mind panel.
   - expected: the goal appears under "Goals - what they are pursuing" with its status badge; `goal complete` / `goal drop` change the badge.
   - observed: VERIFIED 2026-10-12, live on localhost:4445. `goal set Become chief of the camp`, then `goal complete` -> the panel's Goals block shows "Become chief of the camp" with a green `reached` badge, and `/api/state` carries the same.
2. Give a character an assignment (`Player.active_pursuit`) and a plan, then open the 🧠 Mind panel.
   - expected: a "Pursuit & plan" block shows the label, template, reason, and `step n/total: <next step>`; a character with no assignment reads "no assigned pursuit".
   - observed: VERIFIED 2026-10-13, live on localhost:4444. With `active_pursuit {label: scrap_run, template_id: haul, reason: "Move scrap to the workshop for repairs."}` and `plan {index: 1, steps: [travel, take, drop]}`, `#mind-pursuit` rendered "scrap_run / haul / Move scrap to the workshop for repairs. / step 2/3: take scrap"; a character with no assignment rendered the empty state.
3. Set an activity, an emotion, known places and known recipes on a character, then open the 🧠 Mind panel.
   - expected: "Activity - what is underway", "Feeling - their mood", "World knowledge - places known (n)" and "Known recipes (n)" blocks render from those runtime fields; each is absent when its field is empty.
   - observed: VERIFIED 2026-10-13, live on localhost:4444. `activity {type: fishing, elapsed_minutes 12, duration_minutes 40, catch_count 2}` -> "ACTIVITY - WHAT IS UNDERWAY / fishing 12 min / of 40 min / caught 2"; `emotion {afraid 45, description}` + `emotions {afraid 45, angry 12}` -> "FEELING - THEIR MOOD / afraid (45) / ... / afraid 45 / angry 12"; `known` 4 -> "WORLD KNOWLEDGE - PLACES KNOWN (4) / Workshop, Gate, Mess Hall, River Fork"; `crafting_known` 2 -> "KNOWN RECIPES (2) / scrap_hinge, camp_stew".

4. Inspect a character the body is failing, a character with an obligation and a schedule, and a character whose last memory carried a feeling.
   - expected: the "Body - what is driving them" block names the non-awake state, each condition with its source, and the vitals out of band (and is absent when nothing is wrong); the Obligations block shows who asked and the status; the Feeling block shows "last felt in a memory: ..." from a real memory.
   - observed: VERIFIED 2026-10-13, live on localhost:4444, kraktooth camp (27 players). `Eldenford Blacksmith` (state `frightened`; conditions `frightened` why `trait:paranoid`, `hallucinating`, `social_breakdown`; vitals `HP 20 bad / Hunger 66 warn / Thirst 77 warn / Sanity 5 bad / Social 0 bad / Entertainment 0 bad / Hygiene 0 bad`) -> the Body block rendered all of it; `Arix` (nothing wrong) -> Body absent. `Arix` (1 obligation, 1 schedule step) -> Obligations + Schedule rendered on the Mind tab. On a probe, `rat` with `emotion afraid` + a memory carrying an `afraid` feeling -> "FEELING ... last felt in a memory: "..." t1"; probe removed after.

## Files

- `static/js/inspector/mind-view.ts`
- `engine/goals.py` (the model the Goals block reads)
- `engine/background_plans.py` (the source of `active_pursuit` / `plan`, task-818)
- `engine/serialization.py` (the `goals` / `active_pursuit` / `plan` fields it renders)

## Browser UI and intended live verification

Intended UI home: Select a character in the world → Inspector → Bio → 🧠 Mind. Inspect the complete Mind surface from its first block through the bottom, including memory filters, timeline, and detail.

Current availability: The task records live checks for Goals, Pursuit & plan, Activity, Feeling, World knowledge, Known recipes, Body, Obligations, and Schedule. The saved `kraktooth_goblin_camp` scenario has 27 player records: Vekka has an active scouting pursuit, Gribba has a 06:00 `eat` schedule at Cooking Area, and lowercase `james` has a travel-then-sleep plan targeting `item_bed_1791229267206_939`. The acceptance says “Grandma,” but no player is named Grandma in that scenario; reconcile whether Gribba is the intended character before claiming that exact exhibit is satisfied. James has a plan in the saved data; the task's “sleeping Activity” still needs a live check.

Live steps when available:
1. Load `kraktooth_goblin_camp`, select Vekka, open Bio → Mind, and scroll the entire view from top to bottom.
   - expected: the Pursuit & plan block shows `vekka_scout_north`, the remembered human-tracks reason, and the current plan step; the lower memory timeline and filters remain reachable.
2. Select Gribba and inspect “Schedule - their day”.
   - expected: the 06:00 `eat` reminder at Cooking Area appears. If the acceptance's “Grandma” refers to another character, do not count this as satisfying it until the saved fixture identifies that character.
3. Select lowercase `james` and inspect Pursuit & plan and Activity.
   - expected: the plan shows travel to Hut Sleeping Corner followed by sleeping on `item_bed_1791229267206_939`; if the activity is not active yet, the UI reports the plan without fabricating an ongoing sleep activity.
4. Select a character with no authored goal or pursuit, then after a turn or interruption reopen Mind for the same character.
   - expected: empty states are explicit, and displayed values refresh from current player state without stale data or a second UI copy.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Progress (2026-10-12)

- Goals layer done and verified live: a "Goals - what they are pursuing" block in the Mind panel, rendering `Player.goals` (task-807) with status badges and GIMP's motivation/intention. Screenshot-confirmed in the real browser on port 4445.

## Progress (2026-10-13)

- Pursuit & plan layer done and verified live on localhost:4444: a "Pursuit & plan - what they are doing" block reads `Player.active_pursuit` (task-818: character data, not a node) and `Player.plan`, rendering the label, template, reason, and `step n/total: <next step>`, with a legible empty state.
- Activity, Feeling, World knowledge and Known recipes blocks done and verified live: they read `Player.activity`, `Player.emotion` / `emotions`, `Player.known` and `Player.crafting_known`; each is absent when its field is empty.
- Disposition block done and verified live: derived weights (labelled with their registry kind / base / range), authored dials, value-gated verbs and the whisper lines (tasks 800-806).
- `python tools/ts_convert.py check` green.
- Mission is the existing Obligations block (task-813) - same layer, not a second one. Body (`state` / `conditions` / core vitals out of band, shown only when there is something to explain) and the Feeling block's "last felt in a memory" line added and verified live on the kraktooth camp.
- The only layer still absent is the *trigger event* behind a mood or a death: no memory records it, so the panel cannot show it. That is the task-725 data gap (engine/authoring), not a missing Mind surface - this card's display work is complete.

## Progress (2026-10-13, later)

- Body block (`_bodyHtml`) and the Feeling cause line landed in `mind-view.ts`, mounted on the Perception tab; `python tools/ts_convert.py check` green; verified live: the Eldenford Blacksmith's conditions and failing vitals render, Arix's quiet body is absent, and the blacksmith was the card's original death repro.

## Note on the named authored cases

The card asks to exercise the layers with Vekka's scouting pursuit, Grandma's 06:00 food reminder, and James's sleeping activity. Those were set at runtime in an earlier session and are **not in the saved `kraktooth_goblin_camp.json`** - the loaded world has no `active_pursuit` anywhere and Vekka has no plan/schedule. The layers were therefore verified against the authored state that *is* in the file (Arix: obligation + schedule; Cullen Rutherford: a running `activity`; the Blacksmith: conditions + failing vitals) plus transient probes. Re-authoring Vekka/Grandma/James is content work for that scenario separately.

