---
type: task
status: inprogress
area: library
priority: high
related: [task-694, task-2, task-409, task-426, task-699, task-807]
---

# task-701: Pursuit template library: reusable undertakings as versioned entries

**Filed:** 2026-10-04
**Clarified:** 2026-10-05

<!-- deps:start -->
**Related:** [[task-694-htc-fixture-world-a-tiny-scenario-authored-to-exercise-every-turn-panel-surface]], [[task-2-crafting_and_recipes]], [[task-409-background-schedules-work-and-coarse-social]], [[task-426-plan-archetypes-and-group-goals]], [[task-699-mosiac-design-doc-schedules-plan-templates-and-recipe-activities-as-one-decision-layer]], [[task-807-gimp-the-goal-model-and-its-serialization]]
<!-- deps:end -->

## What

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

The registry loads seven JSON entries and binds actor-specific values into a
character-side instance. Typed steps and the structured purpose, requirements,
supplies, timing, progress, stop, duration, and recipe fields are validated and
preserved by the existing registry writer. This is still only the content and
binding layer; it does not make the authored plans executable by every actor.

## Why

Without a reusable, validated library, longer undertakings remain hardcoded in the
background planner and cannot be selected or authored consistently across
characters. The template must describe the undertaking while the bound pursuit
keeps the actor-specific reason and world references.

## How

Added a declared plan-step vocabulary in `engine/plan_steps.py` and extended
`engine/pursuit_templates.py` to validate shared condition leaves, supplies,
progress and stop-condition records, recipe references, timing fields, step
fields, bindings, and Activity references. Added `meal`, `scout-and-report`, and
`sleep-at-venue` entries alongside the existing catalog. The existing generic
library writer and pursuit-template loader preserve arbitrary authored fields.
The UI browser's declared tab type still omits `pursuit_templates`.

## Steps to verify

1. Run `python -m pytest tests/test_pursuit_templates.py`.
   - expected: validation rejects unsupported leaves, unresolved bindings and
     Activity ids; binding and registry save/load preserve authored values; a
     bound bed ID reaches the existing Activity runner.
   - observed: 30 passed. `test_sleep_at_venue_template_binds_the_exact_activity_target_item`
     and `test_item_id_parameter_reads_the_named_assignment_property` assert the
     `bed_id` binding is read and emitted as `target_item`. In
     `test_sleep_pursuit_starts_activity_on_the_bound_existing_bed`, the
     background caller advances the character to the Bed Room, starts the
     `sleeping` Activity on the exact graph bed node, and preserves the active
     pursuit. `test_timing_reads_the_worlds_own_clock`, the date/sun tests, and
     the fail-closed timing tests cover existing clock values. The registry
     tests cover all seven entries and a save/load round trip.
2. Check the authored timing and pursuit templates against the acceptance list.
   - expected: date, time, season, forecast/weather, moon, sun and daylight are
     read from the existing world clock; authored examples resolve real world
     references and their observable behavior is verified.
   - observed: partial. `timing_matches` reads date, hour, season, forecast
     state, moon phase, and an hour-derived sun/daylight band; no runtime
     selector caller was found. `test_scout_and_report_template_runs_end_to_end`
     verifies travel to the scout area and back and the pursuit completion log,
     but there is no report interaction or report fact to verify. The meal
     template starts the existing eating Activity but has no world-recipe
     reference or recipe execution. The Kraktooth content lane was live-checked:
     Vekka's pursuit and plan render in Mind Layers and `/api/state`; the water
     skin and dagger IDs resolve, while the backpack is held by the Eldenford
     Merchant and the report condition is explicitly not checkable. Gribba's
     06:00 `eat` schedule and James's travel/sleep plan also render and appear in
     `/api/state`; James's bed ID resolves to a bed in Hut Sleeping Corner.
     The schedule's `eat` value is accepted and persisted; the current scheduler
     only starts blocking Activities for `work` and `rest`, so this entry does
     not itself force an eating Activity or emit an explicit reminder.
     On the current integration branch, live ticks 59–71 left James's plan at
     index 0 and `activity` null. His `needs:hunger` travel oscillated between
     `Road (world 15,5)` and `Road (world 16,6)`, so the survival cascade kept
     preempting the authored sleep plan. This does not invalidate the isolated
     sleep mechanism test, but the Kraktooth runtime path still does not reach
     bed activity. The library browser still has no `pursuit_templates` tab,
     and this lane's file boundary excludes `static/js/**`.

## Files

- `engine/plan_steps.py`
- `engine/pursuit_templates.py`
- `data/library/pursuit_templates/*.json`
- `tests/test_pursuit_templates.py`

## Remaining blockers

This card stays in `inprogress`. The sleep template now binds an exact `item_id`
to the `target_item` field read by the existing runner, and a focused test proves
that caller starts a visible sleeping Activity on the bound bed while retaining
the pursuit. Remaining acceptance gaps are the missing pursuit-template browser
tab, the lack of a timing selector caller, a checkable report interaction, and a
meal template that invokes a real world recipe. The authored Kraktooth scenario
is live-verified, but Vekka's backpack is carried by another character and her
report condition cannot complete in the current system. In the integrated live
scenario, hunger preempted James's plan for 12 consecutive ticks and sent him
between two road nodes; his plan index remained 0 and `activity` remained null.
The engine's survival precedence is working, but this content does not
demonstrate arrival at the bed. Do not start task-702 until task-701 is accepted;
task-702 remains blocked by task-700 and task-701.

The saved scenario also has no physical route to that bed: a breadth-first walk
over `connection` edges from James's `area_world_15_5` visits 1,962 nodes and
cannot reach `area_fisherman_s_hut_1_1`, where the bound bed is located. Fixing
this requires a graph connection outside the character-content lane.
