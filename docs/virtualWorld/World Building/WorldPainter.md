---
type: doc
tags: [system/graph]
---

# WorldPainter

**Tasks:** [[dev_tasks/review/world/task-495-worldpainter-recursive-scope-grids-and-3-mode-editor|task-495]] (recursive scope grids, 3-mode editor) · [[dev_tasks/review/world/task-520-worldpainter-scale-canvas-grid-surface-route-tool-batch-paint|task-520]] (canvas surface, route tool, batch paint) · [[dev_tasks/review/ui/task-540-worldpainter-cell-inspector-hover-or-click-a-cell-to-read-what-is-on-it|task-540]] (cell inspector)

WorldPainter is the editor that paints a **[[World Scopes|scope]]'s grid**: layers of
biome / road / floor / climate, keyed by `"x,y"` cell, stored on the scope record in the
save. It is an authoring surface only — the grid is inert data until
[[Grid to Graph|Grid to graph]] compiles it — but it is the same data the runtime later
reads, so a painted cell is a real place rather than a picture of one.

Two files implement it, both plain browser-global modules:

| Module | Role |
|--------|------|
| `static/js/worldpainter/editor.js` (3095 lines) | the overlay: rail, canvas, palette, grid dialog, drill-down, every `POST` |
| `static/js/worldpainter/grid-model.js` | the view-model: cell keys, row rendering, layer colours, storey reads, compile estimate |

Opened from JS as `window.VW.worldPainter.open(scopeId)` (`editor.js:3093`).

---

## The three fixed sets

### 8 tools — `editor.js:746`

`TOOLS` is a literal array of `[id, label, key, hint]`, and there are exactly **8**
entries. Each has a keyboard shortcut and a HelpCenter card (`editor.js:781` wires
`_help(btn, 'wp-tool-' + id)`).

| id | Label | Key | What it writes |
|----|-------|-----|----------------|
| `select` | ⬚ Select | `V` | selection only; Paint/Erase then apply to the whole selection in one request |
| `paint` | 🖌 Paint | `P` | current layer + value; drag to stroke |
| `erase` | 🧽 Erase | `E` | clears the current layer on a cell |
| `move` | ✥ Move | `M` | shifts the selection's contents one cell; clamped, one undo |
| `route` | 🧭 Route | `R` | clicks waypoints, then ✓ Paint route — Bresenham line, 1 cell = 1 turn (`grid-model.js:196-213`) |
| `feature` | 🏠 Feature | `F` | places a **child scope** on a cell (not a road — roads are paint) |
| `area` | 📍 Area | `A` | puts an **area you already wrote** onto a cell; the compiler will not mint a second one there |
| `inspect` | 🔍 Inspect | `I` | reads a cell without changing it; right-click does this on any tool |

They render as a **vertical rail** down the left of the canvas (`_toolRail`,
`editor.js:768`) rather than a toolbar — the layer/value/brush controls stayed in the top
row because they belong to the four *write* tools, not to whichever tool is active
(`editor.js:733-745`).

### 3 modes — `grid-model.js:24`

```js
const MODES = ['world', 'town', 'interior'];
```

The backend is the source of truth: `world_grid.MODES`, served in the vocabulary payload
(`routes/world_grid_ops.py:321`). A mode is set in the **▦ Grid…** dialog and `POST`ed
with the grid size (`editor.js:3072`), so it is a property of the scope record, not of the
editor session. `nextMode()` (`grid-model.js:126-129`) is the drill-down ladder: opening a
child feature steps `world → town → interior`.

Mode is not cosmetic. `world_compile.compile_grid` reads it at `world_compile.py:1552` and
`outdoor = mode == "world"` gates cliffs, climate, and the `outdoor` tag; a `town` or
`interior` scope is built space, where a storey step is a staircase rather than a rockface.

### 4 layers — `world_grid.PAINT_LAYERS`

Declared once, in Python:

```python
PAINT_LAYERS = ("biome", "road", "floor", "climate")   # engine/world_grid.py:141
```

`grid-model.js:28` mirrors that tuple in the order it renders the layer `<select>`
(`editor.js:1064-1080`), and `world_grid.paint()` / `paint_many()` refuse anything not in
it (`world_grid.py:540`, `:572`) — so the layer list cannot drift without breaking a write.
The vocabulary endpoint sends the tuple straight from Python
(`world_grid_ops.py:320`) rather than letting the editor own a copy.

| Layer | Value | Compile meaning |
|-------|-------|-----------------|
| `biome` | a taxonomy id | the cell's terrain, its tags, its surface |
| `road` | a feature id | **replaces** the biome as the cell's identity; one place per cell |
| `floor` | an integer storey | 0 ground, 1 up, −1 down, unbounded; also splits regions and makes a step a `stairs` way |
| `climate` | one of five coarse ids | aggregated per region into `environment.base_temperature` |

`floor` is a **storey index, not a floor material** — what you stand on is `surface`, read
from the biome/road record (`engine/biomes.py::ground_surface`). The earlier revision that
put material on `floor` was wrong and is gone (`world_compile.py:54-62`).

---

## The palette taxonomy

The palette is **data, served from the backend**: `GET /api/world/painter/vocabulary`
(`routes/world_grid_ops.py:287-322`) returns `biomes`, `features`, `climates`,
`default_climate`, `layers` and `modes`. Those ids come from the taxonomy file
`data/worldpainter/biomes.json`, loaded by `engine/biomes.py` (`DATA_PATH`,
`biomes.py:35-38`). The editor holds no vocabulary of its own — `state.vocab` starts empty
(`editor.js:248`) and is filled from that endpoint (`editor.js:242`), which is why a
mis-typed id is impossible rather than merely warned about.

