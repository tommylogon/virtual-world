---
type: task
status: review
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704, task-800, task-801, task-802, task-804]
blocked_by: [task-800]
---

# task-803: Disposition value gates: traits and morality as hard exclusions

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-801-disposition-action-features-verb-score-contributions]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]], [[task-804-disposition-pick-argmax-with-a-stable-tie-break]]
<!-- deps:end -->

## What

Hard gates that REMOVE options (honest excludes theft, nonviolent excludes attack, loyal excludes betraying an ally), as distinct from weights that merely lower a score.

Adds to `engine/disposition.py`: `VALUE_GATES` (a flag -> excluded verb-classes table), plus `gated_verbs`, `is_gated` and `filter_actions`. Flags are read from the character's `traits` and an authored `morals` map. The gate table includes one real library trait (`prudish` excludes `flirt`) so a gate can fire against authored content today, alongside the illustrative moral flags.

## Why

A weight says "rather not"; a gate says "cannot". Personality must never make an impossible action *possible*, and morality is an exclusion, not a preference. So a gate is applied after the capability gates (budget, prerequisites, location) and only ever removes a candidate - it is never a score delta.

## How

Declared in `engine/disposition.py`. `_flags` reads truthy keys from `player.traits` and `player.morals`; the moral flags (`honest` / `nonviolent` / `loyal`) are authored character data rather than capability traits, while `prudish` is a real `data/library/traits/` id so that gate is reachable now. `filter_actions` subtracts only, so it can never add a verb the capability gate denied. The caller is the resolver that builds a candidate set (task-804); until that lands the functions are exercised by tests, not by a live turn.

## Steps to verify

1. Open the action menu for a character carrying `honest`, beside a stealable item.
   - expected: the steal verb is ABSENT from the menu, not present as a low-score option.
   - observed: NOT DONE as an action-menu check - the menu and candidate set are task-804 / task-702. The engine gate is proven: `filter_actions(honest, ["steal","take","look"]) == ["take","look"]`.
2. A character with no value traits, same room.
   - expected: the verb present, so the gate is trait-driven and not global.
   - observed: PASS as a mechanism - `gated_verbs(_FakePlayer()) == set()`; `filter_actions(plain, ...)` returns the list unchanged.
3. In the 🧠 Mind panel, a character's value-gated verbs are visible.
   - observed: VERIFIED 2026-10-13, live on localhost:4444. The "Disposition - what they weigh" block renders "excluded by values: flirt, bully" when `disposition.gated` is non-empty, and the "Actions - what they can choose (16, 1 excluded)" block strikes the gated verb's row (verified: with `gated: ['bully']` the "bully social.weight.bully" row is line-through). The action-menu *removal* still needs the resolver's candidate set.

## Acceptance

- [x] A gate removes the option; it is never only a score penalty (`filter_actions` drops the verb).
- [x] Gates never enable an action the capability gate denied (`filter_actions` is a pure subtraction; `test_a_gate_only_subtracts_and_never_enables`).
- [x] `tests/test_disposition.py` 26 passed; the gate still reports "35 scores across 4 decisions, no drift".

## Files

- `engine/disposition.py` (the `VALUE_GATES` table and the filter)
- `tests/test_disposition.py` (the gate tests)
