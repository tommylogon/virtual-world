---
type: task
status: inprogress
area: ui
priority: medium
---

# task-385: scenario-health-dashboard

**Filed**: 2026-08-30
**Status**: Not started (card complete; no implementation yet).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P4 — Scenario health dashboard: per-file audit reports (issues count by severity) for every scenario.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

A dashboard listing every scenario file with an issue count by severity
("3 high, 1 block"), produced by running the validator against a fresh load of
each file.

## Why

Audit P4 #19: the Issues panel validates the LIVE world, not the scenario files,
so there is no offline overview of which scenarios are broken. Companion to the
Scenario Manager (task-374) and the import audit (task-375).

## How

- For each `data/scenarios/*.json`, load into a throwaway
  `VirtualWorld().load_from_dict(...)` and run `TriggerValidator` — the same
  pass as task-374's Audit and task-375. Safe: no side effects beyond the
  object.
- Render a table: file, counts by severity; click a row for the issue details.
- Reuse the validator; no live-world mutation; no new storage.

## Steps to verify

1. Open the dashboard.
   - expected: every scenario file listed with issue counts by severity.
   - observed: TODO
2. Point it at a known-bad file.
   - expected: non-zero counts matching the validator.
   - observed: TODO
3. Confirm the live world is unchanged.
   - expected: the dashboard run mutates nothing.
   - observed: TODO

## Acceptance

- [ ] Every scenario file listed with severity counts.
- [ ] Validator runs on throwaway loads; no live-world mutation.
- [ ] Clicking a row shows the issue details.
- [ ] No new storage.

## Files

- `routes/` — validator route (reuse `TriggerValidator`).
- `static/js/ui/` — the dashboard (new).
- `templates/index.html`.
- `tests/`.
