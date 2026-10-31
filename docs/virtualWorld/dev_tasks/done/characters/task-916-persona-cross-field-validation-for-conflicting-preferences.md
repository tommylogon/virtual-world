---
type: task
status: done
area: characters
priority: medium
wiki: "[[Characters/Persona|Persona]]"
related: ["task-903"]
---

# task-916: Persona cross-field validation for conflicting preferences

**Filed:** 2026-10-31
**Related:** task-903

## What

Add cross-field contradiction checks in `engine/character_appearance.py` that identify mutually exclusive items in character preferences:
- Overlap between `likes` and `dislikes`
- Overlap between `turn_ons` and `turn_offs`
- Overlap between `fears` and `kinks` (unless explicitly flagged as a fearplay trope)

## Why

Characters authoring identical tags in both positive and negative preference arrays create erratic affect and dialogue generation where the LLM tries to simultaneously approach and avoid the same stimulus.

## How

- Add `validate_persona_conflicts(persona_dict: dict) -> list[str]` in `engine/character_appearance.py`.
- Surface non-blocking warnings in the Persona inspector tab and compile preview modal.
- Add unit tests verifying conflict detection and warning outputs.

## Acceptance

- [x] Overlapping tags across polar pairs (`likes`/`dislikes`, `turn_ons`/`turn_offs`) emit validation warnings.
- [x] Conflicts are non-blocking in authoring but visible in the Persona UI.
- [x] Unit tests cover detection of conflicting tag entries.


## Verification

- Completed and verified 2026-10-31.
- Unit tests in 	ests/test_character_appearance.py and 	ests/test_character_store.py passing.
- TS build green and zero em-dashes.
