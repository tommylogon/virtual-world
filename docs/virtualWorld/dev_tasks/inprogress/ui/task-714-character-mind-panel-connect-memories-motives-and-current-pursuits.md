---
type: task
status: inprogress
area: ui
priority: medium
related: [task-409, task-426, task-691, task-699, task-701, task-702, task-703, task-704, task-725, task-800, task-802, task-806, task-807, task-810, task-811, task-812, task-813, task-814]
---

# task-714: Character Mind panel: connect memories, motives, and current pursuits

**Filed:** 2026-10-05
**Related:** task-409, task-426, task-691, task-699, task-701, task-702, task-703, task-704, task-725

<!-- deps:start -->
**Related:** [[task-409-background-schedules-work-and-coarse-social]], [[task-426-plan-archetypes-and-group-goals]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-699-mosiac-design-doc-schedules-plan-templates-and-recipe-activities-as-one-decision-layer]], [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]], [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-725-memories-carry-nothing-about-death-vitals-travel-perception-or-resurrection]], [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]], [[task-806-split-traits-capabilities-from-personality-decision-dials]], [[task-807-gimp-the-goal-model-and-its-serialization]], [[task-810-gimp-the-goal-graph-links-blocks-and-chaining]], [[task-811-gimp-achievement-log-and-goal-replay]], [[task-812-mosiac-per-character-context-assembly-m-o-s-i-a-c]], [[task-813-mosiac-obligations-the-missing-letter-s-data]], [[task-814-mosiac-schedules-a-character-can-edit-themselves]]
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

Extend `InspectorMindView` (`static/js/inspector/mind-view.ts`) with a Goals block in the left column, below People. It reads `worldState.players[name].goals`, the character's own record, serialized in the players block (task-807), and renders each goal's `what`, `status` (colour-coded), and its `motivation` / `intention` (GIMP's M and I) when present. No second copy and no unified Goal record is invented to fill a blank; an empty list reads "no goals".

Still to add, layer by layer (per the acceptance list): Mission, Pursuit, Schedule, Short-term plan, Activity, plus world knowledge, known recipes, general memories, and the emotional-cause and death/vitals surfaces. Each reads its own runtime source.

## Steps to verify

1. Set a goal on the controlled character, then open the 🧠 Mind panel.
   - expected: the goal appears under "Goals - what they are pursuing" with its status badge; `goal complete` / `goal drop` change the badge.
   - observed: VERIFIED 2026-10-12, live on localhost:4445. `goal set Become chief of the camp`, then `goal complete` -> the panel's Goals block shows "Become chief of the camp" with a green `reached` badge, and `/api/state` carries the same.

## Files

- `static/js/inspector/mind-view.ts`
- `engine/goals.py` (the model it reads)
- `engine/serialization.py` (the `goals` field it renders)

## Progress (2026-10-12)

- Goals layer done and verified live: a "Goals - what they are pursuing" block in the Mind panel, rendering `Player.goals` (task-807) with status badges and GIMP's motivation/intention. Screenshot-confirmed in the real browser on port 4445.
- Remaining layers: Mission, Pursuit, Schedule, Short-term plan, Activity; and world knowledge, known recipes, general memories, death/vitals/perception.
