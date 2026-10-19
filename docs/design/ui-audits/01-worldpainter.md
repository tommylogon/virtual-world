# WorldPainter UI Audit & Redesign Specification

> **Status: UNVERIFIED DRAFT (2026-10-19).** Written from file headers and partial reads. Line counts, wireframes and several failure claims were NOT measured or reproduced live. Treat every claim here as a lead to check, not a finding. Verified findings live in the task cards, not in this document.


**Surface:** WorldPainter Modal & Canvas (`static/js/worldpainter/editor.ts`, `grid-model.ts`)
**Lines of Code:** 4,315 lines (editor.ts) + 1,192 lines (grid-model.ts)
**Rendering Tech:** Konva.js (HTML5 Canvas wrapper) mounted in a full-screen DOM dialog.

---

## 1. Measured Ground Truth & Current Architecture

WorldPainter mounts inside `#worldpainter-modal` via `showModal()`. 

### The Lifecycle Flaw
- Every single mutation (stroke commit, tool select, brush size change, cell inspect, area selection) calls `render()`.
- `render()` completely clears `box.innerHTML = ""` via `_renderShell()`, rebuilds the toolbar, rebuilds the palette, unmounts the Konva Stage, creates a brand new `new K.Stage()`, and re-binds DOM event handlers.
- A `requestAnimationFrame` scroll-capture hook attempts to restore scroll position, creating visible layout flicker on every paint stroke.

### Component Inventory
- **Header & Breadcrumbs:** `_breadcrumb()` (line 1160).
- **Toolbar:** `_toolbar()` (lines 1505-1644). 17 discrete inline controls packed into one flex row.
- **Palette Panel:** `_palettePanel()` (lines 1715-1820). 26 category buttons, search box, tile grid, detail box.
- **Left Tool Rail:** `_toolRail()` (lines 1202-1225). 8 tool buttons + dynamic sub-options.
- **Canvas Viewport:** `_grid()` / `_mountGrid()` (lines 2301-2370). Konva stage, 4 layers (`refLayer`, `bg`, `paint`, `decor`).
- **Footer:** `_checklist()` (lines 1420-1503), `_renderChildren()`, and `_status()` (line 1152).

---

## 2. Ruthless Usability & Layout Critique

### A. The Scroll & Fold Disaster
- In standard 1080p desktop viewports, the modal content is rendered as a vertical document block:
  `[Breadcrumbs] -> [Toolbar (1-2 wrapped rows)] -> [Palette (up to 380px tall)] -> [Canvas (480px tall)] -> [Checklist] -> [Child scopes]`.
- When the palette is opened to select a tile, the canvas is shoved completely below the viewport fold. The user is forced to scroll down to paint, scroll up to pick another tile, and scroll down again to see the result.

### B. Toolbar Clutter & Duplication
- **Duplicate Grid Controls:** Two buttons exist side-by-side: `■ Grid...` (opens modal) and `✥ grid` (toggles interactive handle overlays). Neither clearly explains the difference without reading tooltips.
- **17 Buttons on One Line:** Mode pill, layer dropdown, value picker swatch, grid modal, grid adjust toggle, add feature button, blockers badge, paint interior button, merge checkbox, sibling traversal checkbox, compile estimate counter, Generate button, Ungenerate button, and Refresh button fight for horizontal space. On displays < 1920px wide, this flexbox wraps into an uneven 3-line block.

### C. State Leaks & Discrete Placement Mishaps
- **Global Brush Size:** `state.brush` is shared. Setting brush to 5x5 in Paint mode persists into `feature` (child scope placement) and `area` (authored area placement), causing users to accidentally place clusters of duplicate area markers across a 5x5 footprint.
- **Erase tool blind spot:** `erase` only removes raster layer values (`biome`, `road`, `floor`, `climate`). Placed child scopes (`p.placements`) and areas (`p.area_placements`) cannot be cleared with the eraser, forcing authors to hunt through the area rail.

