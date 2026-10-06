---
type: task
status: done
area: ui
priority: medium
---

# task-719: WorldPainter: per-tool brush options, brush hover outline, toolbar layout fix

**Filed:** 2026-10-06
**Related:** worldpainter editor.ts

## Goal

Move brush size selector into per-tool rail options, add dashed white brush hover preview outline on grid, and fix toolbar layout so it no longer blocks the grid below it.

## Acceptance

- [x] Brush size selector lives in the per-tool rail options (paint/erase/route), not the shared toolbar
- [x] Dashed white hover outline shows the cells the brush would cover, for paint and erase, tracking the pointer and clipping to the grid edge
- [x] Toolbar is single-row with horizontal scroll; it no longer wraps and blocks the grid below
- [x] The what-next checklist reports from below the map, not between the toolbar and the art

**Evidence (live, 2026-10-06):** the outline was dead code — drawn at
the end of `_drawRoute`, below the route early-return, so with no route
in progress the redraw never reached the canvas context. Moved above
the return. Measured in the browser: 0 outline pixels at rest, ~2900
dashed pixels on hover; the outline box tracks the pointer across the
grid (339-575 x 178-335 at cell (2,0), 1527-1763 x 812-968 at cell
(17,9)) and a 3x3 brush at the top row correctly draws 3x2 (edge
clipped); contrast 4.4-6.6 against map content. `python
tools/ts_convert.py check`: build/typecheck/lint/unit/header survival/
window guards all ok (module:check failure is the pre-existing
a394b51e debt, unrelated).
