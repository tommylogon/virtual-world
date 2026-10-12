---
type: task
status: todo
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704, task-691, task-714]
blocked_by: [task-800]
---

# task-805: Disposition whispers: render the score registry as words for the LLM

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

The same registry and weights rendered as prose for the LLM prompt, so soak and LLM share one vocabulary instead of two.

## Why

One layer for soak and LLM: the soak gets the numbers, the LLM gets the whispers, both from the same authored traits. Extends the existing behavior_prompt pattern in engine/traits.py.

## How

For each active score/trait above a threshold, emit a short line into the character context. Reuse behavior_prompt where a trait already has one.

## Steps to verify

1. In the app, open the LLM Inspector (`VW.inspector.showAgent`) for a strongly-traited character.
   - expected: the built request contains the character's traits as prose (the whisper lines).
   - observed: TODO
2. The same character in the 🧠 Mind panel (`InspectorMindView`).
   - expected: the whispers and the numbers come from the same traits.
   - observed: TODO

## Acceptance

- [ ] The LLM context carries the same traits the soak weights.
- [ ] No trait renders only in numbers or only in words.

## Files

- `engine/traits.py`
- `static/js/agent/prompt-builder/character-state.ts`
