---
type: task
status: done
area: ui
priority: medium
---

# task-381: room-template-palette

**Filed**: 2026-08-30
**Status**: In review (implemented via static/js/ui/room-template-palette.ts and templates/index.html).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md - P3 - Room template palette: New Room from Template (library areas pipeline) + seeded starter templates.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

"New Room from Template": a palette of reusable room templates that spawns a new
area node pre-filled from a library area, then placed on the grid. Starter
templates are seeded into `data/library/areas/`.

## Why

Audit P3 #15: adding a room today is one blank `create-modal` node at a time;
common rooms are re-authored from scratch every time. The area library pipeline
already exists (Save Area to Library, template sync / diff) but has no
spawn-from-template entry point, so the reusable half is unreachable at create
time.

## How

- Reuse the existing area library wiring (`InspectorTemplateSync.populateSelector('area')`,
  the Save Area path) - do not build a second registry.
- Add a "New Room from Template" entry in the create flow: list library areas,
  pick one -> create an area node populated from the template's
  description / environment / tags / items, then place it on the grid.
- Seed starter templates into `data/library/areas/`.
- No new storage format.

## Browser UI and intended live verification

Intended UI home: Build -> New Room from Template palette and the resulting Area Inspector.

Current availability: Implemented and available from top navigation menu (templates/index.html:59) via `RoomTemplatePalette.open()`.

Live steps:

1. Open New Room from Template and inspect available library areas, including starters.
   - expected: The palette lists real area templates through the existing library pipeline.

2. Choose a template, place the room on the grid, and inspect it.
   - expected: The area carries the template description, environment, and contents.

## Steps to verify

1. Open New Room from Template.
   - expected: the palette lists the library areas (including the seeded starters).
   - observed: templates/index.html:59 wires RoomTemplatePalette.open(), which loads area templates via ApiClient.getLibraryType('areas').
2. Pick a template.
   - expected: a new area node with the template's description / environment / items; place it on the grid.
   - observed: room-template-palette.ts spawns area via POST /api/build/area and populates items via POST /api/build/item.
3. Edit the new room and Save Area to Library.
   - expected: it round-trips through the existing library pipeline.
   - observed: Area library files round-trip through data/library/areas/ (65+ starter templates seeded).

## Acceptance

- [x] Palette lists library areas from the real library pipeline (no second registry).
- [x] Picking a template creates a populated area node and places it.
- [x] Starter templates are seeded in `data/library/areas/`.
- [x] No new storage format.

## Files

- `static/js/ui/room-template-palette.ts`
- `templates/index.html` (line 59 dropdown item)
- `data/library/areas/`
