---
type: task
status: todo
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704]
blocked_by: [task-800, task-802]
---

# task-804: Disposition pick: argmax with a stable tie-break

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]]
<!-- deps:end -->

## What

The resolver: score every surviving candidate and pick the maximum, with a deterministic tie-break, and an optional seeded jitter for variety.

## Why

The soak needs a reproducible, explainable pick ('fled because cowardly = safety +2'). This is the function that turns the scores into one action.

## How

argmax over the gated candidate set; tie-break by a stable key; a seeded jitter can perturb scores without breaking reproducibility.

## Steps to verify

1. Run one soak turn, then read the event stream.
   - expected: the chosen action is logged with its top contributing scores.
   - observed: TODO
2. Repeat with the same state and seed.
   - expected: the same action both times.
   - observed: TODO

## Acceptance

- [ ] The pick is deterministic given state (and seed).
- [ ] The chosen action's top contributing scores can be reported for debugging.

## Files

- `engine/disposition.py`
- `engine/background_simulation.py`
