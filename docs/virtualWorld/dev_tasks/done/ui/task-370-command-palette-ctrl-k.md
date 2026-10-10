---
type: task
status: done
area: ui
priority: medium
---

# task-370: command-palette-ctrl-k

**Filed**: 2026-08-30
**Status**: Todo
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P1 — Command palette (Ctrl+K): fuzzy search across graph nodes (jump+focus), menu actions, panels/tabs. Single index built from graph + static action table.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## Steps to verify

- expected: Ctrl+K opens a fuzzy palette over graph nodes, actions and panels.
- observed (2026-10-10 live): Ctrl+K opens input[placeholder='Jump to a node...']; typing 'armory' lists 'Armory area . area_armory_bhg4 . tags: interior, cave, goblin'.

## Acceptance

- [x] Ctrl+K opens the palette; fuzzy search over graph nodes returns results; Enter runs the top hit (verified live 2026-10-10).

## What

TODO

## Why

TODO

## How

TODO

## Files

- TODO
