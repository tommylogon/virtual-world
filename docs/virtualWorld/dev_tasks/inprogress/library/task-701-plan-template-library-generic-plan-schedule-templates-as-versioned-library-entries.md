---
type: task
status: inprogress
area: library
priority: high
related: [task-694, task-2, task-409, task-426, task-699, task-807]
wiki: "[[design/Character Pursuits]]"
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

2026-10-17: the resume-path timing gate shipped. `maybe_assign`
(`engine/background_plans.py`) consults `timing_matches` against the world's
own clock before building the plan: a closed window holds the start, the
assignment survives the wait, and an already-running approach is never stopped
by dusk. Two tests pin the branch
(`test_the_resume_path_waits_for_the_window_then_starts`,
`test_a_mid_run_approach_is_not_stopped_by_a_closing_window`).

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

## Browser UI and intended live verification

Intended UI home: Build → Library → Pursuit Templates in the existing editor; Character Inspector → Mind → Pursuit for the copied instance.

Current availability: The registry and seven entries bind actor-specific values; the library tab is built and was live-verified in the open browser on 2026-10-17 (see the observed notes); generic execution/selection completeness is what the live run chain is checking.

Live steps when available:

1. Open the Library editor’s Pursuit Templates category and inspect a reusable scout or sleep entry.
   - expected: The existing editor exposes the versioned, character-agnostic template and its authored fields.

2. Bind it to a character, then inspect that character’s Mind → Pursuit.
   - expected: The character-side instance carries its own reason and world references; it does not reference the source template as live state.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Run `python -m pytest tests/test_pursuit_templates.py`.
   - expected: validation rejects unsupported leaves, unresolved bindings and
     Activity ids; binding and registry save/load preserve authored values; a
     bound bed ID reaches the existing Activity runner.
   - observed: 38 passed (2026-10-17). `test_sleep_at_venue_template_binds_the_exact_activity_target_item`
     and `test_item_id_parameter_reads_the_named_assignment_property` assert the
     `bed_id` binding is read and emitted as `target_item`. In
     `test_sleep_pursuit_starts_activity_on_the_bound_existing_bed`, the
     background caller advances the character to the Bed Room, starts the
     `sleeping` Activity on the exact graph bed node, and preserves the active
     pursuit. `test_timing_reads_the_worlds_own_clock`, the date/sun tests, and
     the fail-closed timing tests cover existing clock values. The registry
     tests cover all seven entries and a save/load round trip. New today for
     the resume gate, the recipe step and the report condition:
     `test_the_resume_path_waits_for_the_window_then_starts`,
     `test_a_mid_run_approach_is_not_stopped_by_a_closing_window`,
     `test_a_recipe_step_opens_the_existing_cooking_flow`,
     `test_a_recipe_step_fails_closed_when_the_inputs_are_missing`,
     `test_met_character_resolves_names_keys_and_node_ids`,
     `test_a_reported_pursuit_delivers_the_receipt_and_tells_the_recipient`,
     `test_progress_checks_flip_the_assignments_own_progress_dict`, and
     `test_the_completion_hook_runs_progress_and_reports_once`.
