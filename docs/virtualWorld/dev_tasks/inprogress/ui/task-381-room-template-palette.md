---
type: task
status: inprogress
area: ui
priority: medium
---

# task-381: room-template-palette

**Filed**: 2026-08-30
**Status**: Not started (card complete; no implementation yet).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P3 — Room template palette: New Room from Template (library areas pipeline) + seeded starter templates.

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
  the Save Area path) — do not build a second registry.
- Add a "New Room from Template" entry in the create flow: list library areas,
  pick one → create an area node populated from the template's
  description / environment / tags / items, then place it on the grid.
- Seed a handful of starter templates into `data/library/areas/`.
- Note task-645: `data/library/rooms/` holds files but has no read endpoint;
  area templates come from `data/library/areas/`.
- No new storage format.

## Steps to verify

1. Open New Room from Template.
   - expected: the palette lists the library areas (including the seeded starters).
   - observed: TODO
2. Pick a template.
   - expected: a new area node with the template's description / environment / items; place it on the grid.
   - observed: TODO
3. Edit the new room and Save Area to Library.
   - expected: it round-trips through the existing library pipeline.
   - observed: TODO

## Acceptance

- [ ] Palette lists library areas from the real library pipeline (no second registry).
- [ ] Picking a template creates a populated area node and places it.
- [ ] Starter templates are seeded in `data/library/areas/`.
- [ ] No new storage format.

## Files

- `static/js/` — the palette / create-modal entry (reuse `create-modal` + `InspectorTemplateSync`).
- `data/library/areas/` — seeded starter templates.
- `templates/index.html`.
- A read endpoint for the area library if one does not already exist.
