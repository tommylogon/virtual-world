---
type: task
status: review
area: gameplay
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704, task-691, task-714, task-800, task-802, task-803, task-804, task-812]
blocked_by: [task-800]
---

# task-801: Disposition action features: verb -> score contributions

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]], [[task-803-disposition-value-gates-traits-and-morality-as-hard-exclusions]], [[task-804-disposition-pick-argmax-with-a-stable-tie-break]], [[task-812-mosiac-per-character-context-assembly-m-o-s-i-a-c]]
<!-- deps:end -->

## What

The action-side half of the score model: what each verb (and verb-on-target) contributes to each decision score. `score(action) = weights . features` - without the feature table the trait weights (task-802) multiply nothing.

Adds `ACTION_FEATURES` (verb -> {declared score: contribution}) and `TARGET_FEATURES` (target tag -> declared score) to `engine/disposition.py`, plus `features_of(verb, target_tags)`. It also adds the fourth decision, **survive** - the soak's per-turn need choice - because the soak-relevant verbs (drink, eat, sleep, relieve, ...) had no decision to contribute to; none of the spike's three covered them.

The table is grounded, not invented: contributions are `1.0` ("this verb exercises the channel"; the magnitude is a live read - task-802), and the target tags are the engine's own vocabularies (`relief.RELIEF_TAGS` / `PRIVATE_TAGS`, `background_simulation.FOOD_TAGS` / `DRINK_TAGS`).

## Why

score(action) = weights . features. Without the feature table the trait weights multiply nothing. Derived from the verb's tier and the target's tags where possible, authored explicitly where not.

## How

Declared in `engine/disposition.py`, not `engine/action_tiers.py`: the feature table names registry scores, so it lives with the registry; `action_tiers.py` owns a verb's *tier*, not its decision contribution. `check_features()` validates the table (an undeclared score, or a soak verb that contributes to nothing) and is called from `check_registry()`, so both `tools/disposition_index.py --check` and the tests cover it. The `survive` thresholds are cross-checked against `engine/background_simulation.py` in the gate, exactly as the social weights are cross-checked against `background_social.py`.

## Steps to verify

1. The feature table names only declared scores.
   - expected: `python tools/disposition_index.py --check` passes.
   - observed: PASS 2026-10-13 -> "35 scores across 4 decisions, no drift".
2. In the app, open the 🧠 Mind panel for a character.
   - expected: the available actions and the decision scores each contributes are visible.
   - observed: VERIFIED 2026-10-13, live on localhost:4444. The Mind panel's collapsible "Actions - what they can choose (16)" lists each soak verb beside the score it contributes, e.g. "drink survive.utility.need_relief", "chat social.weight.chat", "go survive.utility.need_relief".

## Acceptance

- [x] Every soak-relevant verb contributes to at least one registry score (`SOAK_VERBS`; `test_every_soak_verb_contributes_to_a_declared_score`).
- [x] Unknown scores are impossible (`check_features`, folded into `check_registry`).
- [x] `tests/test_disposition.py` 13 passed (feature table + target tags + merge).
- [x] `python tools/feature_index.py --check` passes.

## Files

- `engine/disposition.py` (the `survive` decision + `ACTION_FEATURES` / `TARGET_FEATURES` / `features_of`)
- `tools/disposition_index.py` (the `survive` threshold cross-check)
- `tests/test_disposition.py` (the feature tests)
