---
group: Triggers
---
# Warn on Empty Triggers

**Filed**: 2026-08-19
**Priority**: High
**Status**: In Review — implemented 2026-08-19 (backend validator, left-panel World Issues)

---

## Idea

Editor warning on triggers that are empty — no effects, or empty success/fail messages.

## Implemented

- `engine/trigger_validator.py` — `empty_trigger` (no effects at all) in `validate_trigger_props`; `empty_effect_message` for `message` effects with blank text.
- Surfaced in the left panel `#validation-section` via `/api/triggers/validate`.
- Tests: `TestEmptyTriggerWarnings` (no-effects + empty-message cases).

**Verified**: full suite 980 passed (+9 validator tests).

**Follow-up (2026-08-19)**: a message effect is only flagged when `message`, `success_message`, and `fail_message` are all empty — the editor stores trigger messages in `success_message`/`fail_message` (mirrored into the first effect's params; the runtime fills `message` from `success_message`, `trigger_system.py:105`). This stops false positives on triggers like the Valerius painting. Warning text now names the trigger + source node. Suite now 986 passed.

## Notes

- Authoring-time validation in the trigger editor, same pattern as the existing tag validation warnings.
- Catches triggers that silently do nothing (no effects) or produce blank narration (empty messages).
- Family of warnings: `task-305` (ways), `task-306` (this), `task-307` (mechanic tags).

## Related

- `developer ideas.md` line 13
- Trigger editor (`static/js/shared/trigger-editor.js`), `engine/trigger_validator.py`
