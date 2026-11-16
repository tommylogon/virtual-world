---
type: task
status: review
area: ui
priority: medium
wiki: "[[World Building/WorldPainter]]"
---

# task-880: WorldPainter modularisation: split editor.ts into canvas, dialogs, and palette modules

**Filed:** 2026-10-19
**Related:** task-776, task-876, task-877, task-879

## What

Split the monolithic `static/js/worldpainter/editor.ts` into coherent, decoupled modules under `static/js/worldpainter/`:
1. `editor-dialogs.ts`: Modal and popover dialogs (Grid exact dimensions, Heightmap import/export, New scope prompt, Interior floor-plan picker, Scope chooser, Generation preview).
2. `editor-palette.ts`: The floating tile palette, category rail, search filter, tile detail panel, blocker badge, and cell & seam inspectors.
3. `editor-handles.ts`: Interactive canvas handles (cell 0,0 corner handle resize, frame boundary E/S/SE handles, reference image scaling/cropping handles).
4. `editor-canvas.ts`: Konva rendering passes: grid lines, vision decor, route drawing, stroke accumulator, selection marquee, cell clicking, and batch nudges.
5. `editor.ts`: Core Konva stage lifecycle, viewport state, tool rail, toolbar orchestration, and network mutation dispatch.

## Why

At 5,379 lines prior to modularization, `editor.ts` was the single largest TypeScript file in the front-end. It conflated five distinct responsibilities:
- UI dialog DOM rendering and file upload/download flows
- Pure Konva canvas transformations and shape drawing
- Pointer drag maths for multiple independent interactive handle systems
- Tile vocabulary browsing and search filtering
- Network synchronization, undo/redo stacks, and preflight blockers

This makes adding features difficult to navigate and increases compilation overhead. Isolating math and state contracts into pure modules drastically improves testability and readability.

## How

1. **Extract Dialogs (`editor-dialogs.ts`):** Move `openGridDialog`, `openHeightmapImportDialog`, `openHeightmapExportDialog`, `promptNewScope`, `showChooser`, and interior floor-plan pickers out of `editor.ts`.
2. **Extract Palette (`editor-palette.ts`):** Move `palettePanel`, category filtering, blocker badge, feature/area bars, grid HUD, and detail panel DOM builders into a dedicated module that interfaces with `grid-model.ts` vocabulary functions.
3. **Extract Handle Drag Logic (`editor-handles.ts`):** Group `refMouseDown`/`refMouseMove`/`refMouseUp` and `gridMouseDown`/`gridMouseMove`/`gridMouseUp` along with their stage anchor maths and reference image transforms.
4. **Extract Canvas Rendering & Stroke Logic (`editor-canvas.ts`):** Move grid line drawing, vision decor, route rendering, marquee, nudging, and stroke batch mutations.
5. **Shared Ambient Types (`static/js/types/worldpainter.d.ts`):** Declare interfaces (`WpState`, `WpPayload`, `WpCell`, etc.) once for TypeScript type checking without polluting classic script namespaces.
6. **Bundle/Compile:** Compile via `npm run build:ts` ensuring all parts compile cleanly and remain accessible through the window namespace / classic script tags in `templates/index.html`.
7. Zero regressions in the 68 WorldPainter unit test suite and scope generator tests.

## Browser UI and intended live verification

Intended UI home: WorldPainter overlay canvas and toolbars

Current availability: Functional modularized implementation in `editor.ts`, `editor-dialogs.ts`, `editor-palette.ts`, `editor-handles.ts`, and `editor-canvas.ts`.

Live steps:
1. Open WorldPainter on any scope (e.g. `world` or `the_pines`).
2. Verify all modal dialogs open, render, and commit edits without error (Grid dropdown exact dimensions dialog, heightmap import dialog, add feature prompt).
3. Verify palette rail filters tiles by category and search.
4. Verify cell resize (0,0) green handle and boundary handles drag smoothly on canvas.

## Steps to verify

1. Follow the live verification steps above on the running server (`http://localhost:4444`).
   - expected: All tools, handles, dialogs, and palette function identically to the monolithic build.
   - observed: Clean UI mounting with zero console errors.
2. Run unit test suite `node tools/unit/run.cjs test_worldpainter.js` and verify all tests pass.
   - expected: All 68 tests pass.
   - observed: 68 passed, 0 failed.
3. Run backend scope generator tests `python -m pytest tests/test_scope_generation_preview.py tests/test_scope_generators.py`.
   - expected: All 7 tests pass.
   - observed: 7 passed, 0 failed.

## Acceptance

- [x] `editor.ts` line count decreases by at least 1,800 lines (under 2,600 lines) - achieved 2,577 lines (reduction of 2,802 lines).
- [x] Dialogs are isolated in `editor-dialogs.ts` (609 lines).
- [x] Palette components are isolated in `editor-palette.ts` (796 lines).
- [x] Handles are isolated in `editor-handles.ts` (574 lines).
- [x] Canvas rendering is isolated in `editor-canvas.ts` (683 lines).
- [x] No regression in canvas handle manipulation, painting, or dialog execution.
- [x] `node tools/unit/run.cjs test_worldpainter.js` passes with zero failures (68/68 ok).
- [x] Zero em-dashes introduced.

## Files

- `static/js/worldpainter/editor.ts`
- `static/js/worldpainter/editor-dialogs.ts`
- `static/js/worldpainter/editor-palette.ts`
- `static/js/worldpainter/editor-handles.ts`
- `static/js/worldpainter/editor-canvas.ts`
- `static/js/types/worldpainter.d.ts`
- `templates/index.html`
- `tools/unit/test_worldpainter.js`
