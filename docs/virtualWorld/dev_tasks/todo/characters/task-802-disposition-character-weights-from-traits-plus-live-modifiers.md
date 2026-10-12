---
type: task
status: todo
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704, task-691, task-714]
blocked_by: [task-800]
---

# task-802: Disposition character weights from traits, plus live modifiers

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

The character-side half: a trait -> weight-delta table, and live modifiers from emotion, needs, relationships and recent memories.

## Why

A character's numbers must be its traits, authored once - not hand-authored per character, which is a second copy of the prose. Live modifiers are how fear, hunger, loyalty and trauma reach the score without a special system.

## How

One trait -> {score: coef} table. Modifiers read state: emotion, vitals, relationship closeness, memories bound to an entity. delta = (value - 0.5) * coefficient if traits are dials.

## Steps to verify

1. In the 🧠 Mind panel (`InspectorMindView`), read a character's disposition weights.
   - expected: a cowardly character reads safety+ / aggression-, derived from their traits, not hand-authored numbers.
   - observed: TODO
2. In the app, open the LLM Inspector (`VW.inspector.showAgent`) for that character.
   - expected: the built request names the same traits the weights were derived from.
   - observed: TODO

## Acceptance

- [ ] Weights derive from traits, not per-character numbers.
- [ ] Emotion/needs/relationships/memories move at least one score.

## Files

- `engine/disposition.py`
- `engine/traits.py`
