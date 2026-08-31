---
type: task
status: review
area: ui
priority: medium
---

# task-367: scenario-status-chip-commit

**Filed**: 2026-08-30
**Status**: In Review — implemented 2026-08-30; chip + Commit + status API live-verified.

## What was built

- `static/js/ui/scenario-status.js` — top-bar chip `📦 <scenario> · ●` where the ●
  (dirty dot) appears only when `edit_seq != commit_seq`; chip holds **Commit** only.
- `POST /api/scenario/commit` — writes live world into the scenario source file
  (`data/scenarios/<name>.json`), resets `_commit_seq`.
- `GET /api/scenario/status` — dirty flag via edit/commit sequence compare.
- **Consolidation (same day)**: the chip previously had a second [🌀 Restart]
  button (duplicate of the toolbar Restart) — removed; toolbar keeps the only Restart.
  Chip = status + Commit only.
- Tests: `tests/test_scenario_commit.py` (5).

## Note

Original audit text mentioned "[💾 Commit] and [🌀 Restart]" — Restart stayed in the
toolbar per the two-Restart consolidation; see task-368 for the menu wording.
