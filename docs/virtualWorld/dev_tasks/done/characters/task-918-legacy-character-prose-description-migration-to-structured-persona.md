---
type: task
status: done
area: characters
priority: medium
wiki: "[[Characters/Persona|Persona]]"
related: ["task-903", "task-843"]
---

# task-918: Legacy character prose description migration to structured persona

**Filed:** 2026-10-31
**Related:** task-903, task-843

## What

Build an offline / CLI tool (`tools/migrate_prose_to_persona.py`) and an inspector action that parses unstructured character description paragraphs into the 4-part persona block (`identity`, `appearance`, `personality`, `narrative`), keeping existing prose intact as `base_description`.

## Why

Older scenarios (and imported third-party character cards) have multi-paragraph descriptions mixing eye color, height, speech quirks, and backstory into a single prose wall. Converting them to structured persona blocks manually is tedious and error-prone.

## How

- Implement an extraction pipeline in `tools/migrate_prose_to_persona.py` using LLM entity extraction and heuristic regex matching for age, height, eye color, hair, and clothing.
- Allow dry-run review before applying updates to scenario JSON files.
- Add unit tests verifying schema conformance of generated persona blocks.

## Acceptance

- [x] CLI tool can parse a character prose description into a valid persona schema block.
- [x] Converted persona block round-trips through validation without dropping prose context.
- [x] Tested on sample character descriptions from Kraktooth and Millwood.


## Verification

- Completed and verified 2026-10-31.
- Unit tests in 	ests/test_character_appearance.py and 	ests/test_character_store.py passing.
- TS build green and zero em-dashes.
