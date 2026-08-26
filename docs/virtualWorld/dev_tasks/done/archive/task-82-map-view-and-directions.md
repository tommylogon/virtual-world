---
wiki: "[[World Building/Graph System]]"
---
# Map View Fix + Multiple Direction Keys + Area Floor

**Priority**: Medium
**Status**: Not Started

## Bugs

- `_renderMapView()` throws `ReferenceError: floorOffsetY` — `const` used before declaration (TDZ). ✅ Fixed (moved before first use)
- Item library editor was missing `current_state` dropdown, action list was inconsistent with world inspector ✅ Fixed
- Library save payload was missing `current_state` ✅ Fixed

## Remaining Work

### 1. Multiple Direction Keywords
Allow both narrative directions (`"front_way"`, `"trail"`, `"hallway"`) and standard 8 cardinals + up/down.
- Engine should accept any string as a direction name
- Map view should use `cardinal` property on exits for positioning, falling back to the raw direction name if no cardinal set
- If cardinal is missing, treat as unknown and skip in map layout (or ask user to set one)
- cardinals are north, northeast, east, southeast, south, southwest, west, northwest, up, down, or N, NE, E, SE, S, SW, W, NW, U, D (case-insensitive)

### 2. Map View Cardinal Rendering
- `getCardinal()` helper already exists in `_renderMapView` (line 828-831) — reads `ex.cardinal` or falls back to `dir`
- But `dirOffsets` only has the 10 cardinal directions — any non-cardinal exit gets skipped silently
- Need to handle areas with only non-cardinal exits (show them as unconnected)

### 3. Area Floor in Editor (✅ Done)
- Number input for floor (-10 to 10) added to room inspector
- Updates via `api.updateNode(nodeId, { properties: { floor: value } })`
- Map view already uses `areas[rn].floor` for positioning

## Files

- `static/js/graph-manager.js` — `_renderMapView()` cardinal fallback, unconnected room placement, direction label display
- `static/js/inspector.js` — floor editor ✅ done
- `templates/index.html` — map view toggle buttons
- `static/css/style.css` — map view styling

**Deferred**: Post-merge feature branch. This branch is refactoring/testing only.


## Refactoring Impact (July 2026)

Map view exists as static/js/graph/map-view.js. Layout engine is static/js/graph/layout-engine.js. This task fixes open issues in map rendering, adds direction aliases, floor display — extend existing modules.
