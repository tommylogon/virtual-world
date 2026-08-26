---
type: task
status: done
area: ui
priority: medium
created: 2026-07-27
---

# Task 111: Remove Map View

**Status**: done — verified 2026-08-03. `static/js/graph/map-view.js` no longer exists; zero references to `GraphMapView`, `_renderMapView`, or `map-view` in static/, templates/, css/, or tools/test_ui.cjs. The 🗺️ toolbar button (index.html:107) still exists but toggles the cardinal layout (task-112), not the removed map view.

## Summary

The map view (SVG-based cardinal direction room layout) is broken, unused, and architecturally nonsensical. Remove it entirely — button, module, CSS, dead code in graph-manager, and test references.

## Files to Remove

- `static/js/graph/map-view.js` — entire module (214 lines)

## Files to Edit

### `templates/index.html`
- Remove line 113 — the Map toolbar button
- Remove line 564 — `<script src="/static/js/graph/map-view.js">`

### `static/js/graph-manager.js`
- Remove `'map'` case from `setViewMode()` (line 558) — just keep the `'outline'` branch
- Remove `'map'` case from `_renderCurrentView()` (line 567)
- Remove the dead `_renderMapView()` method entirely (lines 571+)

### `static/css/style.css`
- Remove all map-view CSS (the `/* ===== Map View ===== */` block, lines 960-975)

### `tools/test_ui.cjs`
- Remove the map view setViewMode test (lines 332-335)

### `docs/virtualWorld/dev_tasks/todo/task-82-map-view-and-directions.md`
- Move to `done/archive/` (its core work is moot with map view removed)

## Verification

- Server starts without errors
- Graph/Outline buttons still work in the toolbar
- No 404s for the removed JS file
- No CSS references to map-view classes
- No JS references to `GraphMapView` or `_renderMapView`
