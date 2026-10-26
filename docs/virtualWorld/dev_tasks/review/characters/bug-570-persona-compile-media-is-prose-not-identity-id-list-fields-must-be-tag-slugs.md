---
type: bug
status: review
area: characters
priority: high
wiki: "[[Characters/Persona|Persona]]"
---

# bug-570: Persona compile: media is prose not identity; id-list fields must be tag slugs

**Filed:** 2026-10-22
**Related:** 

## What

Fix persona compile validation: media should not be identity (prose, not tags); likes/dislikes/fears/interests/kinks/turn_ons/turn_offs/traumas/boundaries/habits/quirks/traits/aspirations must be tag ids (slugs), not display names; speech_pattern is prose.

## Why

Miki card shows correct tag ids (monster_energy, alcohol, social_media_attention, stripping_goals) but error shows display names rejected (Monster energy drink, alcohol mixed with Monster). Media is a prose category (movies/games/books/music), not identity. The compile is correct (fail-closed on unknown ids); the data/authorship is wrong.

## How

Update persona import/compile docs; fix any authored scenarios using display names; verify all id-list fields use slug format.

## Browser UI and intended live verification

Intended UI home: Mind > Persona import

Current availability: always

Live steps when available:
1. Open mind persona
2. Check likes/dislikes/fears/interests/kinks/turn_ons/turn_offs/traumas/boundaries are tag ids
3. Check media is prose (not identity)
4. Verify speech_pattern is prose
5. Confirm habits/quirks/traits/aspirations are tag ids

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Mind > Persona inspector displays identity (without media), narrative (holding media list), and personality id-list tags.
   - observed: Confirmed. Persona tab mounts sections from schema and rejects non-slug ids.
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: Inspected schema and validation in NL editor and Persona system.
   - observed: Tested validate_ops in NL editor validation with character update and verified rejection of non-slug display names.
3. Run the targeted regression test for the mechanism.
   - expected: 88 passed in tests/test_character_appearance.py and 10 passed in tests/test_nl_editor_validation.py.
   - observed: 88 passed in tests/test_character_appearance.py in 8.82s; 10 passed in tests/test_nl_editor_validation.py in 2.14s.

## Acceptance

- [x] Personality fields validated: id-list fields hold slugs; prose fields hold free text.
- [x] Media moved out of identity to narrative prose list.
- [x] No display names in likes/dislikes/fears/interests/kinks/turn_ons/turn_offs/traumas/boundaries/habits/quirks/traits/aspirations.

## Files

- `engine/character_appearance.py`
- `engine/nl_editor_validation.py`
- `docs/virtualWorld/Characters/Persona.md`
