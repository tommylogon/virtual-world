---
group: UI & Settings
wiki: "[[World Building/Graph System]]"
---

# World Outline Tab + Camera Focus on Click

**Priority**: Medium

## Summary

Remove the 🔍 Analyze toolbar button (replaced by the world outline) and move the outline from the graph-container view into a tab in the left panel, alongside Agents and Initiative Order. Clicking an agent in the agent list, or an area / item / way / player in the outline, moves the graph camera to that node (and opens the inspector).

## Requirements

- Remove the `🔍 Analyze` toolbar button (was `graphEditor.analyze()` → `GraphTreeView.showAnalysis()`)
- Remove the `📋 Outline` graph view-toggle (`setViewMode('outline')`) — the outline now lives in the left panel
- Left panel gets a tab bar: 🧍 Agents | ⚔️ Initiative | 🗺️ Outline (Agents active by default)
- Outline tab renders the world tree into `#outline-container`:
  - Rooms sorted with env badge, collapsible children (exits, items, players)
  - Exits now clickable when `way_id` is present (opens way inspector + focuses way node)
- Camera focus: clicking an agent in the agent list, or an area / item / way / player in the outline, focuses the graph node (`network.selectNodes` + `network.focus` with animation) and switches back to graph view if an overlay was active
- Initiative tab shows a hint when turn-based mode is off (previously the whole section hid)

## Audit

**Status**: In Review — implemented 2026-08-09, verified with Playwright smoke test (14/14 checks)
**How to test**:
- Analyze button and Outline view-toggle are gone from the graph toolbar
- Left panel shows Agents / Initiative / Outline tabs; switching works
- Outline tab lists all rooms; clicking a room / item / way / player opens the inspector AND pans/zooms the graph to that node (overlay views are exited first)
- Clicking an agent in the Agents list pans the camera to that character's graph node
- Initiative tab with turn-based mode off shows the "Turn-based mode is off" hint

## Files Changed

- `templates/index.html` — removed Analyze + Outline buttons; added left-panel tab bar and `#outline-container`
- `static/css/style.css` — `.left-tabs` / `.left-tab` / `.left-tab-pane` / `.left-outline` + initiative item styles
- `static/js/main.js` — removed `graphEditor.analyze()`
- `static/js/graph-manager.js` — added `focusNode()` / `showNodeAndFocus()`; `_selectRoom()` now focuses; dropped dead `showAnalysis()` / `_copyTree()` / `_renderOutlineView()` / `_copyOutlineTree()` and the outline branches of `setViewMode()` / `_renderCurrentView()`
- `static/js/graph/tree-view.js` — added `renderOutlinePanel()` (replaces content, clickable exits); removed dead `showAnalysis()` / `copyTree()` / `renderOutlineView()`
- `static/js/ui-controller.js` — added `switchLeftTab()` / `showAgentAndFocus()`; `selectAgent()` focuses camera; `renderAll()` refreshes outline when its tab is active; initiative hint when turn-based off
- `docs/virtualWorld/World Building/Graph System.md` — updated tree-view.js description
