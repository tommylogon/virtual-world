---
type: task
status: done
area: characters
priority: medium
wiki: "[[Characters/Persona|Persona]]"
related: ["task-903", "task-844"]
---

# task-921: Live side-by-side compiled prose preview in Persona tab

**Filed:** 2026-10-31
**Related:** task-903, task-844

## What

Add a live side-by-side diff preview modal / drawer in the Persona tab before committing a compile action, displaying:
1. Current `base_description` vs Proposed compiled description
2. Current `personality` vs Proposed compiled personality
3. Current tags vs Proposed tag diffs (added/removed)

## Why

Compiling currently applies the changes directly when `force: true` or opens a simple alert. The author needs to clearly see what sentences and tags will change before applying the compile.

## How

- Wire into the existing `DiffModal` widget (`static/js/ui/diff-modal.ts`).
- When clicking "Compile", call `POST /api/players/<name>/record/compile` (dry-run mode without saving) and open the diff modal.
- Allow per-section acceptance (e.g. "Apply description only", "Apply personality only", or "Apply all").

## Acceptance

- [x] Persona Compile opens a diff preview showing side-by-side prose comparisons.
- [x] Authors can cancel the compile or accept specific sections.
- [x] No prose is overwritten until the author explicitly clicks Apply in the diff view.


## Verification

- Completed and verified 2026-10-31.
- Unit tests in 	ests/test_character_appearance.py and 	ests/test_character_store.py passing.
- TS build green and zero em-dashes.
