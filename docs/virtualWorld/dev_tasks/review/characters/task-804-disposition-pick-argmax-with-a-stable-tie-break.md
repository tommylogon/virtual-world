---
type: task
status: review
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704, task-800, task-801, task-802, task-803, task-805]
blocked_by: [task-800, task-802, task-702, task-704]
---

# task-804: Disposition pick: argmax with a stable tie-break

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]]
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

### Why the soak is not the caller (measured 2026-10-13)

`BackgroundSimulation._satisfy_needs` (`engine/background_simulation.py:451-560`+) is a **hand-ordered precedence cascade** of `if` branches (energy -> hunger -> bladder -> hygiene -> sanity -> social -> plan -> preparation), each with its own `served` set and fall-through. It never builds a candidate list and never scores one, so there is nothing to hand to `resolve(decision, candidates)`. The one scored pick in it is `_travel_to_privacy` (`:745`), an argmin of `engine.relief.score_privacy` over **reachable areas** - not over verbs - and it already works and is tested. Dropping `resolve` in would mean rewriting the cascade into candidates, which changes behaviour and belongs to the plan executor ([[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]]) / selector ([[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]]) that produce those candidates. So the resolver stays unwired until then; this is a dependency, not a gap to paper over.

## Steps to verify

1. Run one soak turn, then read the event stream.
   - expected: the chosen action is logged with its top contributing scores.
   - observed: NOT DONE - and measured 2026-10-13, the soak is not the right caller: `_satisfy_needs` is a precedence cascade, not a scored candidate list (see "Why the soak is not the caller"). `Outcome.contributions` is the debug read and is unit-tested; the first live caller is the plan executor / selector (task-702 / task-704).
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

## Progress (2026-10-13, assessment)

- Re-read `_satisfy_needs` to look for a safe live caller. There is none: it is a precedence cascade, and its one scored pick (`_travel_to_privacy`) is an argmin over areas that already works. The resolver's caller is the plan executor (task-702) / selector (task-704); `blocked_by` now names them. No code change: forcing the swap would rewrite the cascade and change behaviour.

## Browser UI and intended live verification

Intended UI home: run the three registered decision consumers (relief, hunt/survive, and a weighted choice) in the game/soak view; inspect the selected action and its contribution trace.

Current availability: the resolver has deterministic seeded selection and `Outcome.contributions`; the card explicitly defers wiring to `engine/background_simulation.py` until tasks 702/704. No live-caller integration is claimed.

Live steps when available:
1. Repeat one relief decision with the same state and seed; inspect the result and contribution detail.
   - expected: argmin/argmax chooses the same action and reports the highest-magnitude contributing scores first.
2. Run hunt/survive decisions with the required threshold below and above its boundary.
   - expected: threshold-then-utility excludes the below-threshold action and ranks eligible actions by the registered utility.
3. Run a weighted-draw decision with a fixed seed and sorted candidate keys.
   - expected: the same seed/state chooses the same candidate; changing candidate insertion order alone does not change the result.
4. Inspect the event/soak trace after background simulation invokes the resolver.
   - expected: the live outcome matches the registry-declared combine/pick mode and includes its contributions; no alternate pick implementation makes a conflicting choice.

This section is not a claim that the resolver is wired to a live caller today.
