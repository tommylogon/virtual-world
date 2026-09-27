---
type: bug
status: done
area: graph
priority: high
---

# bug-52: Map grid pitch does not move painted areas, so a pitch change splits the map and its areas onto two grids

**Filed:** 2026-09-27
**Related:** task-523, task-524, bug-51
**Fixed:** 2026-09-27

## Symptom

The author raised **Map grid** from 40 to 260. The background image grew to the
new pitch; the areas stayed where they were, so the map and its areas ended up on
two different grids — exactly what `graph-background.js` warns about in its
`_mapUnitsPerCell` comment.

## Cause

`_applyGridLayout` filtered out every node with `central_gravity_enabled: false`:

```js
const frozen = (id) => (((nodesObj[id] || {}).properties) || {}).central_gravity_enabled === false);
```

That flag is **not** the author's doing: `tools/build_scenario.py:81`,
`tools/assemble_scenario.py:135` and `tools/generate_scenario.py:254` all
`setdefault("central_gravity_enabled", False)` on every area they emit. All 21
areas of the goblin camp carried it, so the lattice placed *none* of them and they
kept whatever pitch they were last saved at (40px), while
`_mapUnitsPerCell()` — which reads the current pitch — re-fitted the art to 260.

Measured on the goblin camp before the fix: pitch 260, art `5200 × 1743`
(= 20 × 260, letterboxed), areas still at 40px/cell.

## Fix

- A node carrying `properties.cell` is **always** placed at its cell. The flag is
  about physics, and the lattice is not physics: for a painted node the cell *is*
  the position, and the art is drawn to those cells. The exemption still stands
  for a node with no cell, so a hand-positioned way/item is untouched.
- `hasPaintedCoords(properties)` is the new predicate, and **`cell` is the
  discriminator, not the numbers** — a node dragged in the graph also has numeric
  `x`/`y` (canvas units), and treating it as painted would scale it a second time.
  The first version of the fix checked the numbers and the regression test caught
  exactly that.
- Latent twin closed: `persistPositionsToWorld` wrote canvas positions into
  `properties.x/y`, which for a painted node hold *engine* units (`cell * 40`)
  that the Map layout multiplies by the pitch again. A "save layout to world" in
  Map mode would therefore have drifted the map further on every save. Painted
  nodes are now skipped there, and the log says how many were left on their cells.
  (Checked the saved world: no drift had happened yet — all 21 areas were exactly
  `cell * 40`.)

## Tests

- `test_graph_layout_engine.js`: a painted area and a placed way are placed at
  `cell * pitch` with physics off, while a frozen area *without* a cell is left
  alone; plus the `hasPaintedCoords` discrimination cases.
- `tools/unit/run.cjs`: the `vm` sandbox had no `setTimeout`, which
  `_applyGridLayout` needs for its redraw — added synchronous stubs (and
  `clearTimeout`/`setInterval`/`clearInterval`) rather than making every test
  care.

## Verified

Live against the author's server, goblin camp loaded, Map layout, pitch 260:
`nodePitch {x: 260, y: 260}` and `artWidth 5200` — the areas and the art on one
grid, matching each other.

## Also answered here

**The map pitch is global, not per scope.** One `config.graphMapSpacing` for the
whole world, read by both `GraphLayoutEngine.mapSpacing()` (the lattice) and
`_mapUnitsPerCell()` (the art). It is also **Map-layout only** — in Graph layout
the areas sit on their saved positions and the toolbar says so, so raising the
pitch there does nothing by design.