Grouping is computed in the editor from each record's `tags`, because the backend sends
tags for exactly this reason (`world_grid_ops.py:295-299`). `_biomePalette`
(`editor.js:341-396`) emits **`<optgroup>`** sections in this order:

1. **wild terrain** — no `building` tag, flat,
2. **Rooms** — `indoor` tag, grouped by `ROOM_PURPOSES` (14, circulation first),
3. **Buildings** — `building` tag, grouped by `CATEGORIES` (9: residential, religious,
   commercial, civic, craft, industrial, military, rural, transport),
4. **Structure** — `not_a_place` tag: wall, void, window, door, stairway.

Two things ride along from the same functions the compiler uses: each building's `refusal`
line comes from `world_compile.building_refusal` (`world_grid_ops.py:306`), and each
climate's base °C comes from `world_grid.CLIMATE_BASE_C` (`:317`) — one implementation, so
the painter and the world cannot disagree.

The structural categories (place / structure / indoor / building / stair) are **not** the
editor's judgement: `biomes.cell_kind()` (`biomes.py:149`) decides what a cell may be, and
an id the taxonomy does not know is treated as a place, not a hole (`biomes.py:156-159`).

---

## Reads and writes

Every write is one `POST` under `/api/world/scopes` (`routes/world_grid.py`):

| Endpoint | Handler |
|----------|---------|
| `GET /api/world/scopes/<id>/grid` | `_grid_payload` (`world_grid_ops.py:220-254`) |
| `POST …/grid` | size, `cell_scale`, `mode` |
| `POST …/grid/paint`, `…/paint_batch` | single stroke / one request for a whole selection |
| `POST …/grid/name` | author-set name on a cell (a `names` map, not a 4th layer) |
| `POST …/grid/place`, `…/place_area`, `…/unplace_area` | Feature / Area tools |
| `POST …/grid/generate`, `…/ungenerate` | compile / uncompile — see [[Grid to Graph]] |

The payload carries more than paint: `placements`, `area_placements`,
`boundary_overrides`, `boundary_ways`, `unplaced_areas`, `children`, `breadcrumb`, and
`blockers` — the compiler's own preflight advice, so a scope that cannot compile says so
**before** the Generate click (`world_grid_ops.py:250-253`; rendered at `editor.js:1107`).

Undo is one snapshot per request: a move, a marquee batch and a route stroke are each a
single POST, so each is a single undo step.

---

## Known constraints

- **Empty layers are absent, not empty.** `_grid_payload` sends
  `dict(rec.get("layers") or {})` (`world_grid_ops.py:238`), so a grid with no climate
  paint has no `climate` key at all. The view-model treats a missing layer as empty
  throughout (`grid-model.js:286`, `:316-322`) — filed as
  [[dev_tasks/todo/world/task-651-painter-grid-payload-omits-the-floor-and-climate-layers-when-they-are-empty|task-651]].
- **Names are not a layer.** There is no name vocabulary; a name is a value in the
  `names` map beside `layers` (`grid-model.js:258-266`), and the eraser does not clear it.
- **Zoom is capped** —
  [[dev_tasks/todo/ui/task-595-cap-how-far-the-worldpainter-view-can-be-zoomed-out|task-595]].
- **The grid preview cannot be moved or resized yet** —
  [[dev_tasks/todo/ui/task-597-worldpainter-better-grid-preview-with-drag-to-move-and-handles-to-resize|task-597]].
- **Preflight must be kept in step with the compiler.** `preflight()` says so in its own
  docstring: a `block` must be a condition `compile_grid()` refuses, or one it will refuse
  once the stated remedy is applied; anything advisory belongs at `warn`
  (`world_compile.py:1345-1351`).
- **A biome id the taxonomy does not know compiles anyway**, to a bare place, and is
  listed in the generate report as a warning rather than swallowed
  (`world_compile.py:1627-1632`).

---

## Code map

| Module | Role |
|--------|------|
| `static/js/worldpainter/editor.js` | tools, rail, palette, canvas, grid dialog, all POSTs |
| `static/js/worldpainter/grid-model.js` | cell keys, rows, layer colours, storey reads, area estimate, cell inspector |
| `routes/world_grid.py` | 22 route registrations (thin) |
| `routes/world_grid_ops.py` | handlers, `_grid_payload`, vocabulary |
| `engine/world_grid.py` | the record: `PAINT_LAYERS`, `CLIMATE_BASE_C`, paint/place/name normalisation |
| `engine/biomes.py` | the taxonomy (`data/worldpainter/biomes.json`) and `cell_kind` |
| `engine/world_compile.py` | the consumer — see [[Grid to Graph]] |
| `tools/unit/test_worldpainter.js` | the view-model's unit tests (`npm run unit`) |

---

## Related docs

- [[Grid to Graph]] — what Generate does with the painted cells
- [[World Scopes]] — the record being painted, and placement/promotion
- [[Graph System]] — the graph the compile writes into
- [[Millbrook Falls Town Map]] — a painted world as it reads in play
- `docs/design/worldpainter-knowledge-and-fog.md` — "WorldPainter grids, belief-based travel, and fog of war", the target architecture (cited as a path: `docs/design/` is outside the note vault)

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Read next** — [[Grid to Graph#The pipeline]]

**Features** — [[worldpainter|WorldPainter]] (#47)

**Neighbouring notes** — [[Doors & Connections]], [[Generated Scenario Review (2026-08)]], [[Graph System]], [[Grid to Graph]], [[Millbrook Falls Town Map]], [[Rooms & Areas]]

<!-- connected:end -->
