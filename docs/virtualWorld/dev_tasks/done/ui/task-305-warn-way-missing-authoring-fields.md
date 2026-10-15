---
area: ui
status: done
type: task
priority: medium
---

# Warn on Way Missing Authoring Fields

**Filed**: 2026-08-19
**Priority**: High
**Status**: In Review — implemented 2026-08-19 (backend validator, left-panel World Issues)

---

## Idea

Editor warning when a way is missing required authoring fields: cardinal direction, view-from direction, description, pass message.

## Implemented

- `engine/trigger_validator.py` — new `_validate_way_authoring()` pass: `way_missing_description`, `way_missing_pass_message`, `way_missing_cardinal`, `way_missing_view_direction` (cardinal + `visible_in_direction` checked per connection edge).
- Surfaced in the left panel `#validation-section` (renamed "Trigger Issues" → "World Issues") via `/api/triggers/validate`, with jump-to-node.
- Tests: `TestWayAuthoringWarnings` (missing-all + clean cases).

**Verified**: full suite 980 passed (+9 validator tests); smoke test confirms all four codes fire.

**Follow-up (2026-08-19)**: cardinal + view direction checks now only validate the **area→way** edges (`edge.target == node.id`). The reverse way→area "enter" edges legitimately carry only a `direction` command, so they no longer trigger false positives (`way_icy_arch`/`way_root_tunnel`). Verified against the live world: those ways clean; remaining warnings are genuine gaps on `way_bathroom_door`/`way_ice_bridge`. Suite now 986 passed.

## Notes

- Authoring-time validation in the way inspector, same pattern as the existing tag validation warnings.
- Cheap to build, and it catches real gaps — ways authored without a cardinal direction/description render poorly in the map editor's cardinal-axis layout and produce weak narrative ("the stranger at the north" relies on this data).
- Family of warnings: `task-305` (ways), `task-306` (empty triggers), `task-307` (mechanic tags).

## Related

- `developer ideas.md` line 12
- Way inspector (`static/js/inspector/way-view.js` / `way-authoring.js`), `docs/virtualWorld/World Building/Rooms & Areas.md`

## Steps to verify

- expected: way authoring warnings fire for missing description / pass message / cardinal / view direction.
- observed (2026-10-10 live, validator API): way_missing_description 1369, way_missing_view_direction 2739, way_missing_cardinal 15, way_missing_pass_message 4.

## What

TODO

## Why

TODO

## How

TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Left panel → World Issues → select a way-authoring warning;
the selected way opens in the Inspector.

Current availability: `/api/triggers/validate` returns the four way-authoring
warning codes, and the left panel surfaces them with jump-to-node. The card's
2026-10-10 live result includes genuine gaps on `way_bathroom_door` and
`way_ice_bridge`.

Live steps when available:
1. Open World Issues and select the `way_bathroom_door` warning for missing
   description; inspect the selected node in the Way Inspector.
   - expected: the warning identifies the missing field and the graph/Inspector
     focus moves to that exact way.
2. Enter its appearance description and refresh World Issues; inspect the
   remaining warnings for that way and for `way_ice_bridge`.
   - expected: only the description warning is removed; independent missing
     pass-message/cardinal/view warnings remain until their own fields are
     authored.
3. Inspect reverse way→area edges on the same examples.
   - expected: command-only return edges do not produce false cardinal or
     view-direction warnings.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
