---
id: 168
title: Test Triggers in the Editor (Run Button)
status: review
priority: medium
created: 2026-08-02
updated: 2026-08-05
tags: [triggers, editor, ux, tooling]
---

# Test Triggers in the Editor (Run Button)

**Status**: In Review — implemented 2026-08-05. Backend `POST /api/triggers/test` (new `routes/triggers.py`) + `TriggerSystem.test_trigger()` (dry-run reports per-condition pass/fail + would-run effects + fireable check; live-run executes effects). Editor "▶ Run Test" button + result panel in `trigger-editor.js`. Browser-verified: button renders, fires API, shows condition PASS/FAIL + dry-run outputs + fireable warning. 5 new tests; suite 507 passed, 1 skipped.

## Summary

Add a way to test triggers from the editor — a run button on each trigger that simulates the trigger firing so the author sees its conditions and effects without having to play through the scenario.

## Problem

The trigger editor (static/js/shared/trigger-editor.js) lets you build triggers but there's no way to verify them in place. Authors have to run the game, set up the situation, and trigger it manually to see if the conditions/effects are right.

## Implementation

### Editor UI

- Add a "Run" / "Test" button per trigger row (and in the trigger graph editor) — ✅ "▶ Run Test" button added to the trigger editor modal (`trigger-editor.js`); opens a result panel inline
- Opens a test panel showing: the trigger type, its conditions with current-world evaluation, and a button to execute — ✅ panel shows type, per-condition ✓/✕, PASS/FAIL summary, "Would run:" effects, and a fireable warning

### Backend test endpoint

- Add a route like `POST /api/triggers/test` that takes a trigger definition + optional context (area, item, actor) and runs it through `TriggerSystem` without committing side effects — ✅ `routes/triggers.py`, wired in `app.py`; `TriggerSystem.test_trigger()`
- Two modes:
  - **Dry run**: evaluate conditions against the live world, show pass/fail per condition, show what effects *would* fire — ✅ default mode; `side_effects` list warns about node-modifying/spawning effects
  - **Live run**: actually execute the effects (with a confirm) so the author sees the real result — ✅ `dry_run: false` executes effects through the normal pipeline
- For live runs, snapshot graph state first and offer rollback, or log clearly what changed — ⏳ dry-run is the editor default; live-run side effects are surfaced in `side_effects` (no snapshot/rollback yet — noted for later)

### Feedback

- Show pass/fail for each condition — ✅ per-condition rows
- Show the output messages the trigger would produce — ✅ "Would run:" list (dry-run) / real outputs (live)
- Show a warning if the trigger type can't fire in the current context (e.g. `on_take` needs an item) — ✅ `fireable` flag → ⚠️ warning in panel

## Files to Modify

1. `static/js/shared/trigger-editor.js` — run/test button + result panel
2. `routes/triggers.py` (or graph.py) — test endpoint
3. `engine/trigger_system.py` — expose a safe evaluate/execute helper for testing

## Testing

- [x] Run button appears on triggers in the editor — browser-verified (renders + fires API)
- [x] Dry run shows condition pass/fail without side effects — `test_dry_run_reports_conditions_and_outputs`, `test_dry_run_flags_failed_condition`
- [x] Live run executes effects and shows output — `test_live_run_executes_message_effect`
- [x] Un-fireable trigger types warn the author — `test_fireable_false_when_item_required_but_missing`
- [x] Context (speech) reaches conditions — `test_speech_context_reaches_condition`
- [ ] Works for both library item triggers and graph trigger edges — endpoint takes `item_id`; library/graph edges both flow through TriggerSystem. Live-verify edge wiring in editor when convenient.
- [x] Full suite: 507 passed, 1 skipped

## Related

- [[todo/triggers/task-153-rename-item-trigger-effect|task-153: Rename effect]]
- [[review/triggers/task-16-dymanic_trigger_templates|task-16: Dynamic trigger templates]]
