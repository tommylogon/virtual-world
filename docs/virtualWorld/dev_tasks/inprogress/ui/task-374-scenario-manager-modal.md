---
type: task
status: inprogress
area: ui
priority: medium
---

# task-374: scenario-manager-modal

**Filed**: 2026-08-30
**Status**: Not started (card complete; no implementation yet).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P2 — Scenario Manager modal: list data/scenarios/* (stats, age), open with preview, Audit (validator on throwaway load), rename/duplicate/delete, 'Clone current world into new scenario'.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

A Scenario Manager modal over `data/scenarios/*`: list every scenario file with
stats (rooms / players / ways / items, file size, age); open one with the import
preview (task-369); run the validator against a fresh load to report issues
offline; rename / duplicate / delete; and "Clone current world into new
scenario".

## Why

Audit P2 #8: the scenario source files under `data/scenarios/` are invisible
from the GUI. You cannot see which scenarios exist, how big or old they are, or
whether they are healthy, and there is no clone. Together with the health
dashboard (task-385) and the import audit (task-375), this is the maintenance
surface over the scenario library.

## How

- List route: read `data/scenarios/*.json`, `stat` for size + mtime, and count
  rooms / players / ways / items from the file (or via a throwaway
  `VirtualWorld().load_from_dict(...)`).
- Open-with-preview reuses the task-369 import preview dialog; Apply stays
  undo-safe.
- Audit reuses `TriggerValidator` on a throwaway load — the same pass as
  task-369 / task-375 — so it has no side effects on the live world.
- Rename / duplicate / delete are file operations on the directory.
- "Clone current world" writes `to_scenario_dict()` of the live world as a new
  scenario file (the same serialization `/api/load` uses); undo-safe where it
  touches the live world.
- No new storage format.

## Steps to verify

1. Open the Scenario Manager.
   - expected: every file in `data/scenarios/` listed with stats and age.
   - observed: TODO
2. Run Audit on one file.
   - expected: issue counts by severity, from a fresh load, without mutating the live world.
   - observed: TODO
3. Open one with preview.
   - expected: the task-369 preview dialog; Apply is undo-safe.
   - observed: TODO
4. Rename, then duplicate, then delete a scenario.
   - expected: the directory reflects each change; the renamed/duplicated file opens.
   - observed: TODO
5. Clone current world.
   - expected: a new scenario file holding the live world.
   - observed: TODO

## Acceptance

- [ ] Lists every `data/scenarios/*` with stats + age.
- [ ] Open-with-preview (reuses task-369) and Audit (validator on a throwaway load).
- [ ] Rename / duplicate / delete operate on the files.
- [ ] Clone current world into a new scenario.
- [ ] No new storage format; Audit has no side effects on the live world.

## Files

- `routes/saveload.py` — list / stats / audit / rename / duplicate / delete.
- `static/js/ui/` — the modal (new).
- `templates/index.html`.
- `tests/`.
