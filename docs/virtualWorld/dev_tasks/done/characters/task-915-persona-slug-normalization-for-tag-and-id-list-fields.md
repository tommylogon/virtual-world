---
type: task
status: done
area: characters
priority: medium
wiki: "[[Characters/Persona|Persona]]"
related: ["task-903", "bug-570"]
---

# task-915: Persona slug normalization for tag and id-list fields

**Filed:** 2026-10-31
**Related:** task-903, bug-570

## What

Automatically normalize id-list inputs in the Persona tab and import pipeline to valid lower-case kebab-case/snake-case slugs (`^[a-z0-9][a-z0-9_-]*$`) rather than rejecting unnormalized typed input or letting uppercase display strings enter the tag arrays.

## Why

Id-list fields (`likes`, `dislikes`, `fears`, `interests`, `kinks`, `turn_ons`, `turn_offs`, `traumas`, `boundaries`, `traits`, `aspirations`, `quirks`, `habits`) must be tag slugs for engine consumers to match them against world entities and tags. Users naturally type `"Dark Caves"` or `"Monster energy drink"`, which currently fails validation or bypasses checks.

## How

- Add `normalize_slug(value: str) -> str` in `engine/character_appearance.py` that trims, lowercases, replaces non-alphanumeric punctuation with underscores, and strips illegal symbols.
- In `static/js/inspector/mind-view.ts`, apply slug normalization on chip creation so typed tags transform smoothly.
- Add unit tests verifying slug conversion across spaces, special characters, and diacritics.

## Acceptance

- [x] Typing spaces or mixed-case into Persona id-list fields normalizes to valid tag slugs.
- [x] Backend validator normalizes or rejects malformed slugs deterministically.
- [x] Unit tests cover slug normalization rules and edge cases.


## Verification

- Completed and verified 2026-10-31.
- Unit tests in 	ests/test_character_appearance.py and 	ests/test_character_store.py passing.
- TS build green and zero em-dashes.
