---
type: task
status: todo
area: ui
priority: medium
---

# task-371: undo-history-dropdown-labels

**Filed**: 2026-08-30
**Status**: Todo
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P1 — Undo history dropdown: expose the 10-deep undo stack with labels ('before: reset', 'before: loaded X'); push sites add short labels; click = restore.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.




> 2026-08-30 follow-up: per-edit undo snapshots — every graph/player/build mutation now pushes a labeled history entry (edited node <id> / graph edit / character edit…) in the after_request hook (bug fix: minor edits never showed in history). test: test_graph_edit_pushes_labeled_snapshot.
