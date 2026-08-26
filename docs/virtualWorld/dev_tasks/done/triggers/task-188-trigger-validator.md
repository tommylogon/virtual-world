---
id: 188
title: Trigger Validator — Broken Reference Detection + Editor Alerts
status: review
priority: high
created: 2026-08-10
updated: 2026-08-10
tags: [triggers, tooling, validator, editor, ux]
---

# Trigger Validator — Broken Reference Detection + Editor Alerts

**Status**: In Review — implemented 2026-08-10. New `engine/trigger_validator.py` (`TriggerValidator(graph, library_dir)`) + `validate_triggers()` / `validate_trigger_props()` facades + `GET /api/triggers/validate` route. Frontend: `static/js/validator-panel.js` (`window.ValidatorPanel`, auto-refresh via `appEvents` `state:updated` debounced 2 s) + validation section in left panel (`index.html`) + inline ⚠ Validate button in `InspectorTriggers.renderTriggersHTML()` (`trigger-helpers.js`). 27 tests in `tests/test_trigger_validator.py` — all pass. Suite: 814 passed, 1 skipped, 71 deselected, 13 pre-existing failures (unrelated: `TestUnifiedEffectTargeting` 8, `TestGiveItemEffect` 4, `test_way_connect_repair.py` 2 — reproduce with validator code stashed). Browser-verified live: panel shows `item_glasses_case` → `missing_effect_item` (spawns `item_professors_note`, absent from graph + library), 🔍 button opens inspector + graph focus, inline per-node validation works.

## Summary

Add a trigger validator that scans every `triggers` edge / `logic_trigger` for broken references (missing nodes, items, tags, areas; stale copies; wrong target types) and surfaces issues in the left-panel Alerts area with clickable buttons that open the offending node (inspector + graph focus).

## Problem

Triggers silently no-op when they reference nodes/items that don't exist (e.g. effects targeting a removed way, `has_tag` on a tag no node carries, item spawns whose id isn't in the graph or library). Verified real-world examples in `data/scenarios/labs.json`: `item_button_18` trigger edge points to a cached copy of `trigger_item_button 7_..._['on_use']...` whose effects target `way_task_18__door_3__locked` and `way_task_18__door_2__closed` (both missing); `item_keycard` has a `has_tag` condition on `clearance` no node has. Authors get no signal until a trigger mysteriously doesn't fire.

## Implementation

### Backend validator

- `TriggerValidator(graph, library_dir)` in `engine/trigger_validator.py`; iterates all `triggers` edges + `logic_trigger` nodes; validates conditions, effects, branches (`on_fail` / `on_success`), per-node filter (`node_id=`), severity-sorted output.
- Checks:
  - Error `dangling_trigger_edge` — edge targets missing trigger node
  - Error `trigger_edge_wrong_target_type` — target not `logic_trigger`
  - Warning `stale_trigger_copy` — trigger id embeds a node prefix (`item_`, `way_`, `area_`) different from its actual source
  - Error `missing_effect_node` — set_state / set_hidden / rename / adjust_uses / add_tag / remove_tag / set_environment / description / unlock_way target a non-existent node
  - Error/warning `missing_effect_item` — spawn_item / give_item / remove_item / consume_item target absent from graph + `data/library/items/<id>.json`
  - Warning `tag_not_in_world` — `has_tag` / `target_has_tag`
  - Warning `condition_missing_item` — `has_item` / `has_items` / `is_equipped`
  - Warning `condition_missing_node` — `state_equals`
  - Warning `teleport_missing_area`
  - Warning `unknown_trigger_type` / `unknown_condition_type` / `unknown_effect_type`
- Facades on the engine: `validate_triggers()` and `validate_trigger_props()`.

### API

- `GET /api/triggers/validate` in `routes/triggers.py` → `{"issues": [...], "count": n}`.

### Frontend

- `static/js/validator-panel.js`: `window.ValidatorPanel` with `refresh()`, `validateNode(nodeId)`, `validateNodeInline(nodeId, containerEl)`, `jumpTo(nodeId)`, `render(issues, targetEl)`. Auto-refresh on `state:updated` (2 s debounce).
- `templates/index.html`: `#validation-section` after `#alert-section` (`#validator-count`, `#validator-list`, 🔄 refresh button) + `<script src="/static/js/validator-panel.js">`.
- `static/css/style.css`: `.validation-section`, `.validator-list`, `.validator-item`, `.validator-jump`, `.validator-inline`.
- `static/js/inspector/trigger-helpers.js`: ⚠ Validate button + inline results container in `InspectorTriggers.renderTriggersHTML()`.

## Testing

- [x] Validator catches all error/warning classes — 27 tests in `tests/test_trigger_validator.py`
- [x] API endpoint returns `{"issues", "count"}` — `curl http://127.0.0.1:4444/api/triggers/validate` verified live
- [x] Panel renders count badge + severity + message + 🔍 jump button — Playwright snapshot
- [x] 🔍 opens owner node in inspector + graph focus — Playwright verified (`item_glasses_case`)
- [x] Inline ⚠ Validate shows per-node issues — Playwright verified
- [x] Real-world catch: `labs.json` stale trigger copy + missing ways; live template `item_glasses_case` → `item_professors_note`
- [ ] Confirm the 13 failing tests are pre-existing (re-run full suite after committing; validator code stashed reproduces same 13)
- [x] Full suite with changes: 814 passed, 1 skipped, 71 deselected, 13 failed (pre-existing)

## Related

- [[todo/triggers/task-168-test-triggers-in-editor|task-168: Test Triggers in the Editor]]
- [[review/triggers/task-16-dymanic_trigger_templates|task-16: Dynamic trigger templates]]
- [[review/triggers/task-167-speech-phrase-triggers|task-167: Speech phrase triggers]]
