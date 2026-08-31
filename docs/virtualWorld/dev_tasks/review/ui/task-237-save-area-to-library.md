# Task-237: Save Area to Library Button

**Status:** In Review — implemented (context menu + inspector button); the recursive
bundle variant (task-357) is separate.

## Goal

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
