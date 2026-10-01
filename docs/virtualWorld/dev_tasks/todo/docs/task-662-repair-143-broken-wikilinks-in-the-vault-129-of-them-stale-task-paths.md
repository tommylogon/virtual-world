---
type: task
status: todo
area: docs
priority: medium
---

# task-662: Repair 143 broken wikilinks in the vault, 129 of them stale task paths

**Filed:** 2026-10-01
**Related:** task-576, task-578

## Goal

Measured across all 597 [[wikilinks]] in docs/virtualWorld: 143 distinct targets do not resolve, in 74 files. 129 point at dev_task files whose path went stale when tools/tasks.py move relocated them between status folders - the tool renames on disk but does not rewrite inbound links, so every move silently rots the notes that cited the task. 11 point at prose notes that do not exist, mostly a missing folder prefix (Temperature/* are at Environment/Temperature/*) plus three genuinely absent notes (Characters/Equipment Loadouts, UI & Settings/Inspector, World Building/Item System). Two ways to fix: make tools/tasks.py move rewrite inbound [[...]] links, or link tasks by stable id rather than by status-folder path. Then add a broken-link check beside tools/tasks.py validate so this cannot rot again.

## Acceptance

- TODO
