---
type: task
status: done
area: characters
priority: low
wiki: "[[Characters/Persona|Persona]]"
related: ["task-903", "task-843"]
---

# task-924: Batch persona sheet validation for character library import

**Filed:** 2026-10-31
**Related:** task-903, task-843

<!-- deps:start -->
**Related:** [[task-903-persona-mapping-reference-doc-10-improvement-ideas]], [[task-843-character-file-import-llm-converts-any-card-or-prose-to-the-persona-schema]]
<!-- deps:end -->

## What

Add a bulk validation step in the character library import tool (`static/js/character-import.ts` and `engine/character_appearance.py`) to validate all characters in a scenario or folder, reporting missing required fields, unnormalized tags, or broken references in a single batch report.

## Why

When importing a cast of 10+ characters from an external JSON pack or library folder, individual errors currently surface one-by-one upon inspection or compile, causing repetitive context switching.

## How

- Add `validate_persona_batch(characters: list[dict]) -> dict` returning per-character health status and issues.
- Expose a "Validate All Characters" button in the library import dialog and Scenario Wizard.
- Surface summary pills (e.g. `12 valid · 2 warnings · 1 error`).

## Acceptance

- [x] Batch validation analyzes all characters in a payload or library folder without stopping on the first failure.
- [x] Returns a structured health summary categorizing valid, warning, and broken characters.
- [x] Covered by unit tests in `tests/test_character_appearance.py`.


## Verification

- Completed and verified 2026-10-31.
- Unit tests in tests/test_character_appearance.py and tests/test_character_store.py passing.
- TS build green and zero em-dashes.