### D. Palette Category Overkill
- `paletteSections` generates 26 categories unconditionally:
  - 6 Wild terrain groups
  - 14 Room purpose groups (`Rooms · Living`, `Rooms · Circulation`, `Rooms · Sleeping`, etc.)
  - 9 Building categories (`Buildings · Residential`, `Buildings · Commercial`, etc.)
- When editing a wilderness scope like `deep_woods` (scope mode `world`), all 14 room categories are rendered, cluttering the view with domestic interior tiles.

### E. Blind Elevation Painting
- Painting the `floor` layer requires typing integers into an input box (`+1`, `-1`, `2`) and clicking individual cells. There is no ramp tool, slope generator, or heightmap import/export, making large topography creation painfully slow.

---

## 3. Redesign Specification & Layout Blueprint

### Target Layout: The 3-Column Studio

```
+----------------------------------------------------------------------------------------------------+
| [Scope Breadcrumb: World > Eldenford > Deep Woods]                     [Mode: World] [Generate] [X] |
+-----------------------+----------------------------------------------------+-----------------------+
| TOOL RAIL (Left)      | CANVAS VIEWPORT (Center - Fixed 100% Height)       | INSPECTOR & PALETTE   |
| 56px wide             | Flexible pan & zoom, Konva stage never unmounts     | 320px dockable drawer |
|                       |                                                    |                       |
| [ Select   (V) ]      | +------------------------------------------------+ | [ Palette ] [ Layers] |
| [ Paint    (P) ]      | | Grid Rulers (Top & Left)                       | | Search: [__________]  |
| [ Erase    (E) ]      | |                                                | | Categories:           |
| [ Route    (R) ]      | |                                                | | [x] Forest (12)       |
| [ Box Fill (B) ]      | |       Active Scope Grid                        | | [ ] Water (6)         |
| [ Area     (A) ]      | |       (No vertical document scroll)            | | [ ] Mountain (8)      |
| [ Feature  (F) ]      | |                                                | | (Interior biomes      |
| [ Eyedrop  (I) ]      | |                                                | |  hidden in World mode)|
|                       | +------------------------------------------------+ |                       |
| --- Tool Options ---  | HUD Overlay:                                       | Tiles:                |
| Brush: [ 1x1 | v ]    | Pos: (14, 22) | Biome: dense_forest | Elev: 0     | [G] [D] [T] [R]       |
| (Clamped on A/F/R)    | Compile Est: 142 areas, 280 ways                   | [G] [D] [T] [R]       |
+-----------------------+----------------------------------------------------+-----------------------+
| STATUS BAR: [✓ Ready] [Sibling Traversal: ON] [Merge Biomes: ON] [Heightmap: Import/Export]        |
+----------------------------------------------------------------------------------------------------+
```

### Core Architecture Upgrades

1. **Persistent Konva Stage (Soft Render)**
   - Do not call `new K.Stage()` on every paint stroke.
   - Stage mounts once. Only `paintShape` and `decorShape` redraw on stroke commits.
   - Background grid lines and reference images stay cached.

2. **Mode-Gated Palette Rail**
   - In `world` mode: Render only Wild Terrains (`forest`, `grass`, `water`, `rock`, `coast`, `farm`).
   - In `town` mode: Render Streets, Walls, Building Footprints, Yards, Plazas.
   - In `interior` mode: Render Rooms and Interior Architecture.

3. **Tool Footprint Clamping**
   - `state.brush` applies strictly to `paint`, `erase`, and `box`.
   - Discrete placement tools (`area`, `feature`, `route`, `inspect`) force brush footprint to 1x1.

4. **Heightmap Import / Export**
   - **Export:** Read `p.layers.floor`, map min/max elevation to 0-255 grayscale, export as PNG.
   - **Import:** Read image file, sample pixels to grid dimensions `(w, h)`, quantize luminance to elevation integers, commit in one batch.
