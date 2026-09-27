---
type: task
status: review
area: ui
priority: high
---

# task-540: WorldPainter cell inspector: hover or click a cell to read what is on it

**Filed:** 2026-09-27
**Related:** task-495, task-528, task-541
**Status:** implemented 2026-09-27, in review

## Goal

After placing an area or painting a cell there was no way to see what a cell
holds. Add an inspector: hovering a cell shows a tooltip (painted
biome/road/elevation, the placed area or child-scope feature on it, its cell
coords) and clicking selects the cell and opens a small panel with the same
content plus actions (unplace the area, remove the feature, clear the paint).
Reads from buildRows/areaMap/featureMap, so the data is already in the payload.

## Acceptance

- [x] `gridModel.cellInfo(payload, x, y)` — a pure function of the payload, so it
      is unit-tested without a canvas. Returns `{x, y, key, biome, road,
      elevation, area, child, painted, empty}`. The `feature` layer is
      `{cellKey: child_scope_id}`, so the readable name is resolved from the
      scope's own `placements` card; a child id with no card still names
      something rather than printing `undefined`.
- [x] **Hover** — the grid HUD carries a `wp-cellinfo` readout, updated from the
      pointer. Konva fires `mousemove` per pixel, so the DOM is only touched when
      the cell *or its content* changed (a `state.cellInfoKey` guard). An empty
      cell says "nothing here" rather than printing three blank fields.
- [x] **A 🔍 Inspect tool** in the tool rail, and a **right-click inspects on any
      tool** — "what is this?" should never need a tool switch, and the
      right-click handler previously only swallowed the event.
- [x] **The panel** (`wp-cellpanel`, under the grid) lists biome / road /
      elevation / area / sub-zone and offers only what applies to that cell:
      move or unplace the area, open the area in the graph inspector, open or
      remove the sub-zone, clear the paint (one `paint_batch` request, so one
      undo step).
- [x] Escape and switching scope clear the panel; it cannot outlive its scope.
- [x] Unit-tested: `cellInfo` for a cell with all three paint layers + an area +
      a sub-zone, a bare cell, and an orphaned feature id.
- [x] Verified live in the browser: hovering (11,7) of the goblin camp reads
      `(11,7) 📍 Animal Pens`; right-click opens the panel with the area row and
      the `📍 Move Animal Pens` / `🗑 Unplace` / `🔎 Open area` actions; an empty
      cell reads `(18,2) — nothing here`.

## Notes

- The panel deliberately does *not* offer "assign to a scope": that is membership
  and lives on the node's inspector (task-539), so there is one place to read and
  change it.
- The "Open area" action closes the painter first (`VW.inspector.showNode`), since
  the painter is a modal overlay over the graph.
