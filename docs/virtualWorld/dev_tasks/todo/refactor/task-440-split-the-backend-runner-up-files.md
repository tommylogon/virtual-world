---
type: task
status: todo
area: refactor
priority: low
---

# task-440: Split the backend runner-up files

**Filed:** 2026-09-21
**Supersedes:** task-314's backend scope (which was measured 2026-09-21 and is now closed)
**Related:** task-83 (code readability), task-218 (the module-per-concern shape this follows)

## What

Extract focused modules from the backend files that outgrew single-file ergonomics.
**One file per commit, no behaviour change** — extraction only, public imports and APIs
stable, suite green after each.

## Measured targets (2026-09-21)

| File | Lines | Suggested seam |
|------|------:|----------------|
| `routes/graph_ops.py` | 1355 | second pass: split by operation family (node CRUD / edges / batch / import-export) |
| `routes/action_handlers.py` | 1301 | second pass: split by verb family |
| `engine/tick_manager.py` | 1101 | extract the tick phases (vitals / environment propagation / triggers / activities) from the orchestrator |
| `engine/movement.py` | 1098 | split traversal rules from area/way construction |
| `engine/traits.py` | 1096 | split the definition catalog from event dispatch |
| `routes/library_ops.py` | 1084 | second pass |
| `engine/matching.py` | 697 | lower priority — resolve only if it keeps growing |
| `engine/equipment.py` | 754 | lower priority |
| `engine/trigger_validator.py` | 821 | lower priority (also touched by task-393) |

Also carried over from task-314's wave reports: `triggers/testing.py` duplicates the
template-context block from `triggers/execution.py` — de-duplicate while splitting.

**Tracked but not to split:** `engine/serialization.py` (509) already imports
`serialization_template` + `serialization_legacy`; `engine/player_conditions.py` (841)
was already extracted from `player.py`.

## How

1. **One file at a time.** Start with the smallest target that has a clean seam, as the
   proof of pattern, then move up. Do not batch.
2. **No behaviour change.** Extraction only. Keep public imports/API stable, move public
   API re-exports up to the host module.
3. **Record what moved** in the task file as a table (module → lines → what moved), the
   shape task-314's wave-1 table used.
4. Verify per extraction: `python -m pytest tests/ -q -k "not mcp and not emote"`.

## Acceptance

- Each split lands with the host file's line count materially reduced and the package
  existing, verified by measuring both.
- No test file changes required beyond `mock.patch` targets that moved (record them).
- The suite stays green per extraction.

## Non-goals

- Behaviour changes, renames of public APIs, or architectural redesign.
- Chasing a line-count target — a file that is cohesive at 900 lines stays 900 lines.
- The frontend/JS and test splits (task-441).

## Why

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Not applicable — this is a one-file-at-a-time Python module extraction with an explicit no-behavior-change contract; no new browser surface is intended.

Current availability: the task requires smaller host modules while keeping public imports/APIs stable. The extraction sequence is not claimed as complete.

Why no browser UI: a screen interaction cannot establish that backend module boundaries changed without changing the public API or behavior; the proof belongs to imports, focused regression tests, and the measured source diff.

Alternative verification steps:
1. Before and after each extraction, record the host file's line count and inspect the new module's exported functions and imports.
   - expected: the host's line count is materially lower, the extracted concern has one owner, and public import paths remain stable.
2. Run the focused test module(s) that exercise the extracted behavior after each one-file split.
   - expected: the same behavior passes after extraction; any changed `mock.patch` target is recorded explicitly.
3. Import the application package and the extracted module in a clean process.
   - expected: imports have no cycle or import-time side effect and the package still exposes the stable public API.

This section is not a claim that planned UI exists or works today.
