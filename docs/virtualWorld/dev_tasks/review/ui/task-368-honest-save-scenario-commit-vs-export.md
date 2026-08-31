---
type: task
status: review
area: ui
priority: medium
---

# task-368: honest-save-scenario-commit-vs-export

**Filed**: 2026-08-30
**Status**: In Review — implemented 2026-08-30.

## What was built

- Menu renamed to be honest about what each action does:
  - `💾 Commit Scenario` — writes the live world into the scenario source (server-side, undo-safe).
  - `📤 Export Scenario File…` — the old download-to-file action, now clearly an export
    (world-export path, `SaveLoadView`/`WorldExport`), never confused with a save.
- Commit is also reachable from the scenario chip (task-367).
- Wire path: `POST /api/scenario/commit` (saveload.py) — `to_scenario_dict` → source file,
  no download involved.

## Note

Original audit text: "menu wording + verifying the export path". The export path is
`static/js/ui/world-export.js` (buildRangeLog / showRangeExport + file download); verified
working with a live download round-trip.
