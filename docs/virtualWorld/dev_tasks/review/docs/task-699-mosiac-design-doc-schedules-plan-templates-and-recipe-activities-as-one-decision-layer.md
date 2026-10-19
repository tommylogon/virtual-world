---
type: task
status: review
area: docs
priority: high
related: [task-409, task-426, task-2, task-694, task-701, task-702, task-703, task-704]
---

# task-699: Character pursuits, schedules, plans, activities, and recipes

**System name:** **MOSIAC** - Motivation, Obligations, Schedules, Intentions, Attention, Choice. This card is the design doc for the MOSIAC decision layer; see `Character Pursuits.md`.

**Filed:** 2026-10-04
**Clarified:** 2026-10-05

<!-- deps:start -->
**Related:** [[task-409-background-schedules-work-and-coarse-social]], [[task-426-plan-archetypes-and-group-goals]], [[task-2-crafting_and_recipes]], [[task-694-htc-fixture-world-a-tiny-scenario-authored-to-exercise-every-turn-panel-surface]], [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]], [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]]
<!-- deps:end -->

## What

Keep the game-design model in [`Character Pursuits.md`](../../../design/Character%20Pursuits.md) accurate. The earlier draft used “schedule” as the umbrella for reusable activities and blurred an ongoing Activity with the Pursuit that can bring a character to it. The corrected model distinguishes character goals and reasons, missions, reusable pursuit templates, active pursuits, calendar schedules, short-term plans, observable Activities, and world recipes.

## Acceptance

- [x] Defines a **Goal** as the character's desired outcome and reason; keeps motivations human-readable and world consequences grounded rather than inventing generic reward points.
- [x] Defines **Mission** as an external request or charge that a character can accept, alter, decline, and potentially adopt as a pursuit.
- [x] Defines **Pursuit** as a character-owned longer undertaking, with a reusable template and actor-specific motive, target, requirements, timing, resources, progress, and stop conditions.
- [x] Defines **Schedule** as the calendar/routine layer that can prompt a pursuit at a time, date, season, or world condition; preserves the existing HH:MM schedule implementation as that narrow layer.
- [x] Defines a **short-term plan** as the current grounded approach, distinct from the pursuit it advances.
- [x] Defines an **Activity** as an observable, time-spanning world process at a place, with actual state effects, duration or stopping conditions, and interruption behavior. Shows a sleep pursuit bringing James home before a sleeping activity starts on a specific bed.
- [x] Separates an Activity such as cooking from a world recipe such as cooked fish; the recipe owns the transformation inputs and outputs.
- [x] Explains how LLM agents, simple NPCs, and background simulation can use the same pursuit/activity vocabulary with different decision detail.
- [x] Gives a structured-plus-prose prompt example with `what`, `where`, `when`, supplies, requirements, checked progress, reason, and interruption handling. Clearly marks the pursuit prompt block as planned rather than currently wired.
- [x] Uses existing date, clock, season, weather, moon, sun, and daylight state rather than proposing another calendar.
- [x] Keeps the grounded Vekka exhibit, fifteen example pursuits/activities, the fisherman acceptance case, actor sovereignty, and the current implementation boundary.
- [x] Links the design from the background-simulation documentation and feature index.

## Correction (2026-10-05)

The prior draft described reusable activities as “schedules.” The designer clarified that fishing, cooking, bathing, sleeping, and similar things are **Activities**: they occur over time in a place, can be perceived, and may be interrupted. A **Pursuit** can include travel to the activity and carry the character's reason for doing it. A **Schedule** stays the clock/calendar reminder layer. `Character Pursuits.md` now uses those meanings throughout and separates current behavior from planned wiring.

## Why

Previous planning conflated schedules, long-term pursuits, moment-to-moment plans, and ongoing activities, treating them all as monolithic schedules. This conceptual entanglement caused engine implementations to blur travel from actual work, hindered crafting/activity integration, and prevented background NPCs from sharing behavioral vocabulary with LLM agents. Defining the MOSIAC architecture in Character Pursuits.md provides an unambiguous, formal hierarchy of goals, pursuits, schedules, plans, and observable activities.

## How

1. Author comprehensive design specification in docs/virtualWorld/design/Character Pursuits.md.
2. Formalize distinction between Goals (motives), Missions (external requests), Pursuits (undertakings), Schedules (clock prompts), Plans (approach steps), Activities (observable continuous world processes), and Recipes (crafting transforms).
3. Provide concrete exhibits: Vekka scouting mission, James travel-home-to-sleep pursuit loop, and fisherman vertical slice.
4. Integrate cross-references to runtime implementation tasks (task-701 plan templates, task-702 plan executor, task-703 recipes, task-704 MOSIAC selector).

## Steps to verify

1. Review docs/virtualWorld/design/Character Pursuits.md against MOSIAC vocabulary.
   - expected: Clear, consistent definitions for Goal, Mission, Pursuit, Schedule, Plan, Activity, and Recipe.
   - observed: Complete design doc delivered in review.
2. Verify alignment with implementation tasks.
   - expected: Linked child tasks (701-704) reference exact structures described in design doc.
   - observed: Cross-references verified.

## Files

- docs/virtualWorld/design/Character Pursuits.md
- docs/virtualWorld/Characters/Background Simulation.md

## Browser UI and intended live verification

Intended UI home: Not applicable - this card changes the design manual at `docs/virtualWorld/design/Character Pursuits.md`; it does not add a browser interaction.

Current availability: The design note exists. Runtime behavior is tracked by the linked implementation cards and is not asserted by this documentation card.

Live steps when available: Not applicable.

Why no browser UI: The deliverable is a written design reference, not a player or authoring surface.

Alternative verification steps:
1. Open `docs/virtualWorld/design/Character Pursuits.md` and follow its sections for Goal, Mission, Pursuit, Schedule, Plan, Activity, and Recipe.
   - expected: each term has a distinct definition, and the text explains how LLM agents and background simulation use the same vocabulary.
2. Read the Vekka scouting and James sleep examples in that note.
   - expected: Vekka's motive, supplies, route, return/report condition and interruption remain distinct from her short-term plan; James travels home before sleeping on a named bed, and the world recipe is separate from the Activity.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
