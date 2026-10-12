---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704, task-691, task-714]
blocked_by: [task-800]
---

# task-801: Disposition action features: verb -> score contributions

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

The action-side half of the score model: what each verb (and verb-on-target) contributes to each decision score.

## Why

score(action) = weights . features. Without the feature table the trait weights multiply nothing. Derived from the verb's tier and the target's tags where possible, authored explicitly where not.

## How

A table near the action tiers: verb -> {score: amount}. Targets contribute via their tags. Validate against the registry (task-800).

## Steps to verify

1. In the app, open the 🧠 Mind panel (`InspectorMindView`) for a character.
   - expected: the available actions and the decision scores each contributes are visible.
   - observed: TODO
2. The feature table names only declared scores.
   - expected: disposition_index.py --check passes.
   - observed: TODO

## Acceptance

- [ ] Every soak-relevant verb contributes to at least one registry score.
- [ ] Unknown scores are impossible (registry-checked).

## Files

- `engine/disposition.py`
- `engine/action_tiers.py`
