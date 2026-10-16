---
type: task
status: todo
area: ui
priority: medium
wiki: "[[Scenario Workflows & UI Audit]]"
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

## Browser UI and intended live verification

Intended UI home: Scenario Manager modal.

Current availability: Scenario management and audit acceptance are in progress; this section defines the intended modal path.

Live steps when available:

1. Open Scenario Manager and inspect the scenario list and stats/age.
   - expected: Every scenario file appears with its current stats and age.

2. Audit a known-invalid scratch scenario and open another scenario with preview.
   - expected: Audit shows validator issues without changing the live world; preview opens the selected scenario.

3. Rename, duplicate, and delete only scratch scenarios.
   - expected: Each operation has a clear result and leaves unrelated scenarios unchanged.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
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

## Audit note (2026-10-16)

Moved from inprogress back to todo: it was not being worked. No uncommitted changes in the working tree or in any of the eight git worktrees touch this card's files, and nobody is editing it. The card itself says 'Not started (card complete; no implementation yet)'; 0 of its acceptance boxes are checked and no commit references it. static/js/ui/scenario-manager.ts already exists (last commit 2026-10-02); check what it covers before building a second manager.

## What already exists (2026-10-16)

`static/js/ui/scenario-manager.ts` (`ScenarioManager`, opened from Game > Scenario Manager, `templates/index.html:54`) already implements most of this card, so "Not started" on the card is wrong. Read from source on 2026-10-16; it was not exercised live.

- Lists every scenario from `GET /api/scenarios` with area count, character count, file size and age. Also has a name/path search and Modified / Health / Characters / Areas filters (task-598 and task-641, both done). Acceptance 1 is met in source.
- Open loads the scenario through `POST /api/load` with `persist=true` and tells the user Undo restores the previous world. There is no preview step; the task-369 import preview is not reused here. Gap.
- Audit posts the scenario file to `POST /api/import/audit` and reports the issue count by severity as a toast and a console line. Issue details are not shown in the UI. Whether the audit route is free of side effects on the live world was not checked.
- Duplicate, Rename and Delete are wired to `POST /api/scenarios/<name>/duplicate`, `POST .../rename` and `DELETE /api/scenarios/<name>` (`routes/saveload.py:869-916`). Rename uses native `prompt()` and Delete uses native `confirm()`, which task-751 plans to replace.
- Clone the current world into a new scenario is not in this module; Duplicate copies an existing file only. Other modules were not searched for a save-as path, so check before building one.
- No new storage format: met.

Related: `static/js/ui/scenario-health.ts` (task-385) lists the same files from the same endpoint, so two surfaces already sit over `/api/scenarios`.
