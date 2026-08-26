---
group: Graph
---
# Hide Areas With No Characters

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: In Review — implemented 2026-08-20

## Implementation

Added a "🏘 Inhabited" toggle button to the graph editor toolbar. When active, areas with no characters present are hidden. Clicking a way (door) reveals its connected areas, allowing navigation through uninhabited spaces. Clicking empty space clears the revealed areas.

Backend: no changes needed — this is purely a frontend filter using existing graph data.

Frontend (`static/js/`):
- `graph-manager.js`: added `_showOnlyInhabitedAreas` flag (default false) and `_revealedAreaIds` set.
- `graph/network-manager.js`: added `toggleInhabitedAreas()`, `revealAreasForWay()`, and `hideRevealedAreas()`. Modified `loadGraphData()` to filter out uninhabited areas when the toggle is on, computing linked non-area nodes the same way the floor filter does.
- `graph/event-handlers.js`: way clicks call `revealAreasForWay()`; empty clicks call `hideRevealedAreas()`.
- `templates/index.html`: added the 🏘 Inhabited button (starts `active` — on by default).

## Verification

- JS syntax check passed

---

## Idea

Graph editor toggle to hide areas with no characters present. On click, ways reveal the connected areas again.

## Notes

- Editor optimization to reduce visual noise in large worlds (only inhabited areas stay visible by default).
- Toggle button in the graph/map editor; clicking a way re-reveals its adjacent areas.
- Complements `task-302` (siblings stay open) and `task-312` (graph search filter).

## Related

- `developer ideas.md` line 10
- Map editor code (`static/js/` graph/map editor modules)
