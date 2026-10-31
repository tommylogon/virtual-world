---
type: task
status: done
area: characters
priority: low
wiki: "[[Characters/Persona|Persona]]"
related: ["task-903"]
---

# task-917: Persona vocabulary check against known library tags

**Filed:** 2026-10-31
**Related:** task-903

## What

Check id-list entries (`fears`, `interests`, `traits`) against the library's authoritative tag registry (`data/library/tags/`). Surface unmatched tags as "free tags" while offering autocompletion against canonical library tags.

## Why

A typo in a tag slug (e.g. `arachnid` instead of `spider` or `spiders`) prevents `engine.fear` and perception matching from triggering against authored hazards, making authored traits silently inert.

## How

- Expose a tag catalog endpoint or reuse `GET /api/library/tags`.
- In `static/js/inspector/mind-view.ts`, visually distinguish known tags (solid border) from unrecognized custom tags (dashed border).
- Provide autocomplete suggestions in tag input fields.

## Acceptance

- [x] Persona tag inputs provide autocomplete against known library tag slugs.
- [x] Tags not found in the library catalog render with distinct styling in the UI.
- [x] Unknown tags remain valid without blocking custom authoring.


## Verification

- Completed and verified 2026-10-31.
- Unit tests in 	ests/test_character_appearance.py and 	ests/test_character_store.py passing.
- TS build green and zero em-dashes.
