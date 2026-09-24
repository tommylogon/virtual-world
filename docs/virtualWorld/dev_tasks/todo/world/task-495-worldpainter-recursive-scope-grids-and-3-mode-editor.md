---
type: task
status: todo
area: world
priority: medium
---

# task-495: WorldPainter: recursive scope grids and 3-mode editor

**Filed:** 2026-09-24
**Related:** task-397, task-398, task-400

## Goal

Authoring layer: every world scope owns a bounded grid at its own resolution, with three modes - world (zones as cells, no interiors), town (paint settlement grid: walls, gates, roads, markets, buildings), interior (building/floor grid: rooms, doors, windows, tags). Zones ARE world_scopes (engine/world_scopes.py); select a zone to set its scale and open its drawn grid. Paint layers: biome/feature/road/elevation. Features are child scopes placed at a cell (e.g. a village inside a forest) that can be moved/added/deleted. Data model: per-scope grid_w/grid_h, cell_scale, layers, child placements; stable frames so references survive moves; a rule for move-overlap. UI renders each scope's grid.

## Acceptance

- A scope can be selected; its grid (`grid_w`/`grid_h`, `cell_scale`, layers) opens in the matching mode (world/town/interior).
- A feature (child scope) can be placed at a cell, moved, added and deleted; the parent's placements update.
- Grids are recursive: a parent cell can hold a child scope whose own grid opens in the next mode.
- Moving a feature over occupied cells follows a documented rule (forbid / displace / merge) and preserves ids/references.
- The scope manifest + child placements serialize and round-trip, covered by tests.
