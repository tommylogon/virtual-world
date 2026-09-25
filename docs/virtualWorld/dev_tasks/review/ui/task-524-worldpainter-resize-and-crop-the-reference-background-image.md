---
type: task
status: review
area: ui
priority: high
---

# task-524: WorldPainter: resize and crop the reference background image

**Filed:** 2026-09-25
**Related:** 

## Goal

WorldPainter's reference image only has image/opacity/visible and is auto-fitted to the grid. Add scale/offset/crop handles (mirror the graph background's crop UX) and persist them on the scope reference, so the painter and the graph 'fit to painted grid' action share the same geometry.

## Acceptance

- [x] Reference stores a destination `rect` in **cell** units and a normalized
      `crop` window, validated/clamped server-side (`world_grid.set_reference`,
      `reference_rect`, `reference_crop`).
- [x] Painter **✥ adjust** mode: drag the picture to move, corner handles resize
      (scale), edge handles crop (cut, keeps content scale); **⤢ reset** returns
      to auto-fit.
- [x] Layout persists through `POST /api/world/scopes/<id>/grid/reference`
      (`rect`, `crop`, `reset`); a changed image auto-fits.
- [x] Graph **▦ Fit to painted grid** maps the same rect through
      `GraphLayoutEngine.mapSpacing()` and copies the crop, so painter and graph
      show the same geometry.
- [x] Tests: `tests/test_world_grid.py` (+4 model), `tools/unit/test_worldpainter.js`
      (+3 pure geometry: `fitReferenceRect`, `referenceHandleDrag`,
      `referenceHandlePoints`).

## Progress — 2026-09-25

Rect is stored in cells (not px) so the painter (22px/cell) and the graph map
layout (`mapSpacing` px/cell) can each draw it in their own space and still
agree. `null` rect = auto-fit. Corners scale the whole picture; edges cut it by
following the pointer and shrinking the source window proportionally. Pure
geometry lives in `grid-model.js` (unit-tested); the Konva handles/hit-test and
persistence live in `editor.js`.
