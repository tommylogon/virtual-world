---
type: doc
tags: [system/worldbuilding, system/grid, system/elevation, scope/kraktooth]
---

# Kraktooth Regional Scope & Mountain Elevation

## What you can do

The Kraktooth region models a macro-scale fantasy valley centered around a 560-meter alpine peak (**`floor: 187`**). Rather than treating mountains as abstract backdrop art, VirtualWorld represents the entire vertical landmass on the world grid's single `floor` layer (`METRES_PER_STOREY = 3`).

Characters can scale the mountain via trails or climbing gear, enter the fortified goblin camp hollowed into the mountain terrace at `floor: 60` (180m), explore the 160-meter-wide subterranean cave network (`scope: kraktooth_underground`) excavated into solid bedrock, descend into deep iron mines, or climb up to the summit spire (`floor: 187`) to survey the entire 30-kilometer valley basin in 2.5D line of sight.

## Where it lives

- `engine/world_grid.py` - [`METRES_PER_STOREY = 3`](file:///f:/AI/viwo/virtual-world/engine/world_grid.py), `floor` layer storage, and [`calculate_2_5d_los`](file:///f:/AI/viwo/virtual-world/engine/world_grid.py).
- `engine/world_compile.py` - cliff detection, storey step thresholds (`CLIFF_FLOOR_DELTA`), rockface promotion, and automatic climb/drop refusal rules.
- `static/js/worldpainter/editor.ts` - `floor` layer painting, storey input (`+1 / -1`), and greyscale heightmap import/export (Task-877).
- `static/js/worldpainter/grid-model.ts` - client-side viewshed raycaster and palette definitions.
- `docs/virtualWorld/Gameplay/Grid Line of Sight & Charted Memory.md` - deep documentation on 2.5D raycasting, visibility tiers, and horizon context.

**Connected Tasks:** [[dev_tasks/review/world/task-882-elevation-and-obstruction-2-5d-raycast-line-of-sight-on-world-and-settlement-grids|task-882]] · [[dev_tasks/done/world/task-877-worldpainter-heightmap-import-and-export|task-877]] · [[dev_tasks/review/world/task-677-grid-to-graph-elevation-and-multi-level-ways|task-677]]

---

## The 560-Meter Kraktooth Mountain Anatomy

### Structural & Geological Layout

A cavern complex 160 meters wide (holding 20 chambers, an underground lake, and deep mine shafts) cannot exist in a shallow 60m hill without catastrophic collapse. Anchoring the mountain peak at 560m provides 380 meters of solid granite and limestone overburden above the cave ceilings:

```
Altitude (m)       Storey (floor)     Geographic & Structural Feature
--------------------------------------------------------------------------------------
560 m              floor: 187         KRAKTOOTH PEAK & RED SIGIL (Alpine Summit Spire)
                                        |
                                        | ~380m of solid granite cliff & lookout chimneys
                                        |
180 m              floor: 60          HILLSIDE CAVE ENTRANCE (Fortified Exterior Terrace)
                                        |  (Stone staircase descends into bedrock)
160 m              floor: 53          Room 1: Chief's Gathering Pit & Upper Caverns
140 m              floor: 47          Room 16: Underground Lake (Cathedral Stalactites)
110 m              floor: 37          Room 17: Mine Access & Deep Tunnels (Iron Veins)
                                        |
                                        | ~110m of rock cushion above regional water table
                                        |
 45 m              floor: 15          Eldenford Walled Town & Farmlands
  0 m              floor: 0           Murk Lake & Raven River (Valley Floor Basin)
```

---

## How "187 Floors" Are Built: What We Have vs What Is Missing

A common authoring misconception is that 187 floors require creating and managing 187 separate 2D canvas planes. In VirtualWorld, this is not how outdoor terrain functions.

### What We Have Today

1. **Single-Layer 2D Topographic Heightfield:**
   - Outdoor terrain lives on one 2D coordinate grid `(x, y)` containing five parallel layers: `biome`, `road`, `floor`, `climate`, and `current`.
   - The `floor` layer stores an **unbounded integer storey index per cell**. A cell at the mountain peak is simply `floor: 187`, while a cell at the riverbank is `floor: 0`.
2. **Greyscale Heightmap Import/Export (Task-877):**
   - WorldPainter includes built-in heightmap import. Authors can paint a standard 8-bit or 16-bit greyscale heightmap in Photoshop, GIMP, World Machine, or Blender (where black = 0m and pure white = 560m).
   - Clicking "Import heightmap..." in WorldPainter reads the image and converts pixel brightness into 0..187 integer storeys across the entire grid instantly.
3. **Automatic Cliff Detection & Way Compilation (`engine/world_compile.py`):**
   - The world compiler compares storey deltas between neighboring cells (`step = abs(floor_here - floor_nb)`).
   - Steps greater than the cliff threshold automatically promote borders to impassable rockfaces, preventing characters from simply walking off a 100-meter drop.
   - Cells connected by road or trail override the refusal and compile switchback ways.
4. **2.5D Angular Slope-Sweep LoS (Task-882):**
   - The raycaster scales smoothly across any vertical elevation. Calculating visibility from `floor: 187` down to `floor: 0` takes less than 1 millisecond per ray.

### What We Do Not Have Yet (Authoring Quality of Life)

To author huge mountain massifs without importing an external greyscale PNG, two features would bridge the gap:

1. **Radial Cone / Slope Brush in WorldPainter:**
   - Currently, manual editing requires typing numbers (`187`, `150`, `120`) and painting flat terraces.
   - A cone or gradient brush tool would allow clicking the peak at 187, clicking the base at 0, and automatically interpolating a natural bell-curve mountain slope.
2. **Topographic Hypsometric Tinting (Contour Shading):**
   - When viewing the `floor` layer in WorldPainter, cells currently render as raw numbers or greyscale tiles.
   - Adding colored hypsometric tints (e.g. green valley 0-20 -> brown foothills 20-80 -> slate cliffs 80-150 -> snowcap white 150-187) would make steep vertical terrain immediately readable on the editor canvas.

---

## The Child Scope Architecture

The regional landscape connects directly to nested child scopes via boundary seams:

| Scope ID | Type | Bounds | Elevation Range | Key Landmarks |
|---|---|---|---|---|
| `kraktooth_region` | Macro World Grid | 6 km x 3 km | `floor: 0` to `187` | Raven River, Murk Lake, Kraktooth Spire, Northern Hills. |
| `scope: deep_forest` | Wilderness Sub-Scope | 2 km x 1.5 km | `floor: 5` to `25` | The Great Oak (35m tall), Stonefall Waterfall, Bear Den. |
| `scope: eldenford` | Settlement Grid | 400 m x 400 m | `floor: 0` to `15` | Walled town (32 parcels), Raven Bridge, Watermill. |
| `scope: kraktooth_underground` | Interior Dungeon Grid | 160 m x 60 m | `floor: 37` to `60` | 20 cave chambers, Gathering Pit, Underground Lake, Mine Shafts. |

### Transitions
- **Entering the Mountain:** Walking to the cave entrance cell on `kraktooth_region` (`floor: 60`) triggers the inward seam into `scope: kraktooth_underground` Room 1 (`floor: 53`).
- **Descending to Mines:** Traversing Room 17 ("Mine Access") steps down into deeper subterranean mining scopes beneath the mountain core.
