---
type: task
status: review
area: world
priority: high
---

# task-520: WorldPainter scale: canvas grid surface, route tool, batch paint

**Filed:** 2026-09-24
**Related:** task-495, task-496

## Goal

Paint and navigate a massive world grid (16k+ cells) without DOM blowup or 10k area nodes: canvas-rendered grid, a route/trail tool with a cells-to-turns/hours readout, and one-request batch painting.

## Acceptance

- A grid far larger than the old 60×60 DOM cap renders and is navigable (pan/zoom) without one DOM node per cell.
- A route/trail is drawn from waypoints in a few clicks and reports its length in **cells · turns · hours** (1 cell = 1 turn, 60 turns/hour; 240 cells = 4 h 00 m).
- A route of hundreds of cells paints in a **single request** with a single undo entry.
- Every change is covered by tests and verified in a live browser.

## Progress — 2026-09-24

**Surface — Konva canvas** (`static/js/worldpainter/editor.js`, Konva 9 CDN):
the DOM-per-cell grid is replaced by a Konva stage with three layers and four
custom shapes (grid lines, paint, features, route). The shape count is constant,
so a 160×100 canvas costs the same as a 10×10; work is proportional to *painted*
cells (the payload is sparse). Pan/zoom, hit-testing and the transform are
Konva's — nothing hand-rolled. View (`x,y,scale`) is kept in component state so a
panel rebuild (paint/layer change) keeps the author's place. Grid lines drop out
below ~4 px/cell to avoid moiré.

**Route/trail tool**: a `🧭 Route` tool collects waypoints; the HUD shows a live
`route: N cells · N turns · H h MM m` readout and a **Paint route** button. The
line is rasterised with a Bresenham pass (`grid-model.lineCells`/`routeCells`,
pure + unit-tested) and painted through the new batch endpoint.

**Batch paint**: `engine/world_grid.paint_many` (all-or-nothing validation, so a
bad edit cannot half-paint a route) + `POST /api/world/scopes/<id>/grid/paint_batch`
(one undo snapshot). `grid-model.routeStats` converts cells → turns → hours.

**Grid presets** in the grid dialog (region 160×100, wide 180×70, small 60×60).

**Tests**: `tools/unit/test_worldpainter.js` (+3: Bresenham, route chaining/
de-dup, 240 cells = 4 h 00 m); `tests/test_world_grid_routes.py` (+2: atomic
batch, batch = one undo). Live browser run: mount (3 canvases), paint 1 cell,
route of 3 waypoints → **74 cells · 74 turns · 1 h 14 m**, applied in one request.

**Reference image (paint over the art)**: a per-scope `reference`
(`{image, opacity, visible}`) on the scope record, drawn by a Konva.Image in a
bottom layer beneath the grid lines — so you can load a zone's art as a reference
"when needed". The HUD has a picker, a visibility toggle and an opacity slider.
`GET /api/world/painter/backgrounds` offers the scenario's configured map layers
plus every file in `static/images/backgrounds`, so the existing art is reused
rather than re-uploaded; `POST .../grid/reference` sets/clears it. Reference-only:
it never compiles into areas/ways. Live check: selecting
`kraktooth-goblin-camp.png` mounted a 4th canvas whose centre pixel is the map at
50% alpha. Tests: `tests/test_world_grid_routes.py` (+2).

**Feedback round — drag paint, transparency, node-cost guard**:

- **Drag-to-paint**: paint/erase drag now lays a live stroke and commits it as
  **one batch** on mouse-up (the brush felt like "click and wait" before). Pan is
  **space-drag** (or the zoom/Fit buttons), so a stroke is never broken by a pan;
  a space key binding is added on open and removed on close. Verified: a 3×3
  brush dragged once painted 48 cells in a single request.
- **Paint transparency**: a HUD opacity slider (`state.paintAlpha`, default 0.75,
  0.15–1) so painted cells read over the reference art.
- **Node-cost guard**: `grid-model.estimateCompile(payload, merge)` (pure,
  unit-tested) mirrors the compiler and shows a live `≈ N areas · M ways` next to
  Generate; it turns amber past 3,000 and Generate asks for confirmation past it.
  The server refuses patches over `max_nodes` (default 20,000) **before** applying.

Still open (next slices):
- **Lazy/zone materialisation** is now the headline gap: a 200×133 world painted
  densely is ~5,300 areas + ~9,900 ways = ~15,000 nodes, which freezes the vis
  graph view — async transport does not help, only fewer/on-demand nodes does
  (task-400). Merge helps for non-traversed regions but destroys per-cell travel
  time, so it is not a general fix.
- **Align the grid to an anchored transform** (drag/scale/rotate, or reuse the
  `graph-background.js` transform + node `properties.x/y`): the reference image
  currently fills the grid bounds, so it is a guide, not yet registered to the
  illustration or the existing rooms' saved positions.
- **Lazy/chunked materialisation** so a massive map does not mint every area at
  once (task-400); the renderer already scales, the generation side does not.
- **rot.js** (adopt, do not hand-roll) for A*/FOV: per-agent fog of war and
  pathfound routes that avoid barriers rather than straight lines.
