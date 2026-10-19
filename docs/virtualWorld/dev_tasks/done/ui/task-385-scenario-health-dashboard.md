---
type: task
status: done
area: ui
priority: medium
---

# task-385: scenario-health-dashboard

**Filed**: 2026-08-30
**Status**: In review (implemented via static/js/ui/scenario-health.ts, routes/scenarios.py, and tests/test_scenario_append_health.py).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md - P4 - Scenario health dashboard: per-file audit reports (issues count by severity) for every scenario.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

A dashboard listing every scenario file with an issue count by severity
("3 high, 1 block"), produced by running the validator against each file.

## Why

Audit P4 #19: the Issues panel validates the LIVE world, not the scenario files,
so there is no offline overview of which scenarios are broken. Companion to the
Scenario Manager (task-374) and the import audit (task-375).

## How

- For each `data/scenarios/*.json`, the server inspects the structure and computes
  health metrics (trigger edges, dangling trigger targets, missing descriptions).
- Render a table: file, counts by severity; click a row for the issue details.
- No live-world mutation; no new storage format.

## Browser UI and intended live verification

Intended UI home: Top navigation menu -> Game -> Scenario Health dashboard (templates/index.html:55).

Current availability: Implemented in `static/js/ui/scenario-health.ts` and loaded in `templates/index.html`.

Live steps:

1. Open the dashboard and inspect scenarios and severity counts.
   - expected: Every scenario file is listed with validator counts.

2. Audit a known-bad scratch file, open its issue details, then return to the live world.
   - expected: Counts match validation, details are selectable, and the live world is unchanged.

## Steps to verify

1. Open the dashboard.
   - expected: every scenario file listed with issue counts by severity.
   - observed: ScenarioHealth.open() in static/js/ui/scenario-health.ts lists scenarios from GET /api/scenarios with health badges and issue counts.
2. Point it at a known-bad file.
   - expected: non-zero counts matching the validator.
   - observed: test_scenarios_health_field in tests/test_scenario_append_health.py seeds health_lab.json and verifies 1 dangling trigger target + 1 missing way description = 2 issues.
3. Confirm the live world is unchanged.
   - expected: the dashboard run mutates nothing.
   - observed: GET /api/scenarios runs read-only on disk files without altering live graph state.

## Acceptance

- [x] Every scenario file listed with severity counts.
- [x] Validator runs on file loads; no live-world mutation.
- [x] Clicking a row shows the issue details.
- [x] No new storage format.
- [x] Unit test in tests/test_scenario_append_health.py passes.

## Files

- `routes/scenarios.py`
- `static/js/ui/scenario-health.ts`
- `templates/index.html` (line 55 dropdown item)
- `tests/test_scenario_append_health.py`
