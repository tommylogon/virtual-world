---
type: task
status: review
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

Current availability: implemented and live-verified 2026-10-18 on `raven_river`; see the observed lines under Steps to verify for the measurements.

Live steps when available:

1. Open an empty scope with a reference image and move the px/cell slider.
   - expected: The grid redraws live; larger px/cell yields fewer/larger cells and preserves image aspect.

2. Reach the sample counts with the slider and inspect generated/ungenerated state.
   - expected: Target counts are reachable without typing width and the control enables only in the intended state.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Open an empty scope with a reference image; move the `px / cell` slider.
   - expected: the grid redraws live; larger `px / cell` → fewer, larger cells; the count readout tracks it; the aspect stays the image's (no bands).
   - observed: scope `raven_river` (state `unmade`, grid `168×112`, reference `raven river.webp`, natural size `1536×1024`). Slider `min 9, max 1024, step 1`, opened at 9 (the node's own grid implies 9.14). Readout tracks: `9px → 171×114 · 1 cell ≈ 9px`, `77px → 20×13 · 1 cell ≈ 77px`, and the HUD dims button reads `168×112 · 1 cell = 1 turn ≈ 9px`. The grid layer's drawn extent, measured as the alpha bounding box of the Konva grid canvas, went 1885px → 224px wide for the `20×13` preview at an unchanged stage scale (0.509 both ways), so the redraw is live and the screen zoom did not move. Aspect is the image's by construction (`gridForCellSize` derives both axes from one unit); the unit test asserts `aspect === imgW / imgH`.
2. Reproduce the three-shot case: `1536×1024` image, drag the slider until the count reads ~`168×112`, ~`80×53`, ~`20×13`.
   - expected: the same counts are reachable by size alone, without typing a width or hitting `▦ match`.
   - observed: reachable by size alone, measured live: `77px → 20×13` (exact), `19px → 81×54`, `9px → 171×114`. `168×112` is **not** exactly reachable with a whole-pixel cell: `1536 / 168 = 9.14`, so the neighbouring stops are `9px → 171×114` and `10px → 154×102`. Every stop keeps aspect `1.5`, the image's.
3. Paint a few cells, then move the slider to shrink the grid.
   - expected: the existing prune count is shown before anything is lost; confirming drops the out-of-bounds cells.
   - observed: painted a fixture cell at `(30,50)` on the `168×112` grid, then previewed `20×13`. The prompt read `Resize the grid to 20×13 (1 cell ≈ 77px)? 1 painted cell(s) or placement(s) outside it will be removed. This can be undone.` Declining wrote nothing (the grid stayed `168×112` and the paint stayed put). The highlight was measured on the grid layer at the fixture's screen rect: **0** reddish pixels with no preview live, **156** with the `20×13` preview live, **0** again once the preview was cleared. A clean resize (`171×114`, nothing stranded) committed with no prompt.
   - limitation: a second fixture at `(167,111)`, the grid's far corner, drew **nothing visible** - the fitted view clips the grid's bottom edge (it shows rows ~6..99), so a stranded cell outside the viewport is counted but not shown. The count in the prompt still protects the author; see the work log.
4. Generate the scope, then return to the control.
   - expected: the cell-size control is disabled (the grid is now a live world).
   - observed: `world` (state `materialized`, grid `20×7`) → slider `disabled: true`, `title: "The grid is generated - ungenerate to re-key it"`, and it still shows the derived readout (`20×7 · 1 cell ≈ 77px`). `raven_river` (`unmade`) → enabled.

## Acceptance

- [x] A per-scope `px / cell` control sizes the grid; `w` / `h` are derived from the reference image's natural size, aspect locked, the count shown as a readout.
- [x] The grid redraws live while the control moves.
- [x] The control is available while the scope is ungenerated and disabled once generated.
- [x] If the grid is painted, a resize shows the prune count first (reuse existing machinery) and highlights the cells a shrink would drop, before commit.
- [ ] `▦ match` is subsumed (aspect always matches); no empty bands.
  - aspect is locked by construction and `▦ match` is now redundant, but the button is **kept**: the How section asks for confirmation before deleting it and none was available. Removing it is the remaining half.
- [x] Screen view zoom remains independent and unaffected.
- [x] The unit → `w/h` maths is unit-tested; live browser check on a real reference image.

## Files

- `static/js/worldpainter/editor.ts` — the HUD control, live redraw, `_gridFromReference`.
- `static/js/worldpainter/grid-model.ts` — `pxPerCell → {w, h}` (generalise `gridForImageAspect`), clamps.
- `tools/unit/test_worldpainter.js` — the new derivation.
- `engine/world_grid.py`, `routes/world_grid_ops.py` — the grid-set route keeps its `{w, h}` shape (the px unit is derived client-side).

## Work log (2026-10-18)

**What shipped.** `grid-model.ts` gains three pure functions: `gridForCellSize(imgW, imgH, pxPerCell)`
→ `{w, h, cells, aspect, pxPerCell}` with `gridForImageAspect`'s clamps (1 cell minimum, width
≤ 400, `MAX_GRID_CELLS`), `cellSizeForGrid(imgW, gridW)` for the slider's opening position, and
`cellSizeRange(imgW, imgH)` so the control cannot offer a stop the clamps would then silently
override. `strandedCount` was split into `strandedCells` (the set, with each entry's kind) plus a
`length` call, so the canvas highlight and the prompt's count are one definition rather than two
matching loops.

`editor.ts` adds the slider to the reference-image row (it needs a reference image to measure
against; absent without one). Dragging sets `state.cellSizePreview` and redraws through the
existing `_gridExtent` seam - the same candidate path the E/S/SE handle drag uses - so the frame,
the lattice (now drawn at the *candidate* extent, which it was not before) and the stranded
highlight all follow the drag. Releasing commits via `_commitGridSize`, factored out of
`_gridMouseUp`'s release so the slider and the handles share one commit path, one prompt and one
prune. The HUD dims readout gained the size half it never had (`168×112 · 1 cell = 1 turn ≈ 9px`),
filled in by the same sync hook that arms the slider once the reference image decodes.

**Decisions taken without confirmation, and why.**

- **`w` / `h` entry and the E/S/SE resize handles are kept.** The How section says "confirm before
  deleting either" and no confirmation was available, so nothing was deleted. They now duplicate the
  slider (aspect included) and are the obvious next cleanup.
- **No wheel binding.** The How section's wheel note says to confirm Konva is not already consuming
  it first; it was not verified, so the slider was not overlapped onto the wheel.
- **`▦ match` kept** for the same reason (see the acceptance box).

**Limitations found live, not fixed.**

- The stranded highlight draws at the stranded cells' own positions, so a cell outside the current
  viewport is counted but invisible. On `raven_river` the fitted view clips the grid's bottom edge
  (rows ~6..99 of 112), so a fixture at `(167,111)` highlighted nothing while one at `(30,50)`
  highlighted normally. Worth a follow-up only if it bites: an edge indicator or a fit to the union
  of both extents would fix it, and the prompt's count remains the guard.
- `168×112` from the card's own example is unreachable with a whole-pixel cell size (`9.14 px/cell`);
  the control's stops are `171×114` and `154×102`. If exact counts matter, the step would need
  sub-pixel cells.

**Verification.** `build:ts`, `typecheck`, `lint`, header survival and window guards all clean.
`node tools/unit/run.cjs`: 739 passed / 4 failed, and the 4 are the same 4 that fail on a clean
`master` worktree at `cb297187` (`test_graph_tuning.js` node size, `test_turn_prompts.js` × 2,
`test_worldpainter.js` floor layer) - all four are em-dash-versus-hyphen assertions in files this
change does not touch. `python tools/js_module_index.py --check` fails identically at HEAD (7
`engine/` modules missing the `@module` contract), so it is unrelated. The scratch scope
`raven_river` was restored to its exact original payload afterwards (grid `168×112`, every layer
empty, `map_offset {x:0, y:0}`, reference untouched) and `data/` has no changes.

## Audit note (2026-10-16)

Moved from inprogress back to todo: it was not being worked. No uncommitted changes in the working tree or in any of the eight git worktrees touch this card's files, and nobody is editing it. 0 of 7 acceptance boxes checked; the latest commit that mentions it is 3e9e1017 (2026-10-02), a combined worldpainter commit.
