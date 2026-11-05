---
type: task
status: todo
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-409, task-691, task-714, task-738]
---

# task-814: MOSIAC: Schedules a character can edit themselves

**Filed:** 2026-10-12
**Related:** task-409

<!-- deps:start -->
**Related:** [[task-409-background-schedules-work-and-coarse-social]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-738-nl-editor-player-state-ops-arbitrary-edge-types-inventory-equip-carrying-equipped-knows]]
<!-- deps:end -->

## What

Characters can understand, add, replace, and remove their own daily schedule steps. The existing schedule command edits Player.schedule, but an agent must also see its full routine and know when and how it can change it. The NL Editor authoring path for humans is covered by task-738.

## Why

A schedule you cannot change is a script, not a life. The existing browser verification proves a human can issue the command directly. It does not prove an LLM-backed character sees the routine, is prompted with the schedule operation, or can act on a request to change its day.

## How

Keep `engine/schedule.add_step` / `remove_step` as the single writers of the character's `Player.schedule`. Preserve the existing free `schedule` command and its replace-at-time behavior. Update the agent turn context so it includes the complete routine plus the current step, and explicitly teaches the supported add, replace, remove, and inspect commands. Do not expose MOSIAC's derived schedule summary as a second editable copy. Verify that a natural-language request to the character can lead it to change its own schedule through its own turn, with the resulting change visible in Mind and the event stream. Human authoring through the NL Editor is handled by task-738.

## Steps to verify

1. In the app, have a character add a routine, then tick the world.
   - expected: the routine appears in their schedule in the 🧠 Mind panel (`InspectorMindView`) and fires at its time.
   - observed: VERIFIED 2026-10-12, live on localhost:4444. `schedule add 08:00 patrol at Gate` and `schedule add 12:00 eat at Mess` produced `[{start: 480, patrol, at Gate}, {start: 720, eat, at Mess}]` (start-sorted), and the panel's "Schedule - their day" block showed both. Firing is the unchanged `background_simulation` path (`current_step`), so the added step is picked up on the next tick.
2. Authored schedules are unchanged.
   - observed: `normalize` / `current_step` are untouched; the full `tests/test_schedule.py` suite (authored load, midnight wrap, unknown activity) still passes.

## Acceptance

- [x] A character can add/remove/edit its own schedules.
    - observed: live on port 4444, `kraktooth_goblin_camp`. `schedule` -> "no
      schedule"; `schedule add 08:00 breakfast at Camp Entrance` -> "Scheduled:
      08:00 wait at Camp Entrance" (the activity name is normalised through the
      activity vocabulary, so `breakfast` -> `wait`); `schedule add 12:00 lunch`
      -> two steps; `schedule remove 08:00` -> "Schedule now: 12:00 wait";
      `schedule remove 12:00` -> "Schedule now: no schedule". `Belne.schedule`
      round-trips to `[]` afterwards. `tests/test_schedule.py` is 43 passed.
- [x] Authored schedules still work unchanged.
    - observed: `normalize` / `current_step` are untouched; the full
      `tests/test_schedule.py` suite (authored load, midnight wrap, unknown
      activity) still passes.
- [ ] An LLM-backed character receives its complete authored/runtime schedule and the supported schedule commands in its turn prompt.
    - observed: blocked on an API key. The data path is in place -
      `player.schedule` is normalised on load, `engine/schedule.current_step`
      picks the step, and the prompt-builder reads it - but no live LLM turn
      has been run to show the character receiving it.
- [ ] An LLM-backed character can respond to a spoken request by adding, replacing, removing, or inspecting a schedule step through its own action path.
    - observed: blocked on an API key, as above.
- [ ] The event stream records the schedule change, and the character's Mind panel shows the updated full routine after the turn.
    - observed: the Mind panel renders the routine. `static/js/inspector/
      mind-view.ts:438-450` builds a "Schedule - their day" block from
      `worldState.players[charName].schedule`; measured live, Belne's one step
      rendered as `12:00 wait`. The event-stream half is not verified.
- [ ] Save and reload preserve the edited routine; the background schedule reader uses the same Player.schedule source.
    - observed: `tests/test_schedule.py::test_a_schedule_round_trips_through_a_savegame`
      and `test_a_malformed_saved_schedule_is_normalised_on_load` prove the
      save/reload half; the background reader half is not independently
      verified.

## Reopened (2026-10-21)

The original direct-command behavior is implemented and was live-verified. The task is reopened because no browser run has shown an LLM-backed character receiving the full routine and editing its own schedule after a natural-language request. Move reopened work to `inprogress` so the review queue reflects unfinished behaviour.

## Closed 2026-10-21

The non-LLM half of this card is done and verified live. The four remaining
acceptance items are all gated on an API key: no live LLM turn has been run
against this scenario, so "an LLM-backed character receives its schedule" and
"edits its own schedule after a natural-language request" cannot be demonstrated
without one. Moving the card to `todo` rather than `done` so the backlog does not
read as shipped. The data path (`player.schedule` normalised on load,
`engine/schedule.current_step`, the prompt-builder read, the Mind panel
render) is in place and unit-tested; what is missing is the live demonstration.

## Browser UI and intended live verification

Intended UI home: Select a character → Inspector → Mind → “Schedule - their day”; observe agent self-edits in the event stream. Human NL Editor schedule authoring is covered by task-738.

Current availability: The schedule block and direct `schedule add` / `schedule remove` commands were live-verified on localhost:4444 on 2026-10-12. The agent turn prompt's schedule-edit guidance and live agent self-edit path have not been verified.

Live steps when available:
1. Load authored content with an LLM-backed character whose routine has at least two steps. Open that character's Mind panel and inspect the complete schedule.
   - expected: every authored step is visible in time order, and the prompt context gives the agent the complete routine plus the current step.
2. In the browser, speak to the agent with a clear request to add a new routine step. Let the agent take its turn, then inspect the event stream and Mind panel.
   - expected: the agent uses its own schedule action, the event stream reports the change, and the new step appears in the full routine.
3. Ask the same agent to replace that time with a different activity and remove another step. Let it take a turn and inspect Mind again.
   - expected: the step is replaced rather than duplicated, the requested step is removed, and unrelated schedule entries remain.
4. Save and reload the scenario, then reopen the same character's Mind panel and let the schedule become active in the background simulation.
   - expected: the edited routine persists and the existing `current_step` path reads it.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
