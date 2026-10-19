# Graph Canvas & Network Manager UI Audit & Redesign Specification

> **Status: UNVERIFIED DRAFT (2026-10-19).** Written from file headers and partial reads. Line counts, wireframes and several failure claims were NOT measured or reproduced live. Treat every claim here as a lead to check, not a finding. Verified findings live in the task cards, not in this document.


**Surfaces:**
- Graph Network (`static/js/graph/network-manager.ts`) - 2,151 lines
- Layout Engine (`static/js/graph/layout-engine.ts`) - 1,840 lines
- Graph Toolbar (`static/js/graph/graph-toolbar.ts`) - 780 lines
- Relative Layout (`static/js/graph/relative-layout.ts`) - 620 lines
**Rendering Tech:** vis.js Canvas rendering to `<div id="network">`.

---

## 1. Measured Ground Truth & Architecture

The graph canvas renders the spatial and relational topology of the world:
- Nodes represent physical entities: `area`, `character`, `item`, `way`.
- Edges represent relations: `containment`, `traversal`, `holding`, `equipped`, `knows`.

### In-Place Sync vs Catastrophic Reloads
- AGENTS.md mandates: *Never rebuild on a state change. Update in place with `syncGraphData()`.*
- `syncGraphData()` diffs `worldState.graph` against `_graphNodesObj` and runs a batched `nodes.update()`.
- However, view toggles like `toggleEdgeLabels`, `setEdgeLabelSize`, `toggleImages`, and `_clearOverlay` still execute full dataset re-allocations (`setData()`), re-triggering simulation stabilization and causing camera jitter.

### Canvas vs DOM Disconnect
- vis.js draws directly to an HTML5 `<canvas>` element.
- There are **zero DOM elements** for individual nodes.
- Any attempt to find nodes via `document.querySelector('.vis-node')` returns 0.
- Tooltips, node badges, selection rings, and hover outlines must be projected mathematically via `network.canvasToDOM()`.

---

## 2. Usability & Layout Critique

### A. The "World Map Fog" Camera Fit Issue
- When switching from a small child scope (e.g. `goblin_camp` with 142 nodes) to the global scope (e.g. `world` with 2,763 nodes), vis.js fits the camera to the extreme bounding box.
- Areas become 2-pixel dots and character icons disappear completely. The user has to zoom in 800% manually to find where their character is standing.

### B. The 2,763 Node Freeze (Batching Failure)
- In older revisions, `GraphNetwork._applyNodeLabelDecorations` ran `nodes.update()` inside a per-node loop. Because vis.js redraws the canvas per update call, 2,763 nodes caused a **108,770 ms (1.8 minute) freeze**.
- While batching was introduced, tag filtering and edge label size changes still occasionally invoke unbatched passes across large edge sets.

### C. Confusing Multi-Layout Options
- The graph toolbar offers multiple conflicting layout modes:
  - `Free` (Force-directed physics simulation)
  - `Hierarchical` (Levels-based tree layout)
  - `Cardinal / Map Mode` (Spatial coordinate alignment)
- Toggling between them frequently scrambles manual node pins, and switching back to `Free` re-seeds the nodes into arbitrary random ring clusters.

---

## 3. Redesign Specification & Layout Blueprint

### Target Layout: Spatial Map with Contextual HUD

```
+----------------------------------------------------------------------------------------------------+
| [Scope Filter: Eldenford Town ▾]  [Layout: Spatial Map ▾]  [Physics: FROZEN]  [Nodes: 142 | Edges: 280] |
+----------------------------------------------------------------------------------------------------+
| CANVAS (vis.js Canvas with Smart Camera & LOD)                                                     |
|                                                                                                    |
|    [North Gate]                                                                                    |
|         │                                                                                          |
|         ▼                                                                                          |
|   [Town Square] ◄──────► [Blacksmith]                                                              |
|         │                                                                                          |
|         ▼                                                                                          |
|   [Tavern: Taproom] (Selected Node)                                                                |
|      ├── Thorne (Human PC)                                                                         |
|      └── Jerry (NPC)                                                                               |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
| FLOATING CONTROLS HUD (Bottom Left)            | SELECTION MINICARD (Bottom Right)                 |
| [ + Zoom In ] [ - Zoom Out ] [ ⊙ Focus Hero ]  | Area: Tavern Taproom                              |
| Filters: [x] Characters  [x] Items  [ ] Ways   | Contains: 2 characters, 5 items                   |
| LOD Tier: Full Details (Zoom: 1.2x)            | Actions: [ Inspect ] [ Teleport ] [ Enter Scope ]  |
+----------------------------------------------------------------------------------------------------+
```

### Core Architecture Upgrades

1. **LOD (Level of Detail) Dynamic Clustering**
   - At zoom scale < 0.3: Render area nodes as clean colored clusters; hide bare item nodes and minor ways.
   - At zoom scale >= 0.7: Render full character avatars, equipment chips, and edge labels.

2. **Camera Anchor to Controlled Character**
   - Provide a persistent `[⊙ Focus Player]` HUD button.
   - When switching scopes, auto-center the camera on the active player rather than computing an empty whole-world bounding fit.

3. **In-Place Edge Property Updates**
   - Migrate `toggleEdgeLabels` and `setEdgeLabelSize` to in-place `edges.update(batch)` instead of calling `loadGraphData()`.
