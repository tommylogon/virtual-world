---
type: task
status: todo
area: ui
priority: medium
---

# task-443: Validator mismatch recalibration, info section, and mark-as-intended

**Filed:** 2026-09-21
**Supersedes:** the unimplemented residuals of task-393 (the triage mechanics shipped; that task is closed)
**Related:** task-393 (design sections E/F), task-324 (domain tags — feeds `mechanical_tag_missing_props`)

## Goal

Finish the three pieces of the validator triage panel that were specified but never
built, so the mansion run's noise floor drops.

## What is missing (verified 2026-09-21)

1. **`library_mismatch` recalibration — not done, and task-393's claim about it was false.**
   The panel was supposed to fire `library_mismatch` only on **mechanical** field drift
   (vitals / triggers / actions / uses) and not on `light_level` / `contents`, because
   instance divergence on those is the *normal* authoring flow. It still includes them:
   `LIBRARY_SYNC_PROPS` (`engine/trigger_validator.py:147-151`) carries `light_level`,
   `target_temperature`, `heating_rate`, `contents` and `aliases`; the severity is still
   `warning` (`:728`); and `tests/test_trigger_validator.py:428-439` asserts a
   `light_level` mismatch **is** reported. Note `DEFAULTED_MECHANICAL_DEFAULTS`
   (`:135-139`) already declares the first three as engine-defaulted → they belong with
   `mechanical_tag_missing_props` (info), not `library_mismatch` (warning).
2. **No "mark instance as intended" action.** Task-393 design section E calls for batch
   "mark instance as intended" (set an explicit override) rather than resync. No such
   action exists anywhere — no route, no property, no UI.
3. **No default-collapsed `info` section.** Grouping sorts by worst severity
   (`static/js/validator-panel.js:293-300`) but info rows render inline.

Also owed: the **manual browser pass** task-393 never had (grouping UI, scroll,
dismiss-until-touched persistence across reload).

## Design notes

- **Recalibrate by moving props, not by loosening the check.** Keep `library_mismatch`
  for the props where divergence is a real bug; route `light_level` /
  `target_temperature` / `heating_rate` to the existing `mechanical_tag_missing_props`
  (info) path, and decide `contents` / `aliases` explicitly (they are structural, so
  likely stay — but then the message should say why).
- **Mark-as-intended is a node override**, not a library edit: a property on the placed
  node that suppresses its own mismatch until the node is edited again — the same
  dismiss-until-edited shape `ignored_issues` / `_ignored_at` already uses
  (`engine/trigger_validator.py:184-219`). Reuse it rather than inventing a second
  mechanism.
- **The info section is grouping, not filtering** — it must not hide info rows from the
  count in the pinned header.

## Acceptance

- A mansion-style run's ~40 `library_mismatch` warnings on trivial fields fall to ~0,
  and no real mechanical drift is lost (a vitals/uses/actions mismatch still reports as
  a warning).
- "Mark instance as intended" suppresses a mismatch on that node only, survives reload,
  and expires when the node is edited after the mark.
- Info rows sit in a default-collapsed section; the pinned count still reflects them.
- Manual browser pass recorded in this file (grouping, scroll, dismissal persistence).
- `python -m pytest tests/ -q -k "not mcp and not emote"` green, with
  `tests/test_trigger_validator.py` updated for the recalibration.

## Non-goals

- The triage mechanics themselves (grouping, scroll, empty-trigger collapse, dismiss,
  fix-all, progress bar) — those shipped with task-393.
- Changing the derived-progress definition — task-393 settled it on the shipped
  formula; see that task's Outcome block.
