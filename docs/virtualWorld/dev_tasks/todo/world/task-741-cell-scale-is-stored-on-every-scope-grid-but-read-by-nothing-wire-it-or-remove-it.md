---
type: task
status: todo
area: world
priority: medium
---

# task-741: cell_scale is stored on every scope grid but read by nothing: wire it or remove it

**Filed:** 2026-10-08
**Related:** task-495 task-496

## Goal

The WorldPainter grid dialog's scale field writes grid.cell_scale, and it is read by zero engine call sites: engine/world_compile.py:147 states travel time stays one turn per cell and cell_scale is not read by the compiler or movement. Decide the intent: either wire it into movement as turns-per-cell (a real travel-cost change) or delete it from the dialog, the grid record and the round-trip. A field that persists and does nothing is worse than no field.

## Acceptance

- TODO
