# WorldPainter UI & Usability Roadmap

A consolidated roadmap of existing tasks targeting WorldPainter usability, palette organization, grid sizing, and canvas performance.

---

## 1. Active & Foundational Polish

- **task-776: WorldPainter polish and performance: soft-render Konva offscreen, paint palette side dock, and cheap workflow wins**
  - **Status:** In Progress
  - **Scope:** Solves viewport render hitching, docks the floating palette properly to the side pane instead of covering the canvas, and streamlines tool switching.

---

## 2. Palette & Tool Usability (Finding & Selecting Tiles)

- **task-647: WorldPainter cell palette: no search or filter across 105 tiles**
  - **Status:** Open
  - **Scope:** Adds instant search and keyword filtering to the palette so authors don't have to scroll through 100+ tiny tiles looking for a specific biome, room, or track.
- **task-774: WorldPainter palette: filter by layer, mode, and setting**
  - **Status:** Open
  - **Scope:** Context-filters the palette based on the active scope mode (`world`, `town`, `interior`). Hides regional biomes when painting an interior cave, and hides room interiors when painting overland wilderness.
- **task-759: WorldPainter biome palette: illustrated tile grid, category rail, and a rich detail panel**
  - **Status:** Open
  - **Scope:** Replaces the flat grid with an organized category rail (Wilderness, Aquatic, Subterranean, Civic) and adds a detail HUD showing what resources/tags a tile compiles to.
- **task-648: Biome palette has two different civic groups (room purpose vs building category)**
  - **Status:** Open
  - **Scope:** Consolidates redundant taxonomy groups in the palette schema.
- **task-719: WorldPainter per-tool brush options: brush hover outline, toolbar layout fix**
  - **Status:** Open
  - **Scope:** Renders a visible hover outline showing exact brush size and bounds on the canvas, and fixes button crowding on the top toolbar.

---

## 3. Grid Resizing, Navigation & Viewport Controls

- **task-717: WorldPainter grid resize: numbered WxH fields are buried while drag handles are imprecise**
  - **Status:** Open
  - **Scope:** Surfaced explicit Width x Height numeric inputs directly in the top bar rather than burying them inside a modal.
- **task-597: WorldPainter grid sizing by cell size, not a cell count**
  - **Status:** Open
  - **Scope:** Clearer spatial units and bounds checking so resizing does not unintentionally strand or delete border cells.
- **task-595: Cap how far the WorldPainter view can be zoomed out**
  - **Status:** Open
  - **Scope:** Enforces a sane zoom-out clamp so the canvas cannot shrink into an unusable speck.
- **task-580: Unmade scope generate affordance and generation preview**
  - **Status:** Open
  - **Scope:** Adds a one-click preview and status badge to child feature cards before committing generation.

---

## 4. Inspection & Placement Clarity

- **task-540: WorldPainter cell inspector: hover or click a cell to read what is on it**
  - **Status:** Open
  - **Scope:** Dedicated inspector HUD that breaks down everything on the hovered cell across layers (Biome, Elevation/Storey, Road/Feature, Placed Child Scope).
- **task-541: WorldPainter area picker: show what is placed here and what belongs to this scope only**
  - **Status:** Open
  - **Scope:** Restricts the candidate list in the unplaced area drawer to the current scope rather than dumping every global node.
