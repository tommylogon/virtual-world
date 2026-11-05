---
type: task
status: todo
area: world
priority: high
wiki: "[[Grid to Graph]]"
---

# task-816: A scope can hold painted cells outside its own grid, so those cells sit off the map and cannot be touched

**Filed:** 2026-10-12
**Related:** 

## What

Verified on data/scenarios/kraktooth_goblin_camp.json: world_scopes.world.grid is {w:20,h:7} (which matches the kraktooth world map image aspect, 4760x1666 = 20/7), but the world scope's own area cells reach y=8. Eleven areas are placed outside the grid: area_world_11_7..19_7 (y=7), area_world_16_8, area_world_17_8 (y=8), area_abandoned_farm (16,7) and area_murk_lake (7,7). In the graph the world-scope grid is drawn 20x7, so those cells render beyond the grid boundary and are not touchable. Decide and implement one: (a) grow a scope grid to contain every cell it holds, (b) prevent WorldPainter from placing a cell outside the grid, or (c) both. The immediate scenario fix is a data edit to the world scope's grid; the general guard is the durable fix.

## Why

TODO

## How

TODO

## Steps to verify

1. Load the kraktooth goblin camp scenario, select the world scope, open the Map layout.
   - expected: the world scope grid boundary is drawn (bottom edge at row 6, a 20x7 grid)
   - observed: TODO
2. Look below the bottom grid edge (rows y=7 and y=8) and try to click/select the cells that sit outside the dashed boundary.
   - expected (fixed): either every world-scope cell sits inside the grid, OR the out-of-grid cells can be selected and edited
   - observed: TODO
3. Open the WorldPainter / map editor on the world scope and hover a cell at y=7 or y=8.
   - expected: the cell is inside the paintable grid, not past its edge
   - observed: TODO
4. Cross-check the numbers this card cites.
   - expected: world grid is {w:20,h:7}; the 11 listed areas (area_world_11_7..19_7, area_world_16_8, area_world_17_8, area_abandoned_farm, area_murk_lake) sit at y=7 or y=8
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: WorldPainter → select the `world` scope → inspect its grid boundary and painted cells, especially the eleven recorded areas at y=7/y=8 and the off-grid farm/lake cells.

Current availability: the card measured a 20×7 world grid containing cells through y=8 and lists eleven out-of-bounds areas. The fix choice—grow the grid, reject placement, or another documented policy—is still open; no behavior is claimed as corrected.

Live steps when available:
1. Load `data/scenarios/kraktooth_goblin_camp.json`, open WorldPainter, and select the `world` scope. Scroll/zoom until all grid rows and boundary cells are visible.
   - expected: every area held by the scope is visible and selectable; no painted cell lies beyond the displayed grid boundary.
2. Inspect `area_world_11_7` through `area_world_19_7`, `area_world_16_8`, `area_world_17_8`, `area_abandoned_farm`, and `area_murk_lake` in the scope map.
   - expected: each recorded cell is either inside the corrected grid or is rejected/relocated according to the explicit resolution chosen for this task.
3. Attempt to paint a cell just beyond each grid edge and save/reload the scenario.
   - expected: the UI prevents out-of-grid placement or expands the grid before the cell is accepted; no inaccessible off-map area is silently saved.
4. Open each affected area in the graph and Inspector after reload.
   - expected: map placement, scope membership, and graph cell coordinates agree.

This section is not a claim that the off-grid cells have been repaired today.
