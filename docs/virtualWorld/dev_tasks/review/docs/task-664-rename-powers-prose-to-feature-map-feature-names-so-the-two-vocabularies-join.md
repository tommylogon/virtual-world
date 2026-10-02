---
type: task
status: review
area: docs
priority: medium
---

# task-664: Rename @powers prose to Feature Map feature names so the two vocabularies join

**Filed:** 2026-10-01
**Related:** task-663

## Goal

tools/feature_index.py joins each module's @powers against docs/virtualWorld/Feature Map.md and reports the honest result: of 156 modules, 68 name a feature and 88 name none, and 32 of the 58 features have no module naming them. The cause is a vocabulary mismatch, not absent effort - the headers are gerund phrases ('keeping and restoring your world', 'seeing and changing what a character is wearing') and the map is noun phrases ('Save / load', 'Wear / equip'). The 88 are baselined so the gate is green and ratchets. Two ways to close it: rewrite the headers to name features from the map (a 156-file sweep, mechanical but wide), or publish the feature names as a controlled vocabulary and have the map and the headers both use it. Either way the join should reach most modules, and the features nothing claims should be reviewable - a feature no module names may be a feature nobody can reach.

## Root cause found while doing it

The vocabulary mismatch was only half the problem. The matcher itself could
never join a **multi-word** feature: `_terms` splits on `/ & , and` but not on
spaces, so "Turn queue" became the single term `"turn queue"` and the test
`word.startswith("turn queue")` can never be true. Every multi-word label
("Turn queue", "The human turn", "Use / use on", "Soak lab", "Event stream", …)
was unjoinable regardless of how the header was written. That is why the filed
count was 68/88 — not just gerunds vs nouns.

## Resolution

Took the controlled-vocabulary option, in two parts:

1. **Headers name features.** The 86 `@powers` lines that named no feature now
   open with the Feature Map label(s) they enable, taken verbatim from the map
   (e.g. `@powers Turn queue — who acts next …`). Pure-infrastructure modules
   (`shared/dom-utils.js`, `world-state.js`) deliberately name none and stay
   baselined.
2. **The matcher joins phrases.** `feature_index.match` now looks for the label
   as a phrase first, then falls back to the old word-prefix match. Phrase
   matching is what makes a multi-word label joinable at all.

Measured: **155 of 157 modules now name a feature** (was 69); the features no
module names fell from 32 to **11**, listed at the bottom of the generated
`docs/design/feature-index.md` for review.

## Acceptance

- [x] `@powers` opens with Feature Map feature names on every module that
      enables a feature.
- [x] `python tools/feature_index.py --check` exits 0 (`2 known-unmapped`).
- [x] `docs/design/feature-index.md` regenerated; features with no module are
      listed explicitly.
- [x] `tests/test_feature_index.py` covers phrase matching, the term fallback,
      and that every real label joins when quoted verbatim.
- [x] The Feature Map's "Keeping this honest" note states the measured join.
