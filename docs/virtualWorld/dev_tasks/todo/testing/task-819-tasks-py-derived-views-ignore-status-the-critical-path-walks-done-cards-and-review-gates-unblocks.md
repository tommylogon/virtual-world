---
type: task
status: todo
area: testing
priority: low
wiki: "[[Developer Tooling]]"
---

# task-819: tasks.py derived views ignore status: the critical path walks done cards, and review gates unblocks

**Filed:** 2026-10-13
**Related:** task-810, task-814

## What

Two derived views in `tools/tasks.py` read the dependency DAG without regard to card status, and both mislead. (1) `_longest_path` (the critical path printed by `roadmap` and `graph`) walks *every* card, so a chain is printed whose tail links are already `done`/`review` -- for example `task-457 -> 446 -> 577 -> 578 -> 579`, where 579 is done and 577/578 are in review. (2) `next` and the per-card `unblocks N` count use `TERMINAL_STATUSES = {done, cancelled}`, so a card whose predecessor is in `review` reads as not startable though the work is built.

## Why

The roadmap is the tree's own account of what is open. A critical path that runs through `done` cards overstates the work remaining. This was noticed while reading the roadmap for the MOSIAC work, where three of five critical-path links were already built. Whether `review` should gate scheduling is a separate, deliberate question, not obviously a defect.

## How

Decide the `review` semantics explicitly, then apply in `tools/tasks.py`. Filter `_longest_path` to non-terminal cards (or stop it at the first terminal link) so the path describes open work. For `next`/`unblocks`, either add `review` to a scheduling-terminal set, or document in the docstring why it stays non-terminal (do not build on unverified work). Leave `validate` and the folder-authoritative status rule alone. Regenerate `docs/design/roadmap-computed.md`.

## Steps to verify

1. Run `python tools/tasks.py roadmap` and `python tools/tasks.py graph` before and after.
   - expected: the critical path contains no done/cancelled card; a chain whose tail is terminal no longer appears.
   - observed: TODO

## Acceptance

- The printed critical path contains no `done`/`cancelled` card.
- The intended status of `review` for scheduling is decided and either applied or documented.
- `python tools/tasks.py validate` still passes; `roadmap-computed.md` regenerates correctly.

## Files

- `tools/tasks.py`
- `tests/` (a unit test pinning the path/status rule)