2. Check the authored timing and pursuit templates against the acceptance list.
   - expected: date, time, season, forecast/weather, moon, sun and daylight are
     read from the existing world clock; authored examples resolve real world
     references and their observable behavior is verified.
   - observed: resolved 2026-10-17 except where noted. `timing_matches` reads
     date, hour, season, forecast state, moon phase, and an hour-derived
     sun/daylight band, and the resume gate in `maybe_assign` is its runtime
     caller (start gate only; the MOSIAC selection consult stays with
     task-704). The report leg is now a checkable fact: the shared
     `met_character` leaf is declared in `trigger_validator.CONDITION_TYPES`
     and evaluated in the trigger leaf registry;
     `background_plans._check_progress` evaluates template progress leaves
     onto the assignment's own progress dict;
     `background_plans._deliver_report` flips the
     `progress.report_delivered` receipt and writes the authored
     `report_text` onto the recipient as a memory through `AgentMind`.
     Vekka's authored pursuit in the Kraktooth scenario is now
     `report_condition.checkable: true` with a `report_text`. The meal
     template is v2: its cooking step names `barley_pottage` and the
     executor routes recipe steps through `CraftingSystem.start_cooking`
     with the actor swapped in; missing inputs fail closed with a trace. The Kraktooth content lane was live-checked:
     Vekka's pursuit and plan render in Mind Layers and `/api/state`; the water
     skin and dagger IDs resolve, while the backpack is held by the Eldenford
     Merchant; the report condition was authored `checkable: false` at that
     time and is now checkable (see above) with live verification pending.
     Gribba's
     06:00 `eat` schedule and James's travel/sleep plan also render and appear in
     `/api/state`; James's bed ID resolves to a bed in Hut Sleeping Corner.
     The schedule's `eat` value is accepted and persisted; the current scheduler
     only starts blocking Activities for `work` and `rest`, so this entry does
     not itself force an eating Activity or emit an explicit reminder.
     On the current integration branch, live ticks 59-71 left James's plan at
     index 0 and `activity` null. His `needs:hunger` travel oscillated between
     `Road (world 15,5)` and `Road (world 16,6)`, so the survival cascade kept
     preempting the authored sleep plan. This does not invalidate the isolated
     sleep mechanism test, but the Kraktooth runtime path still does not reach
     bed activity. The library browser tab was added in this pass (a
     `pursuit_templates` tab and generic JSON editor in the existing modal).
     Live check of that tab, 2026-10-17 in the open browser: the Library
     Browser opened with all tabs including the new one, the Pursuits tab
     lists all seven authored templates ("7 entries"), `+ New` opens the
     pursuit editor with the full field set (`lib-ed-id`, `lib-ed-name`,
     `lib-ed-purpose` and the JSON textareas), a throwaway probe entry saved
     through the editor landed on disk (`probe_pursuit_tab.json`), a fresh
     open listed it ("8 entries"), and a same-session delete removed it again
     (`DELETE /api/library/pursuit_templates/probe_pursuit_tab`; seven
     templates remain). One soft observation: after a save the already-open
     list keeps its previous count until the modal is reopened. The route fix
     was also authored live: `way_gateway_world_fisherman_s_hut`
     ("Entrance to the fisherman's hut", straight world-road to
     interior-first-room, per the deep-woods gateway convention) was created
     through the app's own `POST /api/build/connect`, a BFS over the live
     graph then reaches `area_fisherman_s_hut_1_1` (2,021 nodes vs the capped
     1,962 before), and the way was committed into the scenario source via the
     Changes panel (`POST /api/scenario/diff/apply {commit:["ways"]}` - the
     drift showed exactly one added way). Note `/api/save-scenario` only
     returns `to_scenario_dict`; the disk write path for authored content is
     the diff-panel commit.
     Live run 1 of the full authored chain, 2026-10-17: ticks 66 to 2,082
     simulated (in-fiction 09:06 day 1 to ~18:24 day 2, about 33 simulated
     hours) drove the pursuit across the real world. The pursuit plan replaced
     the character's generic plan (`vekka_scout_north` in `/api/state`) and its
     travel leg moved her from the camp out along the world roads; the needs
     cascade cost roughly three quarters of the flow minutes to
     sleep-walk-sleep cycles (a durationless background `sleeping` Activity
     runs until Energy reaches full: 425 minutes in one stretch, eats the
     budget); she reached the road cell adjacent to the Human Road once before
     resting again; and the authored stop condition then expired as written.
     The failure branch of the stop machinery is demonstrated live: the trace
     shows `pursuit vekka_scout_north failed @t2064`, the assignment unmounted
     cleanly (`active_pursuit` empty, plan `none`), and the character returned
     to generic needs behavior. The delivery branch (the `report_delivered`
     flip and Zikka's memory) was not reached in run 1.
     Live run 2 (deadline relaxed to delivery-or-abandon, fresh reset to
     tick 66): demonstrated two fail-closed paths and one demo-authoring
     hazard. The stationing hazard first: Zikka is authored sitting at the
     Chief's Pit - her load-path home of record is her containment edge
     (`player_Zikka --in--> area_chiefs_pit`, the resolution layer task-549),
     and the pit is an exposed outdoors station - and at tick 778 she died of
     exposure while the run was mid-flight. Once the recipient was dead the
     pursuit failed closed, exactly as designed: at tick 2014 the prepare
     approach failed loudly (`nothing to take for vekka_prepare_scouting_supplies
     at Armory` - the authored dagger could not resolve live because the
     backpack/dagger items are held elsewhere), the prepare plan and pursuit
     failed, `maybe_assign` restarted the scout pursuit with its reason line,
     and that pursuit failed instantly on the unresolved report recipient and
     unmounted. Run 3 authoring (content fixes, this card's lane): Zikka's
     containment edge retargeted to `area_food_storage`, the pursuit's return
     leg and `report_area` binding moved to "Food Storage", and the supplies
     list slimmed to the resolvable water skin (the packed-progress leaf kept
     in step). Run 3's outcome follows below.
     Live run 3 (same fixes, fresh reset): the recipient still died of
     exposure, now at tick 688 at Food Storage. Reason, verified against the
     records: Zikka is authored a `simulation_mode: "active"` character, and
     active characters receive no flow minutes unless their own agent completes
     a turn, so a sitting one never seeks warmth or food - she freezes on the
     shared decay rates (every character shares one decay table; the exposure
     death is not per-character tuning). Vekka had survived every prior run
     only because this card authored her `background` earlier. Run 3's other
     finding: the supply take steps still cannot resolve live ("nothing to
     take ... at Cooking Area", the water skin not at its authored station),
     so the prepare approach keeps failing - while the run's own trace also
     shows the runtime picking up an unauthored "Ground Beetle Powder", the
     needs flow inventing its own supplies. Run 4 authoring (content fixes,
     this card's lane): Zikka authored `background` and stationed (containment
     edge, current_area, and the pursuit's return leg) at the Cooking Area,
     which has fire and food; the supplies list emptied and the
     `supplies_packed` progress leaf removed from the instance (packed-bag
     evaluation is task-705's territory). Run 4 never concluded - the background driver was killed mid-loop (harness session recycle) at tick 5,491 with no stop event recorded: its last samples show Vekka at the Cooking Area sleeping under the stale run-3 prepare plan (`vekka_prepare_scouting_supplies@0` with unresolvable take steps), both leaves `pending`, Zikka alive at the Cooking Area, and ~60 wall minutes of one-tick driving in. Two facts re-established afterwards, under a controlled probe against the fresh autosave boot (tick 0): (1) the stale Player-side prepare plan is NOT a stuck world state - after boot, `maybe_assign` rebuilds the approach from the assignment and the CURRENT template (supplies already emptied), so the take steps vanish and the route plan (`vekka_scout_north`) mounts; the probe then logged two real route legs out of the camp toward the Human Road before the character went to sleep mid-route at low energy; (2) the engine's travel logs name the destination (`travelled south trail toward Human Road`), so the route leg is the plan step, not need-wandering.
Run 8 (driver-pass vitals fixture: Energy patched to 100 through the app's own `PATCH /api/players/<name>/vitals/<vital>`, Hunger/Thirst/Bladder to 0) then established the operating properties the demo kept tripping over: with Social at 50 or below (the `SOCIAL_THRESHOLD` in `engine/background_simulation._act`), the ladder's "seek company" branch takes every action minute and the assigned plan advances not one step in ~800 driven ticks - all its logged legs carry why `social:travel`, none carry the plan's own `plan:` trace vocabulary. A real authored obstacle (a cut trench with `traversal:blocked` at Road (world 11,6)) forced the BFS to re-route her through the Raven River corridor, where the need-travel ping-ponged between two adjacent road cells for ~25 ticks. Travel energy cost measured ~1.2 Energy per tick, so the camp-Human Road-camp round trip exceeds one full Energy budget without re-patching. During run 8 the recipient also wandered (Zikka: Chief's Pit, Water Source, Shaman Lair) - the delivery is a co-location completion, so the fixture re-parks her from the scenario file. No code changes were made for runs 7-8: the stall was fixture state (run 4 and 8) plus operating properties of the ladder, not a pursuit defect; the plan machinery, route legs and boot rebuild were each demonstrated live.
Run 9 (v2, driver-pass: `/api/reset` re-parks Zikka at the Cooking Area from the scenario file, vitals patched at the start and re-patched mid-walk when Energy/Social/needs decay under threshold) is the delivery attempt. The recovery lesson from the pass: `POST /api/load` is NOT a reload from disk (its body is the world dict; an empty payload replaced the live world with an empty one, wrote `unnamed.json`, and poisoned the resolve-source pointer); a two-step `/api/undo` (the empty load + the rebuilt world snapshot) restored all 27 players and the mounted pursuit intact, and `/api/reset` is the reload-from-disk call.
Run 9's outcome: killed by a real executor bug, not the fixture. After the stale prepare plan failed its Armory take and unmounted (the boot-fail chain behaving exactly as written), the route pursuit mounted at t5, took two legs out of the camp, and then one refused crossing (`the forest turns you back`, `traversal:fail` - a rolled hazard check) ended it at t6: `_run`'s travel branch returned `"failed"` on the first unsuccessful hop, which `_finish` took as a broken precondition and mounted-out the whole assignment permanently. One bad roll must not terminate an undertaking; the retry machinery (`traversal.note_refusal` plus the re-route on the next action) is what answers a refusal. Fixed in `engine/background_plans.py`: a refused action now stalls the plan (a `_stall` counter on the plan dict, reset by any successful hop) and only fails it after `_STALL_ACTIONS` = 36 consecutive refusals - a full `traversal.AVOID_MINUTES` (30 game minutes) window plus slack, since a refused action serves no time itself. Two tests added to the suite (refusal stalls, `plan` stays mounted; the window's last refusal fails loud through `pursuit:<label>:failed` + the terminal record); 40/40 pass. Run 10 (same fixture: reset, re-parked Zikka, re-topped vitals) is the next delivery attempt under the fix.

## Files

- `engine/plan_steps.py`
- `engine/pursuit_templates.py`
- `engine/background_plans.py` (2026-10-17: timing gate, recipe step routing,
  progress checks, report delivery, terminal-unmount fix)
- `engine/trigger_validator.py`, `engine/triggers/condition_tree.py`,
  `engine/triggers/evaluation.py` (the `met_character` leaf)
- `routes/library_ops.py` (2026-10-17: recipe save-gate root fix)
- `data/library/pursuit_templates/*.json` (meal v2)
- `static/js/library-browser.ts`, `templates/index.html` (the Pursuits tab)
- `tests/test_pursuit_templates.py`

## Remaining blockers

This card stays in `inprogress`. Of the six named gaps, five are closed in code
and tests as of 2026-10-17: the library tab (code and now live-verified in the
open browser, 2026-10-17, see the observed notes), the timing-gate
caller, the checkable report interaction (leaf plus runtime, authored data
updated), the meal recipe step, and the route fix (gateway way authored live
through the app's own build surface and committed into the scenario source).
Still open: the live browser session that verifies Vekka's delivery and
James's arrival at the bed through the new gateway. Vekka's backpack is carried by
another character; the supplies_packed progress is authored data this card
does not own (task-705's requirement evaluation covers supply leaves on
templates, not this assignment's packed bag). In the integrated live scenario,
hunger preempted James's plan for 12 consecutive ticks and sent him
between two road nodes; his plan index remained 0 and `activity` remained null.
The engine's survival precedence is working, but this content does not
demonstrate arrival at the bed. Do not start task-702 until task-701 is accepted;
task-702 remains blocked by task-700 and task-701.

Live-runtime findings from the live pass (2026-10-17, Kraktooth loaded with
Vekka authored `simulation_mode: "background"` in the scenario - a content
choice this card owns, mirroring james's tier, so the background sim drives the
pursuit without a live LLM): with ticks driven one at a time through
`POST /api/turn/apply`, the pursuit plan replaced the character's generic plan
(`vekka_scout_north` in `/api/state`) and its travel leg moved her out of the
camp and along the world roads; a durationless background `sleeping`
Activity runs until Energy reaches full (`activities.py` `_should_end` only
honors `duration_ticks`, and the sleep condition ends on `energy_full`), which
at the observed restore rate cost several hundred ticks of simulated night.
The first world timeskip attempt ended early on a subject interrupt
(Belne's bladder; the skip hands control back on the subject's salient
events), and per-tick salient social events around the camp made single
interrupts the norm there - noted as an operating property of
`/api/world/timeskip`, not a pursuit defect.
