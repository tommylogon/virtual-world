---
type: task
status: done
area: characters
priority: high
wiki: "[[Characters/Persona|Persona]]"
related: ["task-903"]
---

# task-919: Pre-compile schema and consumer validation in persona compiler

**Filed:** 2026-10-31
**Related:** task-903

## What

Execute strict pre-compile validation before running `compile_persona()`. Refuse compile or highlight issues if required schema fields are missing, invalid data types are present, or known consumers cannot parse the structured values.

## Why

Compiling an incomplete or broken persona block currently generates broken or empty prose segments (e.g. `None` strings, incomplete sentences, or malformed tag lists) that overwrite working authored prose.

## How

- In `engine/character_appearance.py`, introduce `validate_before_compile(record: dict) -> tuple[bool, list[str]]`.
- Check required types, age ranges, gender/pronoun consistency, and slug conformity.
- Return structured error summaries in `POST /api/players/<name>/record/compile`.
- Prevent accidental overwrite if critical validation errors exist.

## Acceptance

- [x] `compile_persona` refuses compile if critical validation errors exist, returning actionable reasons.
- [x] Warning-level issues are reported without blocking compilation when safe.
- [x] Unit tests cover validation rejections and safe compilations.


## Verification

- Completed and verified 2026-10-31.
- Unit tests in 	ests/test_character_appearance.py and 	ests/test_character_store.py passing.
- TS build green and zero em-dashes.
