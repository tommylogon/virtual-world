---
type: task
status: todo
area: ui
priority: medium
wiki: "[[World Building/WorldPainter]]"
---

# task-880: WorldPainter modularisation: split editor.ts into canvas, dialogs, and palette modules

**Filed:** 2026-10-19
**Related:** task-776, task-876, task-877, task-879

<!-- deps:start -->
**Related:** [[task-776-worldpainter-polish-and-performance-soft-render-konva-offscreen-paint-palette-side-dock-and-the-cheap-workflow-wins]], [[task-876-worldpainter-one-grid-control-instead-of-the-grid-dialog-button-plus-the-grid-adjust-toggle]], [[task-877-worldpainter-import-and-export-a-greyscale-heightmap-for-the-floor-layer]], [[task-879-worldpainter-alt-click-samples-the-layer-value-under-the-cursor-into-the-brush]]
<!-- deps:end -->

## What

Split the monolithic `static/js/worldpainter/editor.ts` (currently 4,387 lines) into coherent, decoupled modules under `static/js/worldpainter/`:
1. `editor-dialogs.ts`: Modal and popover dialogs (Grid exact dimensions, Heightmap import/export, New scope prompt, Interior floor-plan picker).
2. `editor-palette.ts`: The floating tile palette, category rail, search filter, and tile detail panel.
3. `editor-handles.ts`: Interactive canvas handles (cell 0,0 corner handle resize, frame boundary E/S/SE handles, reference image scaling/cropping handles).
4. `editor.ts`: Core Konva stage lifecycle, viewport state, tool rail, toolbar orchestration, and network mutation dispatch.

## Why

At 4,387 lines, `editor.ts` is the single largest TypeScript file in the front-end. It conflates five distinct responsibilities:
- UI dialog DOM rendering and file upload/download flows
- Pure Konva canvas transformations and shape drawing
- Pointer drag maths for multiple independent interactive handle systems
- Tile vocabulary browsing and search filtering
- Network synchronization, undo/redo stacks, and preflight blockers

This makes adding features (like heightmap import/export or unified grid menus) difficult to navigate and increases compilation overhead. `grid-model.ts` (1,216 lines) already proved that isolating math and state contracts into pure modules drastically improves testability and readability.

## How

1. **Extract Dialogs (`editor-dialogs.ts`):** Move `_openGridDialog`, `_openHeightmapImportDialog`, `_openHeightmapExportDialog`, `_promptNewScope`, and interior floor-plan pickers out of `editor.ts`. Dialogs receive `p: WpPayload`, current state accessors, and a dispatch/request function.
2. **Extract Palette (`editor-palette.ts`):** Move `_palettePanel`, category filtering, and detail panel DOM builders into a dedicated module that interfaces with `grid-model.ts` vocabulary functions.
3. **Extract Handle Drag Logic (`editor-handles.ts`):** Group `_refMouseDown`/`_refMouseMove`/`_refMouseUp` and `_gridMouseDown`/`_gridMouseMove`/`_gridMouseUp` along with their stage anchor maths.
4. **Bundle/Compile:** Maintain bundle integrity via `tools/ts_convert.py` ensuring all parts compile cleanly and remain accessible through the window namespace / ES module exports.
5. Zero regressions in the 759 unit test suite.

## Browser UI and intended live verification

Intended UI home: WorldPainter overlay canvas and toolbars

Current availability: Functional monolithic implementation in `editor.ts`.

Live steps when available:
1. Open WorldPainter on any scope (e.g. `world` or `the_pines`).
2. Verify all modal dialogs open, render, and commit edits without error (Grid dropdown exact dimensions dialog, heightmap import dialog, add feature prompt).
3. Verify palette rail filters tiles by category and search.
4. Verify cell resize (0,0) green handle and boundary handles drag smoothly on canvas.

## Steps to verify

1. Follow the live verification steps above on the running server (`http://localhost:4444`).
   - expected: All tools, handles, dialogs, and palette function identically to the monolithic build.
   - observed: TODO
2. Run unit test suite `node tools/unit/run.cjs` and verify all tests pass.
   - expected: All 759+ tests pass.
   - observed: TODO

## Acceptance

- [ ] `editor.ts` line count decreases by at least 1,800 lines (under 2,600 lines).
- [ ] Dialogs are isolated in `editor-dialogs.ts`.
- [ ] Palette components are isolated in `editor-palette.ts`.
- [ ] No regression in canvas handle manipulation, painting, or dialog execution.
- [ ] `node tools/unit/run.cjs` passes with zero failures.
- [ ] Zero em-dashes introduced.

## Files

- `static/js/worldpainter/editor.ts`
- `static/js/worldpainter/editor-dialogs.ts`
- `static/js/worldpainter/editor-palette.ts`
- `static/js/worldpainter/editor-handles.ts`
- `tools/unit/test_worldpainter.js`
