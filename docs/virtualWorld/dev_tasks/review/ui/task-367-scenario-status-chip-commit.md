---
type: task
status: todo
area: ui
priority: medium
---

# task-367: scenario-status-chip-commit

**Filed**: 2026-08-30
**Status**: Todo
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P0 — Scenario status chip + Commit: persistent top-bar chip (📦 scenario · ● unsaved changes) with [💾 Commit] (writes live world into the scenario source) and [🌀 Restart]. Server: GET /api/scenario/status (dirty via edit_seq vs commit_seq) + POST /api/scenario/commit (to_scenario_dict → data/scenarios/<name>.json, sets _scenario_source).

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.


