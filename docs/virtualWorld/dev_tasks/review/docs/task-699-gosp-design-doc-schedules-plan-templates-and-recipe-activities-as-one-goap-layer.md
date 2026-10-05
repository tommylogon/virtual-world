---
type: task
status: review
area: docs
priority: high
related: [task-409, task-426, task-2, task-694, task-701, task-702, task-703, task-704]
---

# task-699: Character pursuits, schedules, plans, activities, and recipes

**Filed:** 2026-10-04
**Clarified:** 2026-10-05

## Goal

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
