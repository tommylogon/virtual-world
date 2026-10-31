---
type: task
status: done
area: characters
priority: high
wiki: "[[Characters/Persona|Persona]]"
---

# task-903: Persona mapping reference doc + 10 improvement ideas

**Filed:** 2026-10-22
**Related:** task-915, task-916, task-917, task-918, task-919, task-920, task-921, task-922, task-923, task-924

## What

Save personality field mapping as reference doc; file 10 new improvement ideas as tasks

## Why

Persona field types (id-list vs prose), GIMP/MOSIAC/interaction/memory mappings, and 10 improvement ideas discussed but not saved as tasks or docs

## How

Create a reference doc mapping all persona fields to their consumers, and file the 10 improvement ideas as tasks (slug normalization, cross-field validation, vocabulary check, prose migration, pre-compile validation, compile undo/revert, compiled prose preview, media schema, experience field split, batch import validation)

## Browser UI and intended live verification

Intended UI home: Mind > Persona import

Current availability: always

Live steps when available:
1. Open mind persona
2. Verify id-list fields use slugs
3. Verify prose fields hold free text
4. Verify media feeds memory
5. Verify speech_pattern/quirks go to personality

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Personality field map documented in reference doc with explicit consumer table
   - observed: `docs/virtualWorld/Characters/Persona.md` contains comprehensive field map table and consumer wiring
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: 10 improvement tasks authored and filed into `dev_tasks/todo/characters/`
   - observed: Filed task-915 through task-924 covering slug normalization, validation, media schema, preview, and batch import
3. Run the targeted regression test for the mechanism.
   - expected: Contract check and em-dash scans clean
   - observed: 0 em-dashes across all new task files

## Acceptance

- [x] Persona mapping doc saved (`docs/virtualWorld/Characters/Persona.md`)
- [x] 10 improvement tasks filed in dev_tasks (task-915 through task-924)

## Files

- `docs/virtualWorld/Characters/Persona.md`
- `docs/virtualWorld/dev_tasks/todo/characters/task-915-persona-slug-normalization-for-tag-and-id-list-fields.md`
- `docs/virtualWorld/dev_tasks/todo/characters/task-916-persona-cross-field-validation-for-conflicting-preferences.md`
- `docs/virtualWorld/dev_tasks/todo/characters/task-917-persona-vocabulary-check-against-known-library-tags.md`
- `docs/virtualWorld/dev_tasks/todo/characters/task-918-legacy-character-prose-description-migration-to-structured-persona.md`
- `docs/virtualWorld/dev_tasks/todo/characters/task-919-pre-compile-schema-and-consumer-validation-in-persona-compiler.md`
- `docs/virtualWorld/dev_tasks/todo/characters/task-920-persona-compile-undo-and-description-history-snapshotting.md`
- `docs/virtualWorld/dev_tasks/todo/characters/task-921-live-side-by-side-compiled-prose-preview-in-persona-tab.md`
- `docs/virtualWorld/dev_tasks/todo/characters/task-922-media-schema-formalization-feeding-lorebook-knowledge-and-memories.md`
- `docs/virtualWorld/dev_tasks/todo/characters/task-923-experience-field-split-into-structured-intimacy-history-and-boundaries.md`
- `docs/virtualWorld/dev_tasks/todo/characters/task-924-batch-persona-sheet-validation-for-character-library-import.md`
