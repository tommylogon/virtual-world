---
type: task
status: done
area: ui
priority: medium
---

# Task-237: Save Area to Library Button

**Status:** In Review — implemented (context menu + inspector button); the recursive
bundle variant (task-357) is separate.

## What

"Save area to library" so a designed area in a scenario exports to
`data/library/areas/` as a reusable entry, mirroring items and characters.

## Implemented

- `static/js/library-browser.js` — `saveAreaByName(areaName)` →
  `_saveAreaWithDiffModal(areaName, payload)` (DiffModal with Skip/Update/Create-New);
  registry write verified.
- `static/js/inspector/area-view.js` (header) — `📚 Save to Library` button →
  `libraryBrowser.saveAreaByName(name)`.
- `static/js/graph-manager.js` + `graph/context-menu.js` — right-click area context menu
  item `📚 Save to Library` → same.
- What is captured: area description, environment (light/temp/air/smell/noise), tags,
  exits (via authoring data), placed items, triggers (via diff sections).
- Upsert semantics: DiffModal; duplicate names handled via the modal's Save-as-Duplicate.

## Notes

Task-357 (structure save/load connected areas) is the recursive bundle; this is the
single-area special case. Verify browser: context-menu save → diff modal → library entry.

## Steps to verify

- expected: an area can be saved to the library from the inspector.
- observed (2026-10-10 live, Animal Pens): header carries '📚 Save to Library' (area-view.ts -> libraryBrowser.saveAreaByName).

## Why

TODO

## How

TODO

## Acceptance

- [ ] TODO

## Browser UI and intended live verification

Intended UI home: Area Inspector header → 📚 Save to Library; Graph → right-click
an area → 📚 Save to Library; then Library Browser → Areas.

Current availability: The inspector button and graph context-menu action both
call `saveAreaByName()` and open DiffModal. The card records a live check that
Animal Pens displayed the inspector button; registry write and create/update
choice are not recorded as live results.

Live steps when available:
1. Open Animal Pens in the area Inspector and click 📚 Save to Library; read
   the DiffModal sections for description, environment, tags, exits, placed
   items, and triggers.
   - expected: the proposed entry contains only that area's authored bundle
     and offers Skip / Update / Create New.
2. Choose Create New, then open Library Browser → Areas and select the new
   entry; repeat from Graph's area context menu on the same area.
   - expected: the new area entry can be read back with the fields just
     reviewed, and both entry points produce the same payload.
3. Save an area with an existing library name and choose Update, then choose
   Skip in a second attempt.
   - expected: Update replaces that named entry; Skip leaves its stored data
     unchanged.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Files

- TODO
