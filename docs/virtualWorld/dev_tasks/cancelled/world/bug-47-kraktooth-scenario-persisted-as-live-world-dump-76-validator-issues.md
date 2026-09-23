---
type: bug
status: cancelled
area: world
priority: medium
---

# bug-47: Kraktooth scenario persisted as live-world dump (76 validator issues)

**Filed:** 2026-09-23
**Related:** task-316, task-408
**Status:** Superseded — folded into task-408 (Goblin scenario consolidation, dedupe,
and data integrity), which already owns this scenario's node dedupe and validator debt.
Kept for the dated re-validation evidence below rather than as separate work.

## Evidence (2026-09-23)

`python tools/validate_scenario.py --input data/scenarios/kraktooth_goblin_camp.json`
→ **76 issues**: 23 `player_*` anchor nodes missing `description`, and 53
`logic_trigger` nodes with a missing `target` and/or no incoming `triggers` edge.
The same 76 issues are present in the pre-edit backup, i.e. they are not caused by
this session's work. This contradicts task-408's 2026-09-20 progress note ("validator
went 78 issues → 0"), which suggests the trigger fixes there are not in the currently
committed file — most likely overwritten by a live-world persist (the file carries
`persist: true`).

## Acceptance

- TODO — see task-408 acceptance.
