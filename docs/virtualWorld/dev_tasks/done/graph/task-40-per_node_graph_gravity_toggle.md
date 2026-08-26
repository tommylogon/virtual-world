---
group: Graph & Area UX
wiki: "[[World Building/Graph System]]"
---

# Per-Node Graph Gravity Toggle

**Filed**: 2026-07-18
**Priority**: Medium
**Status**: Implemented / Needs Review

---

## Summary

The graph now has a saved, per-node **Central pull enabled** toggle. It is available from the inspector for areas, items, ways, and character nodes.

When disabled, the node is excluded from vis-network physics, so it remains in place while the rest of the graph continues to simulate.

## Review Checklist

- Confirm the toggle is shown for room, item, door, and character nodes.
- Disable central pull for one node and confirm it no longer moves while the rest of the graph settles.
- Re-enable it and confirm the node re-enters the simulation.
- Reload the page/world and confirm the choice persists via `central_gravity_enabled`.
- Confirm graph reloads do not discard other node positions.

## Technical Note

vis-network exposes central gravity as a graph-wide setting. The implemented per-node behavior uses `physics: false`, so opting out also disables spring and other force movement for that node; it functions as a position lock.

## Files Changed

- `static/js/graph-manager.js` — maps `central_gravity_enabled` to the vis-network node physics option and refresh signature.
- `static/js/inspector.js` — adds the inspector control and persistence handler.