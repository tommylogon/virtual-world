---
group: Tech Debt & Testing
status: superseded
superseded_by: task-587
---
# Test Plan: 100+ Click/Verify Items — SUPERSEDED

This file was a **presence checklist**: 215 steps, each with a "Test", an
"Expected Result" and a hardcoded `✓`. It recorded no world, no write model and
no run — the summary's "225 passed" was a transcription, not a measurement, and
no run was ever stamped to a commit.

It has been superseded by **`docs/virtualWorld/testing/manual-test-plan.md`**
(task-587), which keeps every one of these steps but gives each one:

- a **phase** and a scratch world it runs in (`data/saves/<run-id>/`, never
  `data/scenarios/`),
- `pre` / `action` / `expect` / `may-write` / `evidence` fields,
- a gate (`tools/test_plan_gate.cjs`) that voids the run if `git status` is dirty
  outside the scratch world,
- named blind spots and a first run recorded honestly (not a row of `✓`).

The 215 rows live on under the same `N.M` ids so links and harnesses keep
resolving. Do not restore this checklist.
