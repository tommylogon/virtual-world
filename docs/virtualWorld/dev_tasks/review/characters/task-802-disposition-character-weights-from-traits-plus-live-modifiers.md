---
type: task
status: review
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704, task-691, task-714, task-800, task-801, task-803, task-804, task-805, task-806]
blocked_by: [task-800]
---

# task-802: Disposition character weights from traits, plus live modifiers

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-801-disposition-action-features-verb-score-contributions]], [[task-803-disposition-value-gates-traits-and-morality-as-hard-exclusions]], [[task-804-disposition-pick-argmax-with-a-stable-tie-break]], [[task-805-disposition-whispers-render-the-score-registry-as-words-for-the-llm]], [[task-806-split-traits-capabilities-from-personality-decision-dials]]
<!-- deps:end -->

## What

The character-side half of the score model: the `weights` in `score(action) = weights . features`. A character's weights derive from its traits - authored once, not per character - plus live modifiers read from state, which is how fear, hunger, loyalty and trauma reach the score without a special system.

Adds to `engine/disposition.py`: `TRAIT_MODIFIERS` (a real trait id -> declared score coefficient table), `EMOTION_TILTS`, `NEED_THRESHOLDS`, and the readers `trait_weights`, `emotion_weights`, `need_weights`, `relationship_weights`, `memory_weights`, `live_weights` and `character_weights`. It also declares `attention.salience.remembered` (a pressing need or a memory naming the target raises the decision's profile) and folds it into the `survive` decision.

## Why

A character's numbers must be its traits, authored once - not hand-authored per character, which is a second copy of the prose. Live modifiers are how fear, hunger, loyalty and trauma reach the score without a special system. An absent or unauthored trait reads dial `0.5` (neutral) so an existing character does not move - the backward-compat rule the catalogue and task-806 both rely on.

## How

Declared in `engine/disposition.py`, not `engine/traits.py`: the tables name registry scores, so they live with the registry, and `traits.py` already exposes a trait's presence through `player.traits` so it needs no change. A delta is `(dial - 0.5) * coefficient`; `_dial` reads a boolean (present = 1.0), a numeric dial (clamped to [0,1]), or a string parameter (present = 1.0). `check_character()` validates every referenced score is declared; `tools/disposition_index.py` additionally checks that every trait named is a real `data/library/traits/*.json` id. Coefficients are unverified, directional starting points - stated in the module, not calibrated.

## Steps to verify

1. In the 🧠 Mind panel, read a character's disposition weights.
   - expected: a cowardly character reads safety+ / aggression-, derived from their traits, not hand-authored numbers.
   - observed: VERIFIED 2026-10-13, live on localhost:4444. The "Disposition - what they weigh" block renders the character's derived weights from `disposition.character_weights` (e.g. a need-pressed character reads "survive.utility.need_relief utility +40.00"). An unauthored character reads the neutral empty state. **Authored content exercises it**: the Eldenford cast carries the modifier traits and `/api/state` shows the derived weights - `patient` -> `social.weight.bully -1.0` (Blacksmith, Elder, Farmer, Road Guard Captain), `loner` -> `social.weight.ignore +1.0` (Elder), `chatty` -> `social.weight.chat +1.0` (Merchant), `cowardly` -> `relief.weight.witness +1.0` (Merchant, Kiala). Pinned by `tests/test_disposition.py::test_disposition_payload_wires_traits_needs_gates_and_dials`.
2. In the LLM Inspector, confirm the built request names the same traits.
   - expected: the request names the traits the weights were derived from.
   - observed: PARTIAL 2026-10-13. The traits now reach the prompt through `trait_behavior` on the `/api/state` payload the builder reads (`character-state.ts:288-303`), verified for 22/27 players; the Inspector's rendered request itself was not driven.

## Acceptance

- [x] Weights derive from traits, not per-character numbers (`trait_weights`; a cowardly character moves witness, an unauthored one is neutral).
- [x] Emotion / needs / relationships / memories each move at least one score (four readers, one test apiece).
- [x] `tests/test_disposition.py` 21 passed; the gate cross-checks trait ids against `data/library/traits/`.

## Files

- `engine/disposition.py` (the trait + live-modifier tables and readers)
- `tools/disposition_index.py` (the trait-catalog check)
- `tests/test_disposition.py` (the character-side tests)
