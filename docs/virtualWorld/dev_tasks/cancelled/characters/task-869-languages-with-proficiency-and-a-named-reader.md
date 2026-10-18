---
type: task
status: cancelled
area: characters
priority: medium
horizon: next
goal: A character's languages and proficiency are authored and consumed by a named reader.
wiki: "[[Persona]]"
blocked_by: [task-865]
---

# task-869: Languages with proficiency and a named reader

**Filed:** 2026-10-18
**Related:** 

<!-- deps:start -->
**Blocked by:** [[task-865-rename-the-persona-block-key-from-appearance-to-persona]]
<!-- deps:end -->

## What

No language field exists on a character. The request is a language value with a proficiency, and possibly a per-language memory dictionary.

## Why

Multilingual worlds need to know who speaks what. The field must have a named reader (who asks "does this character speak Elvish?") or it is unread fiction and rots. That reader is the open decision this card must settle before building.

## How

1. Add `languages: [{id, proficiency}]` to the identity or narrative section of the block.
2. Decide and implement the reader: at minimum the agent prompt context ("you speak Elvish, Common, and passable Dwarvish"); optionally a dialogue / perception gate.
3. If a per-language dictionary is wanted, it rides `player.memories` tagged by language, not a second store.
4. Serve the field in `schema_for_llm`.
5. Round-trip.

## Browser UI and intended live verification

Authoring in the Persona tab (a language + proficiency list). Live check: author two languages, confirm the agent prompt context shows them and a reload keeps them.

## Steps to verify

1. Author a language with a proficiency.
   - expected: the field stores and round-trips.
   - observed: TODO
2. Build the agent prompt for that character.
   - expected: the reader shows the languages.
   - observed: TODO

## Acceptance

- [ ] Language plus proficiency is authorable and stored.
- [ ] A named reader consumes it.
- [ ] The field round-trips a scenario save / load.
- [ ] Open decision recorded: which reader (prompt context, dialogue gate, or perception).

## Files

- `engine/character_appearance.py`
- `static/js/agent/prompt-builder/character-state.ts`
- `static/js/inspector/mind-view.ts`
- `tests/test_character_appearance.py`

## Retracted 2026-10-18

Folded into `task-733`, whose projection table maps `capabilities.languages -> skills, traits`. That mapping is the thing this card disagreed with: a language is not a skill, and if the engine is to gate dialogue or perception on it, it needs its own field with a proficiency and a named reader. The correction is recorded on `task-733`; this card is cancelled so the parent holds the decision.
