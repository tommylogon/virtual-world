---
type: task
status: inprogress
area: graph
priority: medium
---

# task-377: duplicate-room-and-item

**Filed**: 2026-08-30
**Status**: Todo
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P3 — Duplicate room (with items/contents/triggers) and duplicate item (with contents).

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.




> 2026-08-30 hardening (live crash follow-up): the clone recursion now walks a PRE-INDEXED original container tree (never live edges — parent edges previously looked like contents and re-discovered clones forever), with a shared visited set (cycles) and a 200-node cap; duplicate pushes an undo snapshot BEFORE mutating. tests: cycle guard + snapshot tests in tests/test_duplicate.py.

**Operator verification (2026-10-10) — reopened, in progress.** Duplicating an item *works* but takes **20+ seconds** to produce the clone on the goblin camp — long enough that there is no log and no visible item, so it reads as broken. This is a performance problem, not a correctness one.

## What

TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
