---
type: task
status: review
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

- [x] A `pursuit_templates` library registry loads and saves versioned entries using the existing library machinery. The partial `engine/pursuit_templates.py` slice and `data/library/pursuit_templates/` are incorporated rather than duplicated.
- [x] The template and bound pursuit instance together represent purpose and character reason, requirements and knowledge, parameters, timing windows, place/route, supplies, short-term steps, progress checks, duration or stop conditions, and optional world-recipe references.
- [x] Templates contain no character-specific proper names; every actor, item, area, person, and time bound to a pursuit instance resolves through the world and the actor's knowledge.
- [x] Requirements use the shared condition vocabulary (task-705); unsupported or unknown requirements fail closed.
- [x] Schedule conditions can read the existing game date, time, season, forecast/weather, moon, sun, and daylight. No new clock/calendar is introduced.
- [x] Activities are references to the existing Activity system, not schedule-template records: a sleep pursuit reaches a valid bed and starts a visible sleeping Activity there; an interruption or invalid bed is handled through the actor's current decision rules.
- [ ] A small authored set exercises the range in Kraktooth and the existing fixture worlds: Mikka's haul, gather/return, Vekka's scout-and-report, sleep-on-a-specific-bed, and a meal pursuit that invokes a world recipe. Add templates when content needs them; do not target a fixed catalog count such as 200. *(4 of 5 authored and tested; the meal entry exists and starts the existing `eating` Activity but cannot invoke a world recipe  -  task-703 owns the recipe store and no `recipes` library or `cooking` activity exists yet.)*
- [ ] The template browser uses the existing library editor. Save/load and validation preserve authored fields without a second source of truth. *(The backend registry round-trips and reloads through `routes/library_ops.write_library_entry`; the library browser UI declares no `pursuit_templates` tab. That gap is shared with `structures`, which the browser also omits, so it is a general browser limitation rather than this card's defect  -  see Remaining blockers.)*

## Current slice

The registry loads seven JSON entries and binds actor-specific values into a
character-side instance. Typed steps and the structured purpose, requirements,
supplies, timing, progress, stop, duration, and recipe fields are validated,
carried through `instantiate` into the bound instance, and passed on by
`build_plan` into the live plan with their bindings already expanded. This is
still only the content and binding layer; it does not make the authored plans
executable by every actor, and no runtime consumer yet reads the structured
fields off the plan.

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

Two defects were found and fixed while authoring the structured fields, both of
which made authored data silently inert:

1. `engine/background_plans.py:build_plan` rebuilt the plan from four of the
   instance's keys and discarded `requirements`, `supplies`, `timing`,
   `progress`, `stop_conditions`, `duration` and `recipe`. A template that
   authored `stop_conditions` validated, bound, and then had the field dropped
   before the runner ever saw it. `build_plan` now passes every structured field
   through.
2. The authored `requirements` used `{"type": "in_area", "target": "self"}`. The
   condition evaluator builds its context key as `f"{target}_area"`, and the NPC
   behaviour context sets `npc_area` and never `self_area`, so the leaf compared
   `None` against an area name and was permanently False. The entries now use the
   default `npc` target, which reads the acting character's area.

The `sleep-at-venue` progress check was also corrected: it first read
`state_equals: sleeping`, but bed nodes carry `current_state: "normal"` and the
leaf needs an `item_node` in context that a pursuit check does not supply, so it
could never be true. It now checks the rested Energy threshold, and the meal
progress check reads Hunger in the direction the engine uses (high Hunger is
hungry, so "fed" is a low value).

The UI browser's declared tab type still omits `pursuit_templates`.

## Steps to verify

1. Run `python -m pytest tests/test_pursuit_templates.py`.
   - expected: validation rejects unsupported leaves, unresolved bindings and
     Activity ids; binding and registry save/load preserve authored values; a
     bound bed ID reaches the existing Activity runner; the structured fields
     survive into the live plan.
   - observed: 34 passed. `test_sleep_at_venue_template_binds_the_exact_activity_target_item`
     and `test_item_id_parameter_reads_the_named_assignment_property` assert the
     `bed_id` binding is read and emitted as `target_item`. In
     `test_sleep_pursuit_starts_activity_on_the_bound_existing_bed`, the
     background caller advances the character to the Bed Room, starts the
     `sleeping` Activity on the exact graph bed node, and preserves the active
     pursuit. `test_timing_reads_the_worlds_own_clock`,
     `test_timing_reads_the_existing_world_date`,
     `test_timing_reads_sun_from_the_existing_on_day_interval` and the
     fail-closed timing tests cover existing clock values.
     `test_structured_fields_reach_the_plan_not_just_the_instance` asserts
     `build_plan` passes requirements/supplies/timing/progress/stop_conditions
     through with bindings expanded, and
     `test_requirements_use_the_context_key_a_background_actor_sets` pins the
     `in_area` target to the `npc_area` key the behaviour context actually sets.
     The registry tests cover all seven entries and a save/load round trip.
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
3. Re-run the lane's neighbouring suites after the `build_plan` change.
   - expected: no regression in the background runner, activity duration, or the
     trigger condition evaluator that the shared leaf vocabulary is read from.
   - observed: `python -m pytest tests/test_pursuit_templates.py
     tests/test_background_plans.py tests/test_activity_duration.py
     tests/test_trigger_system.py` → 205 passed. `CONDITION_TYPES` is 41 on this
     branch (master added `owns` and `known` for task-705), and every leaf the
     authored entries carry is in that set.

## Files

- `engine/plan_steps.py`
- `engine/pursuit_templates.py`
- `engine/background_plans.py`
- `data/library/pursuit_templates/*.json`
- `tests/test_pursuit_templates.py`

## Remaining blockers

Four acceptance gaps remain, none of them fixable inside this card's scope:

1. **No library browser tab.** `static/js/library-browser.ts` declares eight tab
   types and omits both `pursuit_templates` and `structures`. The backend
   registry (`routes/library_ops.REGISTRY_TYPES`) already accepts
   `pursuit_templates`, so only the UI list is missing. Because `structures`
   shares the identical gap, this is a general library-browser limitation and
   belongs in its own card rather than being bolted on here; adding it means
   editing the `.ts` source, the tab HTML in `templates/index.html`, and a
   `ts_convert.py` rebuild.
2. **No runtime consumer of the structured fields.** `build_plan` now passes
   `requirements`, `supplies`, `timing`, `progress`, `stop_conditions`,
   `duration` and `recipe` onto the plan, but no runner reads them off it yet.
   Enforcing them  -  invalidating a plan when a requirement stops holding,
   honouring a timing window, advancing a progress check, stopping on a stop
   condition  -  is task-702's executor work.
3. **No timing selector caller.** `timing_matches` is a prompt input for
   selection and has no caller; the selector that would use it is task-704.
4. **The meal entry cannot invoke a world recipe.** There is no `recipes`
   directory under `data/library/` and no `cooking` activity, so the entry
   starts the existing `eating` Activity instead. task-703 owns the recipe store.

Separately, the saved scenario has no physical route to James's bed: a
breadth-first walk over `connection` edges from his `area_world_15_5` visits
1,962 nodes and cannot reach `area_fisherman_s_hut_1_1`, where the bound bed is
located. Fixing this requires a graph connection outside the character-content
lane. In the integrated live scenario, hunger preempted his plan for 12
consecutive ticks; the engine's survival precedence is working correctly, but
this content does not demonstrate arrival at the bed.

Do not start task-702 until task-701 is accepted; task-702 remains blocked by
task-700 and task-701.
