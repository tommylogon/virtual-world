---
type: task
status: cancelled
area: characters
priority: medium
horizon: next
goal: mbti, alignment and media are authored AND read, not stored as decoration.
wiki: "[[Persona]]"
related: [task-865]
blocked_by: [task-865]
---

# task-870: Add mbti, alignment and media with a prompt reader

**Filed:** 2026-10-18
**Related:** task-865

<!-- deps:start -->
**Blocked by:** [[task-865-rename-the-persona-block-key-from-appearance-to-persona]]
**Related:** [[task-865-rename-the-persona-block-key-from-appearance-to-persona]]
<!-- deps:end -->

## What

`engine/character_appearance.py:21` excludes `media` / `mbti` / `alignment` on purpose because nothing reads them, and `tests/test_character_appearance.py` enforces the ban (`:427`, and a `media` key is rejected at `:140`). The request is to keep them, and to keep `potential_storylines` for later.

This card adds them WITH a reader, so they are not unread fiction.

## Why

A field with no reader rots; that is exactly why they were excluded. Keeping them is fine, but it is a deliberate reversal of a stated rule, and it comes with naming the reader (the agent prompt context is the obvious one, so the values reach the model) and removing the ban plus its test.

## How

1. Add `mbti` and `alignment` (personality section) and `media` (a `media` group, or personality).
2. Serve them in `schema_for_llm` and add a `CONSUMER_HINTS` entry naming each reader.
3. Feed them into the agent prompt context (`static/js/agent/prompt-builder/character-state.ts` or the system prompt) so they actually reach the model.
4. Remove the exclusion note and the test assertions that ban them, deliberately (not by bypassing the test).
5. `potential_storylines`: keep the field; no reader yet. Record it as authored-but-unread so the state is honest.

## Browser UI and intended live verification

The Persona tab renders the new fields. Live check: author an mbti / alignment / media value, build the agent prompt for that character, and confirm the values appear in it; reload and confirm they round-trip.

## Steps to verify

1. Author mbti / alignment / media on a character.
   - expected: they store and render in the Persona tab.
   - observed: TODO
2. Build the agent prompt for that character.
   - expected: the reader includes them.
   - observed: TODO
3. Run the appearance tests.
   - expected: no test bans the fields any more.
   - observed: TODO

## Acceptance

- [ ] `mbti`, `alignment`, `media` exist, are in the schema, and render in the Persona tab.
- [ ] A named reader consumes them (agent prompt context).
- [ ] The ban and its test are removed on purpose, not bypassed.
- [ ] `potential_storylines` is kept and marked as authored-but-unread.

## Files

- `engine/character_appearance.py`
- `static/js/agent/prompt-builder/character-state.ts`
- `static/js/inspector/mind-view.ts`
- `tests/test_character_appearance.py`

## Retracted 2026-10-18

Duplicate. `task-850` (Identity additions: mbti, alignment, birthday, each with a named reader) already covers mbti and alignment with the same "name the reader" requirement. The only fields this card added beyond task-850 were `media` (and keeping `potential_storylines`); both are folded into task-850, so this card is cancelled rather than kept as a second copy.
