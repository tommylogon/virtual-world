---
type: task
status: review
area: world
priority: high
---

# task-650: Eldenford town map is ~10 percent painted and 12 of its cells are sparse_forest inside the walls

**Filed:** 2026-09-30
**Related:** 

## Goal

Tommy asked for the Eldenford town map to be finished. Measured from GET /api/world/scopes/eldenford_interior/grid on kraktooth_goblin_camp: mode is 'town' and the road layer is well developed (49 cells: 43 road, 2 gate at 13,2 and 17,15, 4 bridge at 17,17 / 7,16 / 8,15 / 8,16), but the biome layer holds only 18 cells and 12 of them are 'sparse_forest' at 9,3 9,5 10,3 11,3 15,4 15,5 16,4 16,5 17,4 17,5 17,6 18,5 -- scrubland inside a walled town. The only built cells are temple (11,8), market (12,9) and cemetery (7,4): 3 of the 30 locations named on the reference art. The floor and climate layers have no cells at all, placements and area_placements are both 0, and names is empty. The roads describe a town; the biome layer does not.

## Acceptance

- [x] All 12 `sparse_forest` cells inside the walls are repainted (the east
      cluster becomes the Orchard & Gardens the art draws; the north-west cluster
      becomes gardens against the cemetery wall). **`sparse_forest` count is 0.**
- [x] The named locations on the reference art are painted and named as real
      data: the biome layer grows from 18 to **42 cells** and `names` from 0 to
      **29** (26 painted/named places + Temple, Cemetery, Town Green named on
      their existing cells).
- [x] Live proof: `GET /api/world/scopes/eldenford_interior/grid` on the loaded
      `kraktooth_goblin_camp` returns `sparse_forest = 0`, 42 biome cells, 29
      names; the painter renders the town and each cell's inspector reads its
      name and exits.
- [x] The graph is deliberately left alone — the scope is `baked`, the ticket
      measures the grid payload, and re-generating would rewrite the authored
      world; the paint is the authoring source it names.

## Notes

Cells added (biome, name): Watch House (14,6); Town Hall (14,8); Shrine (17,8);
Clothier & Tailor (15,10); Leatherworker (17,11); Smithy (20,12); Carpenter
(17,13); Wheelwright (18,14); Baker (13,13); Butcher (11,12); Brewer (19,11);
Apothecary (18,10); Stable (10,14); The Stag Inn (7,9); The Crooked Mug (8,7);
The Silver Lily (9,9); Bathhouse (15,15); Warehouse (6,11); River Landing/Ferry
(6,12); Mill (6,16); Fisher Huts (3,13); Orchard & Gardens (17,5); Farmlands
(21,2); Poor Quarter (21,8); Wealthy Merchant Homes (20,7). A new `bathhouse`
biome was added to `data/worldpainter/biomes.json` (data-only; the legend has a
Bathhouse and no existing building matched).
