---
type: task
status: todo
area: library
priority: high
related: [task-694, task-2, task-409, task-426, task-699]
---

# task-701: Pursuit template library: reusable undertakings as versioned entries

**Filed:** 2026-10-04
**Clarified:** 2026-10-05

## Goal

Provide reusable, character-agnostic pursuit templates that characters can choose, be offered, or be assigned. A template is like a recipe for a longer undertaking: it says what the character is trying to do, where and when it applies, what they need or must know, how progress is checked, and when to stop. The bound pursuit instance adds the character's own reason and target. A template does not force an LLM agent to comply.

Keep the meanings separate:

- A **Goal** explains the desired outcome and the character's reason.
- A **Mission** is an external request; accepting it may create a pursuit.
- A **Pursuit template** is reusable authored content; an **active pursuit** belongs to one character.
- A **Schedule** is a calendar rule that can prompt or time a pursuit.
- A **short-term plan** works out the current approach to the pursuit.
- An **Activity** is the visible, ongoing process at a location (for example, sleeping on a bed).
- A **world recipe** defines how a transformation resolves; an Activity may enact it.

## Acceptance

- [ ] A `pursuit_templates` library registry loads and saves versioned entries using the existing library machinery. The partial `engine/pursuit_templates.py` slice and `data/library/pursuit_templates/` are incorporated rather than duplicated.
- [ ] The template and bound pursuit instance together represent purpose and character reason, requirements and knowledge, parameters, timing windows, place/route, supplies, short-term steps, progress checks, duration or stop conditions, and optional world-recipe references.
- [ ] Templates contain no character-specific proper names; every actor, item, area, person, and time bound to a pursuit instance resolves through the world and the actor's knowledge.
- [ ] Requirements use the shared condition vocabulary (task-705); unsupported or unknown requirements fail closed.
- [ ] Schedule conditions can read the existing game date, time, season, forecast/weather, moon, sun, and daylight. No new clock/calendar is introduced.
- [ ] Activities are references to the existing Activity system, not schedule-template records: a sleep pursuit reaches a valid bed and starts a visible sleeping Activity there; an interruption or invalid bed is handled through the actor's current decision rules.
- [ ] A small authored set exercises the range in Kraktooth and the existing fixture worlds: Mikka's haul, gather/return, Vekka's scout-and-report, sleep-on-a-specific-bed, and a meal pursuit that invokes a world recipe. Add templates when content needs them; do not target a fixed catalog count such as 200.
- [ ] The template browser uses the existing library editor. Save/load and validation preserve authored fields without a second source of truth.

## Current slice

The current registry/module has haul, gather, and rally templates with typed travel/take/drop steps. This is partial background content. It does not yet support the full pursuit schema, LLM selection, ongoing Activity steps, or the prompt block; those are follow-up acceptance criteria above.
