---
type: task
status: review
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

- [x] Trivial-field `library_mismatch` warnings fall sharply: in the live
  mansion run, 23 of 30 `library_mismatch` rows became **info** and only 7
  remain warnings (identity/structural/mechanical drift). No real mechanical
  drift is lost — `actions`/`uses` drift still warns (new test
  `test_actions_drift_still_warns`).
- [x] "Mark instance as intended" suppresses a mismatch on that node only,
  survives reload, and expires when the node is edited after the mark — it
  reuses the shipped `ignored_issues` / `_ignored_at` mechanism via
  `/api/triggers/ignore` (no second mechanism). The validator's expiry test
  already exists.
- [x] Info rows sit in a default-collapsed `info` section; the pinned header
  count still reflects them (`85 (2 err · 21 warn)` with 63 info included).
- [x] Manual browser pass recorded (below).
- [x] `tests/test_trigger_validator.py` updated for the recalibration; targeted
  suite green.

## Recalibration decision (`engine/trigger_validator.py`)

Split `LIBRARY_SYNC_PROPS` drift into three buckets:

- **warning `library_mismatch`** — `name`, `tags`, `actions`, `uses`, `weight`,
  `equip_slots`; the message says "mechanical fields determine behaviour" when
  `actions`/`uses` differ, else "these change what the item is".
- **info `mechanical_tag_missing_props`** — `light_level`, `target_temperature`,
  `heating_rate` (engine defaults from `DEFAULTED_MECHANICAL_DEFAULTS`); the
  existing ⚙ quick-fix sets them, so the info row is actionable.
- **info `library_mismatch`** — `current_state`, `contents`, `description`,
  `aliases`: runtime/per-instance state or free text, which is exactly what an
  instance is for. Decided explicitly (see `LIBRARY_MISMATCH_TRIVIAL_PROPS`).

## Verification (2026-10-02)

Engine:

```
python -m pytest tests/test_trigger_validator.py -q -> 51 passed
  new: test_engine_defaulted_drift_alone_is_info, test_actions_drift_still_warns,
       test_runtime_state_drift_is_info_not_warning; test_library_mismatch_detected
       updated (name warns, light_level is info).
```

Live browser (`VW_PORT=4463`, Playwright; real tab click `ui.switchLeftTab('issues')`):

```
PANEL countText "86 (2 err · 21 warn)"; 76 groups; 32 info sections;
      infoOpenByDefault all false; 31 "Mark this instance as intended" buttons.
group expanded -> nested "↳ N info notes" stays collapsed; opening it shows the
      individual info rows.
click ✓ on a library_mismatch node -> library_mismatch 31 -> 30, total 86 -> 85;
reload -> still 30/85 (persisted on the node).
Severity split after recalibration: library_mismatch {warning: 7, info: 23}.
```

Screenshots: `review-verify/443-validator-top.png`,
`review-verify/443-info-section.png` (collapsed info sub-section),
`review-verify/443-info-open.png` (info rows expanded).

## Files

- `engine/trigger_validator.py` — `LIBRARY_MISMATCH_TRIVIAL_PROPS`,
  `LIBRARY_MECHANICAL_PROPS`, split `_validate_library_sync`.
- `static/js/validator-panel.js` — `_infoSection` (default-collapsed), group
  split, ✓ "mark as intended" for library_mismatch.
- `tests/test_trigger_validator.py`.


## Non-goals

- The triage mechanics themselves (grouping, scroll, empty-trigger collapse, dismiss,
  fix-all, progress bar) — those shipped with task-393.
- Changing the derived-progress definition — task-393 settled it on the shipped
  formula; see that task's Outcome block.
