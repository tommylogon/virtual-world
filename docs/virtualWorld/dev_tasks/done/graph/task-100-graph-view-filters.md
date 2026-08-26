---
group: Graph & Area UX
wiki: "[[World Building/Graph System]]"
---
# Task 100: Graph View Overlays — Light, Heat, Sound, Triggers, Cardinal

**Status**: Done  
**Priority**: High  
**Filed**: 2026-07-24  
**Updated**: 2026-07-31  

## Summary

The graph currently shows one view — the structural room/door/item/character relationships. Add a view selector with different visual overlays to show environmental data, trigger propagation, and spatial relationships.

## Key Design Decision

All 5 overlays are computed **entirely on the frontend** from existing `worldState` data. No API endpoints needed. The engine's Python `get_ambient_light()` is for runtime gameplay (room descriptions, examine, narration) — the graph view is a visualization tool for builders.

## View Types

### 1. Structural View (current default)
Rooms → ways → items, characters. Shows graph topology with type-based coloring.

### 2. Light Overlay
- Area nodes colored by computed light level (spill through open/see_through ways included)
- Items with `state: lit` glow orange
- Color ramp: `pitch_black` → black, `dim` → dark indigo, `normal` → default gray, `bright` → golden, `blinding` → white
- Spill math reimplemented in JS: for each open/see_through door, darker room gets `brighter * 0.5` boost

### 3. Heat Overlay
- Area nodes colored by temperature (below freezing → ice blue, cool → blue, comfortable → green, warm → orange, hot → red, blazing → deep red)
- Heat sources (items with `state: lit`, fireplaces) glow
- Propagation through open ways with linear falloff

### 4. Sound Overlay
- Area nodes colored by noise level (silent → dark, quiet → dim, moderate → normal, loud → bright, deafening → white)
- Sound-emitting items highlighted
- Propagation through open ways with distance falloff

### 5. Trigger Overlay
- Nodes with trigger edges highlighted, others dimmed to 20% opacity
- Trigger edges shown with purple color and trigger type label
- Non-trigger edges dimmed/hidden

### 6. Cardinal Overlay
- Way nodes labeled with cardinal direction (N/S/E/W/NE/NW/SE/SW)
- Area positions arranged geographically using existing cardinal layout
- Useful for spatial navigation planning and debugging

## Implementation

### Frontend

- `static/js/graph/network-manager.js` — add `applyOverlay(mode)`, per-overlay restyle functions, per-view legend builder
- `static/js/graph-manager.js` — extend `setViewMode()` to handle overlay modes without hiding vis.js canvas
- `templates/index.html` — add overlay view buttons to graph toolbar (dropdown or compact buttons)
- `static/css/style.css` — styles for overlay indicator, per-view legend variants

### How It Works

Each overlay:
1. Gets node/edge DataSets from `graphManager.network.body.data`
2. Computes colors from `worldState.rooms`, `worldState.graph.nodes`, `worldState.graph.edges`
3. Calls `nodes.update()` and `edges.update()` to apply colors/visibility
4. Swaps legend content to match current view

Switching back to Structural view clears the overlay by force-reloading graph data (which preserves node positions thanks to the save/restore in `loadGraphData`).

## Files Affected

- `static/js/graph/network-manager.js` — add overlay functions (~150 lines)
- `static/js/graph-manager.js` — extend setViewMode (~20 lines)
- `templates/index.html` — add overlay buttons (~5 lines)
- `static/css/style.css` — overlay legend variants (~20 lines)

## Dependencies

None — everything is frontend-only from existing state data. Task-80 (light spill system) backend code is not required.

## Tests

- Each overlay renders without errors
- Switching between overlays is instant
- Switching back to Structural restores original colors
- Light overlay colors match computed spill values

---

## Implementation Summary (2026-07-31)

All overlays fully implemented and verified:

| Component | Location |
|-----------|----------|
| `applyOverlay()` dispatcher | `network-manager.js:713` |
| Light overlay + spill propagation | `network-manager.js:488` (`_applyLightOverlay()`), `:406` (`_computeAmbientLight()`) |
| Heat overlay | `network-manager.js:515` (`_applyHeatOverlay()`) |
| Sound overlay | `network-manager.js:541` (`_applySoundOverlay()`) |
| Trigger overlay | `network-manager.js:560` (`_applyTriggerOverlay()`) |
| Cardinal overlay | `network-manager.js:610` (`_applyCardinalOverlay()`) |
| Overlay view buttons (dropdown) | `templates/index.html:115-121` |
| Legend updates per mode | `network-manager.js:650` (`_updateOverlayLegend()`) |
| Clear/reset overlay | `network-manager.js:637` (`_clearOverlay()`) |