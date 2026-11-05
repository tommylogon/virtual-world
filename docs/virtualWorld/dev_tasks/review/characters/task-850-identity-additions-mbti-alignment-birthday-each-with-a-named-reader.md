---
type: task
status: todo
area: characters
priority: medium
related: [task-316, task-507, task-733]
wiki: "[[Characters/Persona]]"
---

# task-850: Identity additions: mbti, alignment, birthday, media - each with a named reader

**Filed:** 2026-10-16
**Related:** 

<!-- deps:start -->
**Related:** [[task-316-id-backed-character-identity]], [[task-507-structured-appearance-personality-fields-for-characters-optional-llm-fillable]], [[task-733-character-sheet-a-full-page-worldgraph-style-person-form-that-compiles-into-viwo-primitives]]
<!-- deps:end -->

## What

Add mbti, alignment, birthday to identity only with wired consumers (mbti prompt voice, alignment disposition-or-prompt reader, birthday calendar semantics vs age); no dead fields.

Extended 2026-10-18 (folded in from the cancelled task-870): also add `media` (favourite films / music / books) and keep `potential_storylines`. `engine/character_appearance.py:21` excludes `media` / `mbti` / `alignment` on purpose, and `tests/test_character_appearance.py` enforces the ban (`:427`; a `media` key is rejected at `:140`), so this card must remove that exclusion and its test assertions deliberately. `media` and `potential_storylines` need a named reader too (agent prompt context is the obvious one); `potential_storylines` may ship authored-but-unread if recorded as such.

## Why

A character's identity needs expressive hooks (MBTI, alignment, birthday, favourite media) that directly drive agent behavior, prompts, and world semantics rather than existing as dead metadata. MBTI and alignment calibrate the persona voice sent to LLM agents; birthday wires directly into the world calendar and character aging; favourite media items provide seeds for character memory, likes, and interest tags without inventing duplicate authoring channels.

## How

1. Lift the exclusion of `mbti`, `alignment`, and `media` from `engine/character_appearance.py` and adjust tests in `tests/test_character_appearance.py` that enforced the exclusion.
2. Wire `mbti` and `alignment` into the character's compiled personality block and agent prompt context formatter (`agent_prompt.py` / `prompting.py`).
3. Connect `birthday` to `engine/world_calendar.py` / `engine/character_lifecycle.py` so simulated game days advance age and calendar events when dates match.
4. Project authored `media` entries into character `interest_tags` / likes and seed baseline memory facts during compilation/hydration, ensuring media items have active simulation consumers.
5. Provide UI inputs for these fields in the Mind Dashboard Persona tab and Character Sheet editor.

## Browser UI and intended live verification

Intended UI home: Character Inspector -> Mind -> Persona tab (and the full-page Character Sheet).

Current availability: Planned; the Persona tab currently exposes appearance, core identity picklists, and personality, but mbti, alignment, birthday, and media inputs are not yet rendered in the live UI.

Live steps when available:
1. Open Character Inspector -> Mind -> Persona tab on a character.
   - expected: Inputs for MBTI, Alignment, Birthday, and Favourite Media are present and editable.
2. Enter values (e.g. MBTI 'INFP', Alignment 'Chaotic Good', Birthday 'Spring 14', Favourite Media 'The Old Wayfarer (book)'), save, and compile.
   - expected: Save succeeds; the compiled personality prose / agent prompt preview includes the personality traits; the media item seeds an interest tag or memory fact.
3. Advance the world calendar past the birthday.
   - expected: Calendar event or age increment triggers as designed without crashing.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Fields save, round-trip, compile into prompt context, and project media to interest tags.
   - observed: TODO
2. Inspect prompt generation via `python -m pytest tests/test_agent_prompt.py` or inspect `/api/players/<name>/record`.
   - expected: Prompt voice receives MBTI and alignment cues.
   - observed: TODO
3. Run the targeted regression test for schema and serialization: `python -m pytest tests/test_character_appearance.py tests/test_character_record.py`.
   - expected: All tests pass with new fields accepted and serialized.
   - observed: TODO

## Acceptance

- [ ] `mbti`, `alignment`, `birthday`, and `media` fields are valid attributes on character nodes / persona blocks.
- [ ] `engine/character_appearance.py` accepts the fields and no longer bans them.
- [ ] MBTI and alignment are included in the prompt context / personality compilation for LLM agents.
- [ ] Birthday is linked to the world calendar and lifecycle aging logic.
- [ ] Media favorites compile/project into character memories or interest tags.
- [ ] Schema validation and character record unit tests pass cleanly.

## Files

- `engine/character_appearance.py`
- `engine/character_record.py`
- `engine/agent_prompt.py`
- `engine/world_calendar.py`
- `static/js/inspector/mind-view.ts`
- `tests/test_character_appearance.py`
- `tests/test_character_record.py`
