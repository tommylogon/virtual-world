---
type: task
status: review
area: graph
priority: medium
---

# task-452: Graph PNG export (high-resolution, with map background)

**Filed:** 2026-09-22
**Related:** task-249

## Goal

Export the graph canvas to a high-resolution PNG that includes the map background layers, all visible nodes, edges and labels. Offscreen vis.Network re-render at 1x/2x/3x, Canvas2D composite of GraphBackground.getExportLayers(), whole-graph or current-view scope via a small dialog. New module static/js/graph/graph-export.js.

## Acceptance

- [x] Toolbar **📷 PNG** (Canvas group) and **⋯ More → 📷 Export PNG** open a dialog.
- [x] Dialog offers scope (whole graph fit / current view) and resolution (1×/2×/3×, 2× default).
- [x] Export includes the map background layers with crop/rotation/opacity intact, aligned under the nodes.
- [x] Export includes all currently visible nodes, ways, items, edges and labels; hidden/filtered nodes excluded.
- [x] Saves a real `.png` via `WorldExport.saveFileWithDialog` (now PNG-aware), with `<a download>` fallback.
- [x] Backing store capped at 8192px; dialog reports the rendered size.
- [x] No vis option-validation console errors (width/height passed as `px` strings).

## Implementation

- `static/js/graph/graph-export.js` (new) — `GraphExport.openDialog/closeDialog/exportPNG`.
  Rebuilds the rendered nodes/edges into a hidden N× `vis.Network` (physics off, frozen at
  `getPositions()`), because vis derives canvas resolution from `devicePixelRatio` only.
  Composites map layers (Canvas2D) then the offscreen vis canvas at 1:1.
- `static/js/graph/graph-background.ts` — added `getExportLayers()` (pure accessor for visible,
  decoded map layers); `graph-background.js` regenerated with `npm run build:ts`.
- `static/js/ui/world-export.js` — `saveFileWithDialog` maps `.png` → `image/png`.
- `templates/index.html` — script tag, toolbar button, More-menu item, `#graph-export-modal`.
- `tools/unit/run.cjs` + `tools/unit/test_graph-export.js` — 6 tests for crop/clamp/view-scale helpers.

## Verification

- `node tools/unit/run.cjs` → 85 passed (6 new).
- `npm run lint`, `npm run typecheck`, `python tools/js_module_index.py --check` → clean.
- Live browser check on the running app (kraktooth_goblin_camp, 162 nodes / 166 edges, 1 map layer):
  whole-graph 2× → 1296×1095 PNG (~2.7 MB); current-view 1× → 648×548 (~0.86 MB); background and
  nodes aligned.

## Notes

- Whole-graph scope keeps the viewport aspect ratio, so a wide graph can show letterbox bars.
- On native save-picker cancel, the success toast still fires (cancel is indistinguishable there).

