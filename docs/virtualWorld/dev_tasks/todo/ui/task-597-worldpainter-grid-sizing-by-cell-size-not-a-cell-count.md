---
type: task
status: todo
area: ui
priority: medium
---

# task-597: WorldPainter grid sizing by cell size (px/cell), not by cell count

**Filed:** 2026-09-30
**Reworked:** 2026-10-11 — sizing moves from a cell *count* to a cell *size* (`px / cell`).
**Related:** task-523, task-596, task-774

## What

Frame a scope's grid by the **size of a cell**, not by a `width × height` count.
A per-scope cell-size control (a slider, `px / cell` against the reference image)
derives the grid's `w` / `h` from the image's natural pixel size and redraws
**live** as it moves, so the author finds the right granularity by eye — *"one
cell ≈ a clearing"*, *"about the right amount of cells for this scope"* — in one
gesture, instead of guessing a column count or dragging handles against a
top-left origin.

The count becomes an **output**, not an input: `20×13 · 1 cell ≈ 77px`.

This reworks the first pass on this card (the frame / origin preview and the
E/S/SE handles). The preview is **kept**; the count-driven sizing is
**superseded**.

## Why

The grid is the scope's coordinate space, and one painted cell compiles to one
area (task-496). Today you size it two ways, and both invert or fight the thing
you actually care about — cell size:

- **Typing `w` / `h`** — the number you enter is a *count*, the **inverse** of
  cell size: bigger cells mean a *smaller* number. You guess, hit `▦ match`,
  look, and re-guess.
- **Dragging E/S/SE handles** — the origin is pinned at `(0,0)`, so resizing
  moves everything under the cursor; you micro-adjust size and position together
  to chase a look.

`▦ match` already locks the aspect to the image (it keeps the width and derives
the height), so the aspect half is solved. What is missing is choosing the
*scale* directly. Measuring the same `raven river` reference three ways —
`168×112`, `80×53`, `20×13` — the only thing that changed was cell size, and the
only way to change it was to turn the count the *other* way.

This matters as much for big interiors (a 600-room dungeon; a 200-room hotel with
halls, lifts, stairs, parking and a roof) as for wilderness — the control is
per-scope and assumes nothing about scope size.

## How

- **Control:** a per-scope cell-size slider labelled `px / cell`, in
  **reference-image pixels** (`imgW / w`). Clamp to the existing limits: 1 cell
  minimum; `MAX_GRID_CELLS = 20000` and width ≤ 400 maximum.
- **Derivation:** `w = round(imgW / pxPerCell)`, `h = round(imgH / pxPerCell)` —
  both from one unit, so the aspect is always the image's. This **subsumes
  `▦ match`** (`gridForImageAspect` becomes the degenerate "derive `h` from a
  given `w`" form). With `grid = img / cell`, the reference rect's
  `fitReferenceRect` collapses to 1:1, so the empty bands the aspect button was
  added to remove are gone by construction.
- **Live redraw:** moving the slider re-renders the grid on the image
  immediately; the count readout updates beside it.
- **Aspect is locked to the image.** No separate `▦ match` step. A grid
  deliberately *not* the image's ratio is out of scope for this card.
- **Lock once generated.** The control is available while the scope is
  *ungenerated*. Once the grid has been compiled into areas / ways
  (`properties.generated` / the scope is "made"), the control is **disabled** —
  you do not re-key a live world's coordinates. Before Generate it stays
  available: if the grid is painted, reuse the existing **prune count** warning
  (`grid-model.pruneGrid` / `strandedCount`) so a shrink shows what it will drop.
  Painted-but-ungenerated is the author's call, and a warning is enough. Beyond
  the count, show **which** cells would fall outside (highlight the stranded
  set live as the slider moves) so a shrink is seen before it is committed.
- **Keep the frame / origin preview** shipped on this card (bold frame,
  `0,0 · W×H` marker, shaded painted-content box) — it is what makes the live
  redraw legible.
- **Supersede the count-driven sizing.** The `w` / `h` entry and the E/S/SE
  resize handles are demoted: sizing by *cell size* replaces them. The `✥ grid`
  handles stay for **map offset** (task-523) only. (Confirm before deleting
  either.)
- **View zoom stays separate.** Screen zoom (`＋` / `−`, Konva `scale`, base
  `CELL = 22`) is "how big cells look"; cell size is "how many cells the scope
  has". They read the same but must not be conflated. Wheel is not hand-bound in
  the editor today; if the wheel is to drive cell size rather than view zoom,
  confirm Konva is not already consuming it first.
- **Unit + geometry are pure** and unit-tested, like `gridForImageAspect` and
  `pruneGrid` already are. The `px / cell` unit is derived client-side and need
  not persist — the stored shape stays `{w, h}`.

## Browser UI and intended live verification

Intended UI home: Build → WorldPainter → grid controls for a scope with a reference image.

Current availability: The px/cell sizing control and live redraw behavior are still in progress.

Live steps when available:

1. Open an empty scope with a reference image and move the px/cell slider.
   - expected: The grid redraws live; larger px/cell yields fewer/larger cells and preserves image aspect.

2. Reach the sample counts with the slider and inspect generated/ungenerated state.
   - expected: Target counts are reachable without typing width and the control enables only in the intended state.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Open an empty scope with a reference image; move the `px / cell` slider.
   - expected: the grid redraws live; larger `px / cell` → fewer, larger cells; the count readout tracks it; the aspect stays the image's (no bands).
   - observed: TODO
2. Reproduce the three-shot case: `1536×1024` image, drag the slider until the count reads ~`168×112`, ~`80×53`, ~`20×13`.
   - expected: the same counts are reachable by size alone, without typing a width or hitting `▦ match`.
   - observed: TODO
3. Paint a few cells, then move the slider to shrink the grid.
   - expected: the existing prune count is shown before anything is lost; confirming drops the out-of-bounds cells.
   - observed: TODO
4. Generate the scope, then return to the control.
   - expected: the cell-size control is disabled (the grid is now a live world).
   - observed: TODO

## Acceptance

- [ ] A per-scope `px / cell` control sizes the grid; `w` / `h` are derived from the reference image's natural size, aspect locked, the count shown as a readout.
- [ ] The grid redraws live while the control moves.
- [ ] The control is available while the scope is ungenerated and disabled once generated.
- [ ] If the grid is painted, a resize shows the prune count first (reuse existing machinery) and highlights the cells a shrink would drop, before commit.
- [ ] `▦ match` is subsumed (aspect always matches); no empty bands.
- [ ] Screen view zoom remains independent and unaffected.
- [ ] The unit → `w/h` maths is unit-tested; live browser check on a real reference image.

## Files

- `static/js/worldpainter/editor.ts` — the HUD control, live redraw, `_gridFromReference`.
- `static/js/worldpainter/grid-model.ts` — `pxPerCell → {w, h}` (generalise `gridForImageAspect`), clamps.
- `tools/unit/test_worldpainter.js` — the new derivation.
- `engine/world_grid.py`, `routes/world_grid_ops.py` — the grid-set route keeps its `{w, h}` shape (the px unit is derived client-side).

## Audit note (2026-10-16)

Moved from inprogress back to todo: it was not being worked. No uncommitted changes in the working tree or in any of the eight git worktrees touch this card's files, and nobody is editing it. 0 of 7 acceptance boxes checked; the latest commit that mentions it is 3e9e1017 (2026-10-02), a combined worldpainter commit.
