---
type: task
status: done
area: ui
priority: medium
---

# task-386: keyboard-map

**Filed**: 2026-08-30
**Status**: Todo
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P4 — Keyboard map: Ctrl+S commit, Ctrl+K palette, Ctrl+Z undo (toolbar still works); docs + hints.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

TODO

## Why

TODO

## How

TODO

## Steps to verify

- expected: Ctrl+S commit, Ctrl+K palette, Ctrl+Z undo (typed-safe) + docs/hints.
- observed (2026-10-10): command-palette.ts:319-348 handles Ctrl+L / Ctrl+K (palette, verified live) / Ctrl+S commit / Ctrl+Z undo / Ctrl+Shift+Z redo, typed-safe; toolbar titles ('Command palette - jump anywhere (Ctrl+K)', 'Redo (Ctrl+Shift+Z)') + Patch Notes + HelpCenter reference it.

## Acceptance

- [x] keymap wired (Ctrl+S/K/Z, typed-safe). - [x] documented (toolbar titles, Patch Notes, HelpCenter).

## Files

- TODO
