---
type: task
status: todo
area: refactor
priority: medium
---

# task-713: engine/attention.py is a dead second implementation of the attended-set selector

**Filed:** 2026-10-05
**Related:** task-411,task-418,task-710

## Goal

engine/attention.py is 24.9 KB implementing AttentionBudget, AwarenessChannel, SoundChannel and TIER_NAMES. It is imported by exactly two files, both tests: tests/test_attention.py and tests/test_zones.py. Nothing in engine/, routes/ or app.py imports it.

The live implementation is engine/awareness.py (AwarenessIndex, select_attended, normalise_anchors), wired into tick_manager.attended_set() at engine/tick_manager.py:215.

This is the duplication task-411's own progress note warned about when it recommended closing 411 and 418 into one task: shipping both as written would have duplicated engine/attention.py, and the duplicate is now sitting in the tree.

It matters now because task-710 makes 'who is promoted' a live question with two plausible-looking answers in the codebase. Delete it or make it the implementation; do not leave both.

## Measured, not inferred

- `engine/attention.py` — 24,951 bytes. Defines `AwarenessChannel`, `SoundChannel`,
  `AttentionBudget`, `TIER_NAMES`.
- Importers: `tests/test_attention.py`, `tests/test_zones.py`. **Two, both tests.**
  A grep for `AttentionBudget|SoundChannel|AwarenessChannel|TIER_NAMES` across
  the repo returns hits only inside the module itself and those two tests.
- `engine/awareness.py` defines its *own* `AwarenessChannel` and `SoundChannel`
  with the same names, and is what `tick_manager.awareness()` builds.
- `zones.py:10` mentions `engine/attention.py` in a docstring — a reference, not
  a use.

The two files are not merged and neither imports the other.

## Acceptance

- [ ] One of the two is deleted, or `attention.py` is deleted outright. Both
      `AwarenessChannel` names must not survive in the codebase.
- [ ] `tests/test_attention.py` and `tests/test_zones.py` pass against the
      survivor — `test_zones.py` imports `AttentionBudget` and `TIER_NAMES`
      directly, so this test needs porting, not deleting.
- [ ] `zones.py`'s docstring reference is corrected to whichever file survives.
- [ ] Full pytest lane green afterwards (compare failure **names** against the
      `master` baseline, not counts).

## Also worth deciding here

`tick_manager.attended_set()` — the live, wired selector — currently has **no
production caller either**. `engine/awareness.py` is imported by
`tick_manager.py`, and that is the whole of its production surface.

That is fine under task-710's design, where the scope selection *is* the budget
and no cap is needed. But it should be a recorded decision rather than an
accident: either the awareness selector stays unwired until something needs
finer-than-scope granularity, or it is wired as an additional filter. Task-710's
scope resolution and this selector are not currently known to compose; if both
end up live, that composition needs its own acceptance criteria.
