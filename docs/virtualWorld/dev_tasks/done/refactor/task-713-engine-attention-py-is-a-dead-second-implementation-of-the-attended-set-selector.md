---
type: task
status: done
area: refactor
priority: medium
---

# task-713: engine/attention.py is a dead second implementation of the attended-set selector

**Filed:** 2026-10-05
**Related:** task-411,task-418,task-710

## What

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

- [x] `attention.py` is deleted outright. The duplicate `AwarenessChannel` /
      `SoundChannel` names go with it; only `engine/awareness.py`'s survive.
- [x] Tests handled. **Deviation from this card, on the user's explicit
      instruction (2026-10-12):** `tests/test_attention.py` was deleted and the
      five `AttentionBudget` tests were removed from `tests/test_zones.py` rather
      than ported. The user rejects the fidelity-tier model outright ("promotion
      is per scope, not … this"), so its tests are not a behaviour worth keeping.
      `test_zones.py` keeps its 19 zone tests, green.
- [x] `zones.py`'s docstring reference is corrected (now "scope-driven").
- [x] Affected lane green: `tests/test_zones.py` 19 passed; `import app` clean.
- [ ] Full pytest lane — not run here (targeted lane only); the deletion has no
      production surface, so a full run should match the `master` baseline by
      failure **name**.

## Resolution (2026-10-12)

Deleted `engine/attention.py` (427 lines) and `tests/test_attention.py`; removed
the import and the five `AttentionBudget` / `TIER_NAMES` tests from
`tests/test_zones.py`; corrected the stale `engine/attention.py` reference in
`engine/zones.py`'s docstring. `engine/awareness.py` survives — it is the one
`tick_manager.awareness()` builds — but stays **unwired** (see below).

The user also rejected the whole model this file implemented: anchors + a
hop/sound radius + a global `cap` of 8 + hysteresis. Fidelity promotion is
**scope-driven** (task-710) — the loaded scope *is* the boundary and no cap is
needed. So `engine/awareness.py` / `tick_manager.attended_set()` are **not** to
be wired as-is; any finer-than-scope filter must reconcile with task-710 rather
than sit beside it. task-411 and task-418 (its authors) should be retracted.


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

## Why

Two implementations of "who is attended" in one tree, neither importing the
other, is two sources of truth for one question — the duplication task-411's own
note warned about. One had to go, and it is the one nothing ran.

## How

`attention.py` deleted; `awareness.py` kept as the single `AwarenessChannel`
family. The five `AttentionBudget` tests removed with it (they tested the deleted
module, not a surviving behaviour). Doc reference in `zones.py` corrected.

## Steps to verify

1. `python -m pytest tests/test_zones.py`
   - expected: zone tests pass, no attention import.
   - observed: 19 passed.
2. `python -c "import app"`
   - expected: clean import (nothing imports `engine.attention`).
   - observed: app imports OK.
3. grep `AttentionBudget|engine\.attention` across the repo.
   - expected: no live hits (only this card's own history text).
   - observed: none.

## Files

- `engine/attention.py` — deleted.
- `tests/test_attention.py` — deleted.
- `tests/test_zones.py` — attention import + five tests removed.
- `engine/zones.py` — docstring reference corrected.
