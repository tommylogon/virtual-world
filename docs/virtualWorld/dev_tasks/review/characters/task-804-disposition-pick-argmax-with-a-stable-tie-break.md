---
type: task
status: review
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704, task-800, task-801, task-802, task-803, task-805]
blocked_by: [task-800, task-802]
---

# task-804: Disposition pick: argmax with a stable tie-break

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-801-disposition-action-features-verb-score-contributions]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]], [[task-803-disposition-value-gates-traits-and-morality-as-hard-exclusions]], [[task-805-disposition-whispers-render-the-score-registry-as-words-for-the-llm]]
<!-- deps:end -->

## What

The resolver **family**: turn a decision's scores into one action. Per task-799, a single pick rule is not enough - the three unrelated decisions resolve three ways - so this is a small set of **pick modes**, chosen by the registry's declared `combine` and `pick`:

- **argmin / argmax** - a utility summed and compared (relieve; "fled because cowardly = safety +2").
- **threshold-then-utility** - a drive must cross, then a utility (hunt / survive).
- **weighted-draw** - multiplicative weights sampled with a seed (the social pass).

`resolve(decision_name, candidates, weights=..., seed=...)` takes `(key, features)` candidates and returns an `Outcome` (winning key, combined score, mode, and the winner's top contributing scores). Deterministic: candidates sort by key first, so a tie and a seeded draw resolve the same way every run.

## Why

The soak needs a reproducible, explainable pick. Task-799 showed the choice is not one rule: relieve is a deterministic argmin, the social pass is a seeded draw. A single argmax would silently replace the social draw.

## How

In `engine/disposition.py`: `score_candidate` (declared base + character weight + action feature, per score), `_combine` (a product for `multiply`, so a `gate` score at 0.0 zeroes the whole candidate; a sum otherwise), `_thresholds_met`, and `resolve` dispatching on the decision's `pick`. The social pass's existing seeded draw in `engine/background_social.py` is the reference for the weighted-draw mode and is untouched; this is the generic form. Not yet wired into `engine/background_simulation.py` - the first live caller is the soak/pursuit layer, and until then the resolver is exercised by tests only.

## Steps to verify

1. Run one soak turn, then read the event stream.
   - expected: the chosen action is logged with its top contributing scores.
   - observed: NOT DONE - the soak wiring (`engine/background_simulation.py`) is deferred; `Outcome.contributions` is the debug read and is unit-tested, but no live turn emits it yet.
2. Repeat with the same state and seed.
   - expected: the same action both times.
   - observed: PASS - `test_weighted_draw_is_deterministic_given_a_seed` and `test_ties_break_stably_on_the_key`.
3. The character's decision weights are inspectable.
   - observed: VERIFIED 2026-10-13, live on localhost:4444 - the Mind panel's "Disposition - what they weigh" block shows the weights a pick would read (the character-side half). A per-pick *contribution* log still needs the live soak caller.

## Acceptance

- [x] The pick is deterministic given state (and seed) - candidates sorted by key, seeded draw (`resolve` tests).
- [x] The chosen action's top contributing scores can be reported - `Outcome.contributions`, largest magnitude first.
- [ ] Wired into a live caller (`engine/background_simulation.py`) - deferred; the first soak/pursuit caller lands with task-704/702. Review, not done.

## Files

- `engine/disposition.py` (`Outcome`, `score_candidate`, `resolve`)
- `tests/test_disposition.py` (the resolver tests)
- `engine/background_simulation.py` (deferred - the live caller)

## Progress (2026-10-13)

- Rewritten from "argmax" to "pick modes" per task-799's finding (the three decisions resolve three ways). Blocked on task-800 (the registry declares `combine`/`pick`) and task-802 (the weights).
