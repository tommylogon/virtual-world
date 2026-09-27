---
type: bug
status: done
area: graph
priority: high
---

# bug-51: Background art is not re-fitted to a scope's grid, so painted areas sit off the map

**Filed:** 2026-09-27
**Related:** task-523, task-524, task-528
**Fixed:** 2026-09-27

## Symptom

Hand-placed areas were put on painted cells in the WorldPainter (goblin camp,
21 of them) and showed up in the graph in a tight cluster beside the background
art instead of on top of it.

## Cause — the areas were right all along

Measured on the goblin camp (`deep_woods_2`, grid 20×10, map pitch 40px):

| thing | value |
|---|---|
| `area_animal_pens` cell (11,7) | canvas (440, 280) |
| `area_camp_entrance` cell (8,1) | canvas (320, 40) |
| `area_chiefs_den` cell (5,2) | canvas (200, 80) |
| camp's art rect | **(−150, 344) 6000 × 2011** |

Every placed area was exactly on the painted lattice, and the grid origin is
already cell-centred (`paintedGridRect` starts half a cell before cell 0, and the
painter draws every marker at `cell*CELL + CELL/2`), so there was no half-cell
drift either. The **art** was the wrong thing: a 6000×2011 rect is 150×50 cells —
a leftover from an older, much larger grid, stored in **pixels**.

A layer rect is saved in px, so it goes stale whenever the grid changes shape,
the map pitch changes, or a world whose maps were fitted to a different grid is
opened. `_applyReferenceLayout` — the derived answer: the reference's own cell
rect, or a fit to the whole grid — was only ever reached from
`fitToPaintedGrid`, which is called from a pitch change and from a manual
"fit to painted grid" menu action. **Nothing re-derived the art on load**, so the
drift was permanent until someone happened to press the button.

## Fix

- `_reconcileReferenceArt()` re-applies `_applyReferenceLayout` for the layer
  that *is* the loaded scope's reference, on every world refetch
  (`_onWorldRefetched`) and on every scope switch (new `refreshForScope()`).
- The scope switch needed its own hook: `setScopeFilter` loads a **subgraph** and
  never emits `state:updated`, so the reconcile was silently skipped there — the
  first version of this fix did nothing until that was found.
- Cost control: a signature of `scopeId | pitch | offset` short-circuits the
  request, so the frequent `state:updated` (after every paint stroke) costs
  nothing. Only the *loaded* scope is touched — in the whole-world view there is
  no single grid to fit to.
- Hand placement is unaffected: a zone drag (task-523) moves the grid itself and
  the scope offset is added on top of the derived rect, and a reference carrying
  its own cell rect still wins over the whole-grid fit.

## Verified

The camp's art became `x −20, y 46, 800 × 268` — the 20×10 grid's `800 × 400`
rect with the image letterboxed inside it exactly as the painter does (the
picture's aspect is 2.98, so it is 800 × 268 centred vertically). 20 of the 21
placed areas fall inside the image band; the rest sit in the empty rows above and
below it, which is also what the painter shows.

**Note for the author:** the browser caches `static/js`, so this fix needs a hard
refresh (Ctrl+F5) — a normal reload kept serving the old file.
