---
group: Graph & Area UX
type: task
status: in_progress
area: ui
priority: medium
created: 2026-07-27
wiki: "[[World Building/Graph System]]"
---

# Task 112: Cardinal Layout — Position Ways, Items, Characters; Auto-Reverse; Live Update

**Status**: in_progress (implementation done, testing pending)

## Summary

The cardinal layout (🗺️ Map button) was only positioning area nodes on the BFS grid. Everything else (ways, items, characters) was frozen at random vis.js positions — making the layout look broken. This task positions **all** node types, enables physics for items/characters, adds auto-reverse cardinal on way inspector, and live re-layout on cardinal change.

## Changes

### `static/js/graph/layout-engine.js` — rewritten `applyCardinalLayout()`

| Step | What it does |
|------|-------------|
| Area grid (kept) | Same BFS cardinal layout, rooms on 350×220 grid |
| Way midpoints (new) | Each way node positioned at pixel midpoint between its two connected rooms using `area_from`/`area_to` properties |
| Items near rooms (new) | Scans `location` edges from `worldState.graph.edges`, scatters items in 3-column grid below parent room, **physics enabled** (`physics: true`, `fixed: false`) |
| Characters near rooms (new) | Same via `location` edges, stacked vertically to the right of their room, **physics enabled** |
| Physics model (changed) | Global physics = ON. Areas/ways get per-node `physics: false` + `fixed: {x: true, y: true}` so they stay frozen. Items/chars settle naturally via edge springs. |

### `static/js/graph-manager.js`

- `toggleCardinalLayout()` — now sets `_physicsEnabled = true` always (was `false` when cardinal on), so `wasPhysics` triggers global physics re-enable after layout
- Removed dead `_applyCardinalLayout()` duplicate (107 lines, never called)

### `static/js/inspector/way-view.js` — auto-reverse cardinal + live re-layout

- Added `OPPOSITE_CARDINAL` mapping (north↔south, east↔west, etc.)
- Added `_updateCardinal()` helper — updates both A→B and B→A edges in one `Promise.all()`, then calls `worldState.fetch()`, then if cardinal layout is active, reloads the graph via `loadGraphData()`
- Both cardinal dropdowns now call `InspectorWayView._updateCardinal()`

### `static/css/style.css`

- Removed all map-view CSS (`.map-view`, `.map-area-card`, etc. — dead from task-111)

### `templates/index.html`

- Removed Map button from view-toggle and its script tag (task-111)

### `tools/test_ui.cjs`

- Removed map view `setViewMode('map')` test (task-111)

## Verification

- [ ] 🗺️ Map button places rooms on grid, ways at midpoints
- [ ] Items appear below their parent room in columns
- [ ] Characters appear to the right of their room
- [ ] Changing cardinal in way inspector auto-sets opposite direction
- [ ] Graph layout updates live when cardinal changes
- [ ] Toggling Map off returns to normal force-directed graph
- [ ] Items/characters have physics enabled and settle naturally
- [ ] Server starts clean, no 404s