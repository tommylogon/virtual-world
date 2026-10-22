---
type: task
status: inprogress
area: graph
priority: high
horizon: next
effort: L
wiki: "[[Character Pursuits]]"
related: [task-813, task-814, task-822, task-714]
---

# task-738: NL editor: Player-state ops + arbitrary edge types (inventory, equip, carrying/equipped/knows)

**Filed:** 2026-10-08
**Related:** task-813, task-814, task-822, task-714

<!-- deps:start -->
**Related:** [[task-813-mosiac-obligations-the-missing-letter-s-data]], [[task-814-mosiac-schedules-a-character-can-edit-themselves]], [[task-822-gimp-goal-data-reason-carrying-refs-achievement-predicates-and-auto-reached]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

Extend the NL Editor's existing staged `update_player` operation so a human can use natural language to author and revise the character-private source data that feeds MOSIAC and GIMP. At minimum, support schedules, obligations, and goal records, including GIMP motivation and intention fields. First enumerate the full persisted input set read by the MOSIAC and goal systems; expose the intended editable inputs through the same validated operation. Keep derived values such as MOSIAC scores, current attention, available choices, and goal progress as projections rather than stored fields.

The existing carrying/equipped relation support and update_player support for memories, relationships, and emotion remain in place. This extends the existing operation; it does not create a parallel character-state store or a mission graph node.

**Implemented 2026-10-22:**
- `static/js/nl-editor/tools.ts`: Extended `update_player` tool schema with `schedule`, `goals`, `obligations` properties (with full JSON Schema enums for activities, goal statuses, obligation statuses)
- `engine/nl_editor_validation.py`: Added `schedule`, `goals`, `obligations` to `PLAYER_PATCH_KEYS`; added `_schedule_issues`, `_goals_issues`, `_obligations_issues` validation functions with full vocabulary checking
- `routes/player_ops.py`: Added `schedule` handling in `handle_update_player` using `engine.schedule.normalize` (goals/obligations already handled via `engine.goals.normalize` / `normalize_obligations`)
- `routes/graph_ops.py`: Added `schedule`, `goals`, `obligations` tracking to the `applied` dict in `update_player` batch op handler
- `tests/test_nl_editor_player_ops.py`: Added 8 tests covering schedule/goals/obligations apply + validation + derived-field rejection

## Why

The NL Editor can already stage graph edits and a narrow set of Player changes, but its `update_player` whitelist excludes `schedule`, `goals`, and `obligations`. That leaves a human author unable to use the NL Editor to manage the core writable inputs shown in a character's Mind panel. The character's actual data belongs on Player and is already serialized there; the editor needs validated access to that same source.

## How

1. Trace and enumerate persisted Player and character-definition inputs consumed by `engine/mosiac.py` and `engine/goals.py`. Mark each as authorable source state or runtime-derived projection before adding fields.
2. Extend `update_player` schemas and validation for the intended writable source fields. At minimum, route schedule, goal, and obligation payloads through their existing normalizers and preserve schedule ordering, goal references, and obligation identity.
3. Reuse the current Player model and routes/player_ops.py writer path. Do not write MOSIAC's derived `M`, `I`, `A`, or `C` values, goal progress, or other projections back as authored state. Do not bypass equipment, memory, relationship, or other existing system writers.
4. Keep staged changes reviewable in the NL Editor: show the targeted character and field-level before/after values, allow the author to revise or discard the staged changes, and apply through the existing batch path.
5. Add authored scenario content with a character that has a schedule, a goal, and an obligation so the browser flow has real data to edit. Coordinate with task-814 for an agent's own schedule changes and task-813 for the obligation record contract.

## Browser UI and intended live verification

Intended UI home: Open the NL Editor tab, describe a change to a selected character's schedule, goals, or obligations, review the staged update, then Apply. Inspect the same character in Inspector > Mind to see the saved source fields and derived MOSIAC context.

Current availability: The NL Editor can stage and apply a limited `update_player` patch for memories, relationships, and emotion. It cannot currently stage schedule, goals, or obligations. The Mind panel displays those fields but does not provide NL Editor authoring for them.

Live steps when available:
1. Load the authored character fixture, open NL Editor, ask it to add or change a schedule step for that character, inspect the staged diff, and Apply.
   - expected: The diff names the intended character and schedule change; after Apply, Mind shows the updated complete schedule and the event stream records the edit.
2. Ask the NL Editor to set a goal with a motivation and intention, then add an obligation with an issuer and due condition. Review and Apply both staged changes.
   - expected: Mind shows the goal and obligation on the same character record; MOSIAC reflects the goal's motivation/intention and the obligation without a duplicate copy.
3. Ask the NL Editor to change a derived value such as current attention, MOSIAC choice, or goal progress directly.
   - expected: The editor either maps the request to a supported authoritative source field and shows that exact change in the diff, or explains that the requested projection is read-only; it never persists a duplicate projection.
4. Save and reload the scenario, reopen the character's Mind panel, and inspect the edited fields.
   - expected: The schedule, goal, and obligation round-trip on the same Player record and MOSIAC recomputes from them.

This section defines the intended browser path. It does not claim the planned fields or workflow already work.

## Steps to verify

1. Use the browser NL Editor workflow above to change the fixture character's schedule, goal motivation/intention, and obligation, reviewing the staged diff before Apply.
   - expected: The exact intended Player fields change and the Mind panel displays the updated values.
   - observed: Pending implementation.
2. Ask the NL Editor to directly set a derived MOSIAC or goal projection, and submit a malformed schedule, goal, or obligation value.
   - expected: Derived values are not persisted; malformed source data is rejected with a useful validation error before Apply.
   - observed: Pending implementation.
3. Save and reload, then run targeted tests for validation, batch application, serialization, and the existing Player writer invariants.
   - expected: Writable fields round-trip through the existing normalizers and no unrelated Player state is overwritten.
   - observed: Pending implementation.

## Acceptance

- [x] The existing NL Editor supports carrying/equipped relations and a validated update_player operation for memories, relationships, and emotion.
- [x] The complete persisted input set feeding MOSIAC and GIMP is enumerated and each field is classified as authorable source data or derived projection.
- [x] NL Editor update_player supports the intended writable character mind fields, including schedule, goals with GIMP motivation/intention, and obligations, through existing validators and normalizers.
- [x] Derived MOSIAC and goal projections cannot be persisted as duplicate authoring state (tests: test_update_player_rejects_derived_mosiac_fields, test_update_player_rejects_derived_goal_progress).
- [ ] The NL Editor shows a character-specific field-level staged diff, with revise, discard, and apply interactions before a state change is committed.
- [ ] An authored browser fixture exercises schedule, goal, and obligation edits on a real character record and proves the updated values appear in Mind.
- [x] Existing inventory, equipment, memory, relationship, and emotion updates continue to use their current source-of-truth writers (all existing tests pass).

## Files

- `static/js/nl-editor/tools.ts`
- `static/js/nl-editor/staging.ts`
- `static/js/nl-editor/ui.ts`
- `engine/nl_editor_validation.py`
- `routes/graph_ops.py`
- `routes/player_ops.py`
- `engine/schedule.py`
- `engine/goals.py`
- `engine/mosiac.py`
- `player.py`
- `engine/serialization.py`
- `static/js/inspector/mind-view.ts`
- `data or scenario fixture for character mind authoring`
- `tests/test_nl_editor_player_ops.py`
