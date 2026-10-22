---
type: task
status: todo
area: characters
priority: high
wiki: "[[Characters/Persona|Persona]]"
---

# task-903: Persona mapping reference doc + 10 improvement ideas

**Filed:** 2026-10-22
**Related:** 

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
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

Persona mapping doc saved; 10 improvement tasks filed in dev_tasks

## Files

- `docs/virtualWorld/Characters/Persona.md`
- `engine/character_appearance.py`
- `static/js/character-import.ts`
