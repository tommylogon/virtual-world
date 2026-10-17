---
type: task
status: review
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: ["'task-704'", "'task-799'", "'task-800'", "'task-801'", "'task-802'", "'task-803'", "'task-804'", "'task-806'", 'task-799', 'task-800', 'task-802', 'task-803', 'task-804', 'task-806']
blocked_by: [task-800]
---

# task-805: Disposition whispers: render the score registry as words for the LLM

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-799-disposition-spike-do-three-unrelated-soak-decisions-fit-one-score-registry]], [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-801-disposition-action-features-verb-score-contributions]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]], [[task-803-disposition-value-gates-traits-and-morality-as-hard-exclusions]], [[task-804-disposition-pick-argmax-with-a-stable-tie-break]], [[task-806-split-traits-capabilities-from-personality-decision-dials]]
<!-- deps:end -->

## What

The same registry and weights rendered as prose for the LLM prompt, so soak and LLM share one vocabulary. `disposition.whispers(player)` emits one line per active trait that moves a score, plus a pressing need and a remembered target. `TraitSystem.behavior_prompts(player)` returns each carried trait's own `behavior_prompt`.

**The gap it closes:** the prompt builder already reads `player.trait_behavior` (`static/js/agent/prompt-builder/character-state.ts:288-303`) and **nothing in Python ever wrote it** (`grep trait_behavior --glob *.py` finds no writer), so the trait schema-v2 `behavior_prompt` never reached a prompt. Serialization now writes both the trait prose and the whispers into that field.

## Why

One layer for soak and LLM: the soak gets the numbers, the LLM gets the whispers, both from the same authored traits - so a character does not have two vocabularies. It also repairs the schema-v2 seam: the read side existed, the write side was never built.

## How

`engine/disposition.whispers` (with `WHISPERS`, `_NEED_WHISPERS`, `pressing_need`); `engine/traits.TraitSystem.behavior_prompts`; and `engine/serialization._trait_behavior`, merged into the player payload as `trait_behavior`. No JavaScript change was needed - `character-state.ts` already reads the field, so this is the missing writer. The lines are deterministic and de-duplicated, and `whispers` composes from the same `TRAIT_MODIFIERS` / `NEED_THRESHOLDS` the soak weights read.

## Steps to verify

1. In the app, open the LLM Inspector for a strongly-traited character.
   - expected: the built request contains the character's traits as prose.
   - observed: PARTIAL 2026-10-13. `/api/state` carries `trait_behavior` for 22/27 players (the trait behavior_prompts + the whispers), which is the field the builder reads; the Inspector render itself was not driven.
2. The same character in the 🧠 Mind panel.
   - expected: the whispers and the numbers come from the same traits.
   - observed: VERIFIED 2026-10-13, live on localhost:4444. The "Disposition - what they weigh" block shows the character's weights *and* the whisper lines from the same traits, e.g. scarred's behavior_prompt plus "You need to relieve yourself."

## Acceptance

- [x] The LLM context carries the same traits the soak weights (payload verified live: 22/27 players).
- [x] No trait renders only in numbers: every trait in `TRAIT_MODIFIERS` has a `WHISPERS` line, and every carried trait with a `behavior_prompt` contributes prose.
- [x] `tests/test_disposition.py` 36 passed; `tests/test_serialization.py` 16 passed.

## Files

- `engine/disposition.py` (`whispers`, `WHISPERS`, `pressing_need`)
- `engine/traits.py` (`TraitSystem.behavior_prompts`)
- `engine/serialization.py` (`_trait_behavior` + the payload field)
- `tests/test_disposition.py`
- `static/js/agent/prompt-builder/character-state.ts` (reader only - unchanged; it already consumed the missing field)

## Browser UI and intended live verification

Intended UI home: load a character → Human Turn/Agent Lens prompt context → inspect the generated disposition/trait prose and the matching raw LLM input.

Current availability: the card records live payload verification for 22/27 players and tests for score whispers and carried-trait `behavior_prompt` prose. The UI should expose the same prompt context the LLM receives; no new editor is claimed.

Live steps when available:
1. Select a character with a trait in `TRAIT_MODIFIERS` and inspect its Agent Lens prompt context and Raw LLM capture.
   - expected: the character receives the matching `WHISPERS` line in words, not only a numeric score.
2. Select a character carrying a trait with `behavior_prompt` and inspect the same two surfaces.
   - expected: the trait's authored behavior prose appears once in the LLM context and agrees with the carried trait in `/api/state`.
3. Give the character a pressing need and a remembered target, then reopen the prompt context.
   - expected: the whisper includes those live modifiers only when present and uses the same score vocabulary as the soak registry.
4. Compare the visible Agent Lens and captured raw prompt.
   - expected: both contain the same disposition text; the UI does not fabricate additional personality traits.

This section is not a claim that every character payload is freshly verified today.
