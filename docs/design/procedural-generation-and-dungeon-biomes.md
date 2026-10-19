# Procedural Generation, Subterranean Biomes, and Spatial Topology Design

**Status:** Proposed  
**Author:** Juno  
**Date:** 2026-10-20  
**Scope:** `engine/scope_generators/`, `data/library/biomes/`, `data/worldpainter/`, `engine/world_grid.py`, `engine/world_compile.py`  
**Tracking Tasks:** task-884, task-580, task-496, task-398  

---

## 1. Executive Summary and Architectural Invariants

VirtualWorld is a simulation with an established spatial compilation pipeline:
- **WorldPainter grids are authoring substrates**, not the runtime world.
- **The generator paints; the compiler mints.** Procedural generators write standard sparse grid layers (`biome`, `road`, `floor`, `hazards`) into scope records (`engine/world_grid.py`). The existing compiler (`engine/world_compile.py`) turns those painted cells into real `area` nodes and `way` nodes with connection edges.
- **No private room-to-room bypass graphs.** A procedural generator must not mint its own un-compiled graph nodes. By emitting paint, all existing simulation mechanics (movement, lighting, hazards, foraging, line-of-sight, spectator mode, fog of war, and undo history) work automatically.
- **Deterministic output via GenerationPatch.** Every generation run takes `(scope, seed, budget, constraints)` and outputs a `GenerationPatch` (`engine/generation.py`) with reproducible provenance.

```
+-----------------------------------------------------------------------+
|                       Generation Specification                        |
|  Seed * Budget (Gold) * Landmarks (Anchor Cells) * District Weights   |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                      Pluggable Layout Generator                       |
|   1. Graph-First Spine Router  ->  2. District & Room Allocator       |
|   3. Markov / WFC Infill       ->  4. Catastrophe / Ruin Decay Pass   |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                    WorldPainter Painted Grid Layers                   |
|   layers["biome"], layers["road"], layers["floor"], layers["hazards"]  |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                      engine/world_compile.py                          |
|   Flood-fill regions -> Area nodes -> Way passages & Stairs -> Gates  |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                       Live Simulation Graph                           |
|       Navigable areas, doors, stairways, items, NPC schedules         |
+-----------------------------------------------------------------------+
```

---

## 2. Spatial Model: The 10-Neighbor Neighborhood vs Grid Reality

### 2.1 The Neighborhood Model
The proposed spatial model gives each cell up to 10 potential connections:
- **8 horizontal directions:** North, South, East, West, Northeast, Northwest, Southeast, Southwest.
- **2 vertical directions:** Up (+1 storey), Down (-1 storey).

### 2.2 The 2.5D Heightfield Reality Check
In `engine/world_grid.py`, layers are stored sparsely as dictionaries keyed by coordinate strings:
```python
record["layers"]["biome"]["<x>,<y>"] = "dwarven_great_forge"
record["layers"]["floor"]["<x>,<y>"] = 0
```
**Critical constraint:** A single scope grid in VirtualWorld is a 2.5D heightfield/storey map, **not** a dense 3D voxel array `(x, y, z)`. Coordinate `"5,5"` can hold exactly **one** biome and **one** floor value per scope. You cannot paint an Ancestral Tomb at `(5, 5, floor=-2)` directly underneath a Great Forge at `(5, 5, floor=0)` on the same scope grid.

### 2.3 Resolving 3D Dungeons in VirtualWorld
To represent multi-level subterranean ruins without breaking the 2D Konva canvas editor or rewriting `world_compile.py`:

1. **Architecture A: Hierarchical Scope-per-Depth (Recommended)**
   - The root ruin is a parent scope (e.g. `dwarven_ruins`).
   - Each subterranean level is a child scope (`ruins_level_0_gate`, `ruins_level_minus_1_mines`, `ruins_level_minus_2_tombs`).
   - Vertical connections between floors are compiled as **gateway ways** (`way_gateway_...`) or vertical shaft ways placed on dedicated stairwell/lift cells (task-583, task-775).
   - *Benefits:* Fits the existing lazy-loading, zone materialization, and outline tree systems cleanly. Solves memory issues for massive dungeons.

2. **Architecture B: Unfolded Planar Atlas (For Single Compact Scopes)**
   - Used when a building or ruin is contained in one small scope (like `engine/interior_gen.py` multi-floor plans).
   - Different storeys are painted in disjoint coordinate bands or horizontal slices, with stairwell cells (`cell_kind: passable`, `stair: true`) connecting them across floor levels.

### 2.4 Diagonal Traversal and Wall Clipping
- In `world_compile.py:143`, cardinal doors were originally standard, and diagonal doors on wall corners were skipped.
- Walking diagonally between `(0,0)` and `(1,1)` when `(1,0)` and `(0,1)` are solid stone walls clips through solid matter.
- In pure simulation graph topology, an area node is an unconstrained graph vertex that can connect to arbitrarily many ways. The limitation is purely geometric rasterization on the 2D grid.

### 2.5 WorldPainter Storey Adjuster Rail and Sibling Floor Scopes
The user proposed adding a vertical storey/floor adjuster to the side of the WorldPainter canvas, enabling seamless authoring of multi-level structures.

1. **UX Presentation (The Storey Rail):**
   - A vertical rail on the left/right canvas margin displaying active floor levels (e.g. `+2, +1, Ground (0), -1, -2, -3`).
   - Clicking a floor index smoothly steps the canvas viewport to that storey.
   - An "Add Floor Above / Add Floor Below" affordance creates the next subterranean depth with matching grid dimensions.
2. **Underlying Architecture (Sibling Child Scopes):**
   - Each floor level is stored as a sibling child scope (`kind: "floor"`, e.g. `dwarven_ruins_floor_0`, `dwarven_ruins_floor_minus_1`) under the parent structure scope (`dwarven_ruins`, `kind: "structure"`).
   - *Why this is the cleanest engineering choice:*
     - It leaves the sparse 2D layer storage format in `engine/world_grid.py` completely intact without risking a breaking rewrite.
     - Konva and vis.js only render one floor at a time, preventing memory exhaustion on huge dungeons.
     - Scopes already natively support `kind: "floor"` and hierarchical projection (`engine/world_scopes.py`).
3. **Ghost Layer / Onion-Skinning:**
   - When viewing `floor -1`, the editor renders a faint, non-interactive translucent overlay of `floor 0` (showing walls, stairwells, and lift shafts).
   - This allows authors and procedural tools to visually line up vertical connections.
4. **Vertical Gateway Auto-Compilation:**
   - Placing a stairwell or lift cell (`cell_kind: passable`, `stair: true`) at `(x, y)` on `floor 0` and at the matching `(x, y)` on `floor -1` causes the compiler to automatically mint a vertical gateway way (`way_gateway_...`) connecting the two levels.

### 2.6 Corner Doors and Chamfered Diagonal Portals
In graph space, any area node can have an arbitrary number of way edges. The restriction on diagonal doorways in `world_compile.py` was due to the opposite-pair scan looking only at cardinal offsets:
```python
for dx, dy in ((0, 1), (1, 0)):  # vertical pair, then horizontal
    before = (cell[0] - dx, cell[1] - dy)
    after = (cell[0] + dx, cell[1] + dy)
```
1. **Extending the Compiler for Corner Doors:**
   - The opposite-pair scan in `world_compile.py:1877` can be extended to support diagonal pairs:
     `((0, 1), (1, 0), (1, 1), (1, -1))`
   - *Safety Guard (The Chamfer Rule):* When checking a diagonal opposite pair `(1, 1)` (connecting `(x-1, y-1)` to `(x+1, y+1)` through `(x, y)`), the two flanking cells `(x-1, y)` and `(x, y-1)` must be solid wall cells (`cell_kind: solid`). This represents a classic 45-degree chamfered archway cut into the corner of a stone wall, rather than an accidental breach.
2. **Procedural Router Application:**
   - Wide subterranean halls and natural cavern junctions can emit diagonal open passages (`_SCAN_DIRECTIONS` already supports `southeast` and `southwest`).
   - Reinforced dwarven masonry chambers can place chamfered corner doors using `dwarven_archway` or `dwarven_runic_grille` on diagonal wall corners with verified flanking stone.

---

## 3. Four Procedural Generation Engines

Rather than forcing one algorithm to solve everything, four pluggable algorithms operate under a shared generator interface:

```python
class ScopeGenerator(Protocol):
    def generate(
        self,
        grid_bounds: tuple[int, int],
        landmarks: dict[str, tuple[int, int, int]],
        budget: int,
        config: GenerationConfig,
        seed: int,
    ) -> GenerationResult: ...
```

### 3.1 Method 1: Pure Random Frontier Growth (Baseline Control)
- **Mechanism:** Select a seed cell. Pick an adjacent empty neighbor from 10 directions. Roll room type from weighted frequency table. Leave 20% empty directions. Repeat until budget or cell limit is reached.
- **Strengths:** Trivial to implement, zero configuration, fast baseline.
- **Failure Mode:** Spatially incoherent, sprawling dead-ends, cannot reliably connect distant hand-placed landmarks, high probability of disconnected islands.

### 3.2 Method 2: Adjacency-Weighted Markov / WFC (Local Coherence)
- **Correction regarding Marching Cubes vs Markov Chains:**
  - *Marching Cubes* extracts 3D polygonal isosurfaces from volumetric scalar fields. It creates cave wall meshes, not room selection logic.
  - *Markov Chains* evaluate transition probability based on previous states (1D sequence or 2D neighbor field).
  - *Wave Function Collapse (WFC)* is constraint satisfaction via tile adjacency sockets.
- **Application in VirtualWorld (task-884):**
  - Uses `data/worldpainter/adjacency.json` and `engine/world_adjacencies.py`.
  - Defines bidirectional compatibility weights (0-100) between biomes.
  - Ideal for local cellular texturing, carving cave systems, and generating transition gradients (e.g. `chasm` -> `rubble_banks` -> `excavation_corridor`).

### 3.3 Method 3: Graph-First Spanning Tree (Landmark-Driven Macro-Topology)
- **Mechanism:**
  1. Place mandatory hand-placed landmarks on the grid.
  2. Construct a Relative Neighborhood Graph or Delaunay Triangulation between landmark nodes.
  3. Extract a Minimum Spanning Tree (MST) plus 15-25% extra loop edges to prevent monotonous linear backtracking.
  4. Rasterize the graph edges onto the grid using A* pathfinding with directional costs (carving corridors and vertical stairwells).
  5. Expand secondary functional rooms outward from the arterial corridor cells.
- **Strengths:** 100% guarantee that the Grand Gate, Great Forge, Ancestral Tomb, and Deep Mines are reachable and connected.

### 3.4 Method 4: The Hybrid Grammar & Catastrophe Pipeline (The Recommended Production Engine)
Combines all methods into an architectural pipeline:

```
[Phase 1: Macro-Spine]
Hand-placed landmarks -> Graph MST -> A* Corridor & Stair routing (reserves spine budget)

[Phase 2: District Zonation]
Assign district tags to spatial sectors (Industrial, Civic, Sepulchral, Excavation)

[Phase 3: Grammar & WFC Expansion]
Grow functional room clusters off spine based on district compatibility tables

[Phase 4: Cellular Dressing & Markov Buffering]
Smooth cave borders, insert doors, place perimeter walls, run task-884 feathering

[Phase 5: Catastrophe & Decay Pass]
Simulate ancient disaster: earthquake collapses, flooding, magma intrusion, monster nesting
```

---

## 4. Hand-Placed Landmarks, Budget System, and Catastrophe

### 4.1 Mandatory Landmarks
Landmarks act as hard constraints. Authors specify:
```json
{
  "landmarks": {
    "grand_gate": {"x": 2, "y": 15, "floor": 0, "biome": "dwarven_great_gate", "locked": true},
    "great_forge": {"x": 28, "y": 8, "floor": 0, "biome": "dwarven_great_forge", "locked": true},
    "royal_tomb": {"x": 25, "y": 25, "floor": -2, "scope": "child_crypt_level", "biome": "dwarven_ancestral_vault"},
    "deep_mine": {"x": 5, "y": 28, "floor": -3, "biome": "dwarven_deep_mine"}
  }
}
```

### 4.2 The Gold Generation Budget
Gold acts as an abstract construction point pool (e.g. 100,000 GP). Costs are structured across three dimensions:

1. **Room Footprint Cost:** Base room cost plus cost per cell.
   - Corridor: 50 GP / cell.
   - Common Storehouse: 500 GP + (cells * 40 GP).
   - Mechanists Guildhall: 4,000 GP + (cells * 150 GP).
   - Great Forge: 12,000 GP + (cells * 300 GP).
   - Royal Vault: 25,000 GP + (cells * 500 GP).
2. **Way & Structural Cost:**
   - Plain Carved Archway: 50 GP.
   - Reinforced Stone Portcullis: 300 GP.
   - Spiral Stone Stairwell (per vertical level): 800 GP.
   - Deep Chain Lift Shaft: 2,500 GP.
3. **Budget Partitioning:**
   - **Spine Reserve (30-40%):** Locked up-front to guarantee corridors and stairways connecting all mandatory landmarks can be completed.
   - **District Fill (50-60%):** Spent on elective rooms according to weighted probability tables.
   - **Contingency / Buffer (10%):** Unused budget converts to architectural grandeur (higher tier room descriptions, wider halls) or is discarded.

### 4.3 The Catastrophe and Decay Pass (The Discovery Layer)
A pristine 100k GP Dwarven city is a living stronghold, not a ruin. The catastrophe pass simulates the passage of ages and disasters:
- **Catastrophe Types:** Seismic Cave-In, Magma Breach, Subterranean Flood, Void Incursion, or Rot/Fungal Overgrowth.
- **Decay Operations:**
  1. *Collapse:* Replace 10-20% of corridor cells with `dwarven_collapsed_shaft` (rubble hazard, impassable or requiring climb/mining).
  2. *Chasm Breach:* Splice a `chasm` polygon across multiple storeys, breaking ways and creating sheer drop hazards (task-747).
  3. *Flooding:* Submerge lower storeys with `flooded_cavern` and `deep_water` biomes.
  4. *Monster Nesting:* Seed a monster nest generator (e.g. Troglodyte or Spider den) inside an abandoned district, overwriting room biomes with `den` tags.

---

## 5. Biome Taxonomy and Subterranean Vocabulary

Current taxonomy count: **110 biomes** in `data/worldpainter/biomes.json` and **307 library biomes** in `data/library/biomes/`.
Existing subterranean biomes are scarce (22 items, primarily generic `forge`, `crypt`, `great_hall`, `chasm`, `vault`, `ruin`).

The following 18 biomes are designed to complete the subterranean dwarven and ruin vocabulary:

### 5.1 Industrial and Engineering Biomes
| Biome ID | Name | Cell Kind | Surface | Tags | Description Excerpt |
|---|---|---|---|---|---|
| `dwarven_great_forge` | Great Forge | `place` | `stone` | `indoor, craft, fire, workshop, ancient` | Massive stone hearths banked with dormant anthracite, cold runic anvils. |
| `dwarven_smelting_works` | Smelting Works | `place` | `slag` | `indoor, craft, fire, industrial` | Troughs of vitrified slag, blast channels, and soot-blackened flues. |
| `dwarven_mechanists_guild` | Mechanists Guild | `place` | `stone` | `indoor, craft, machinery, technical` | Bronze gear trains, dismantled automaton joints, pneumatic line ports. |
| `dwarven_hydro_sluice` | Hydro Sluice | `place` | `stone` | `indoor, water, channel, engineering` | Channeled mountain runoff driving dormant turbines and drainage gates. |
| `dwarven_magma_forge` | Magma Forge | `place` | `obsidian`| `indoor, craft, fire, extreme_heat, hazard` | Open conduits of cooling basalt and anvils bolted to glowing lava seams. |

### 5.2 Civic, Religious, and Sepulchral Biomes
| Biome ID | Name | Cell Kind | Surface | Tags | Description Excerpt |
|---|---|---|---|---|---|
| `dwarven_great_gate` | Grand Gatehouse | `place` | `granite`| `indoor, defense, entrance, fortified` | Cyclopean stone slabs set in adamantine grooves, flanked by murder shafts. |
| `dwarven_colonnade` | Grand Colonnade | `place` | `marble` | `indoor, civic, circulation, monumental` | Hexagonal pillars rising fifty cubits to vaulted ribbed ceilings. |
| `dwarven_thane_throne` | Thane High Seat | `place` | `granite`| `indoor, civic, authority, leadership` | A tiered dais carved from living bedrock overlooking a sunken muster court. |
| `dwarven_ancestral_vault`| Ancestral Vault| `place` | `stone` | `indoor, sepulchral, quiet, warded` | Granite sarcophagi etched with genealogies and runic curses against theft. |
| `dwarven_brewhouse` | Vault Brewhouse | `place` | `stone` | `indoor, storage, eating, drink` | Copper fermentation tuns and stone casks of petrified fungal stout. |
| `dwarven_scriptorium` | Deep Archive | `place` | `stone` | `indoor, library, research, quiet` | Bronze shelving holding leaden scroll cylinders and stone tablets. |

### 5.3 Mining and Excavation Biomes
| Biome ID | Name | Cell Kind | Surface | Tags | Description Excerpt |
|---|---|---|---|---|---|
| `dwarven_deep_mine` | Deep Mine Shaft | `place` | `gravel` | `below_ground, mining, excavation, dark` | Shored timber adits following depleted iron seams down into the dark. |
| `dwarven_crystal_geode` | Luminescent Geode| `place` | `crystal`| `below_ground, mineral, light, natural` | A natural hollow spiked with towering prisms of pale glowing quartz. |
| `dwarven_collapsed_shaft`| Collapsed Shaft| `place` | `rubble` | `below_ground, rubble, hazard, blockage` | Shattered granite blocks and buckled iron stays choke the tunnel entirely. |

### 5.4 Structural, Vertical, and Boundary Biomes
| Biome ID | Name | Cell Kind | Surface | Tags | Description Excerpt |
|---|---|---|---|---|---|
| `dwarven_masonry_wall` | Dressed Masonry | `solid` | `stone` | `cell_kind:solid, structure, not_a_place` | Seamlessly dressed granite blocks bonded without mortar. |
| `dwarven_archway` | Carved Archway | `passable` | `stone` | `cell_kind:passable, structure, portal` | A heavy corbelled stone archway standing between chambers. |
| `dwarven_stair_well` | Spiral Stairwell | `passable` | `stone` | `cell_kind:passable, stair, vertical` | A corkscrew stair carved into the shaft wall descending to lower storeys. |
| `dwarven_lift_shaft` | Great Lift Shaft | `place` | `iron` | `indoor, vertical, lift, engineering` | Counterweighted iron hoist cages hanging over an abyss on braided cable. |
| `dwarven_runic_grille` | Runic Portcullis | `see_through`| `iron` | `cell_kind:see_through, structure, barrier`| Heavy wrought iron bars inscribed with warding script; vision passes freely. |

---

## 6. Audit of Existing Tasks

| Task ID | Status | Area | Title and Relationship to this Design |
|---|---|---|---|
| **task-884** | `todo` | `world` | **Child-scope procedural generators: Markov adjacency buffers, settlement/dungeon grammar, and reference-guided painting.** Direct foundation for scope generation, Markov adjacency matrices, and grammar rules. |
| **task-580** | `todo` | `ui` | **Unmade-scope Generate affordance and generation preview.** Provides the UI affordance on scope cards to trigger deterministic recipe generation with preview diffs. |
| **task-398** | `done` | `world` | **Deterministic structure generation with GenerationPatch.** Establishes the core generation contract (`apply_patch`, deterministic seeds, provenance tracking). |
| **task-567** | `done` | `world` | **Building interior generated from preset interior plan.** Implements ASCII interior templates, floor layer painting, and diverged cell protection (`engine/interior_gen.py`). |
| **task-496** | `review` | `world` | **Grid-to-graph compiler: cells to areas and ways.** The core compiler (`engine/world_compile.py`) that converts painted cells to runtime areas and ways. |
| **task-495** | `review` | `world` | **WorldPainter recursive scope grids and 3-mode editor.** Implements the scope grid data model (`engine/world_grid.py`) and sparse layer storage. |
| **task-497** | `done` | `world` | **WorldPainter biome/feature taxonomy and display meta.** Defines the JSON schema for biomes, cell kinds, surfaces, and tags (`engine/biomes.py`). |
| **task-562** | `done` | `world` | **Storey step ways and cell kind movement.** Adds `cell_kind` (`place`, `solid`, `passable`, `see_through`) and stairway way emission. |
| **task-564** | `done` | `world` | **Region merging rules.** Implements `merge:always` and `merge:never` tags to control when contiguous cells form one area. |
| **task-583** | `review` | `world` | **Global scope index, gateway ways, and load before you move.** Handles cross-scope gateways for multi-level child scopes. |
| **task-745** | `review` | `world` | **WorldPainter hazards: a current strength paint layer plus hazards.json.** Adds hazard layer support (cliff, fall, current). |
| **task-747** | `todo` | `world` | **WorldPainter compiler emits terrain hazards.** Converts painted hazard layers into engine hazard triggers during compilation. |
| **task-775** | `review` | `world` | **Sibling scope traversal: border seam remap and footprint placement.** Coordinates transitions across adjacent scopes. |
| **task-880** | `todo` | `ui` | **WorldPainter modularisation: split editor.ts into canvas, dialogs, and palette modules.** Crucial frontend refactor to host generator dialogs. |
| **task-882** | `review` | `world` | **Elevation and obstruction 2.5D raycast line-of-sight.** Line-of-sight calculation reading floor heights and solid cell obstacles. |
| **task-887** | `review` | `world` | **Way description and visible-in-direction generator.** Procedural narrative descriptions for ways based on connected biomes. |
| **task-99** | `todo` | `gameplay` | **Area Grids: Movement Costs, Size/Shape, and Pathfinding.** Legacy task proposing 2D grids inside individual areas. Replaced by WorldPainter scope grids. |

---

## 7. What Is Overlooked in the Initial Design Ideas

A critical engineering review highlights 10 specific design pitfalls:

1. **The 3D Coordinate Storage Trap:**
   Assuming `(x, y, z)` can be painted on a single scope grid. `layers["biome"]` is keyed by `"<x>,<y>"`. You cannot stack two rooms at the same coordinates in one scope. Vertical complexes must use **hierarchical child scopes per level** or unfolded spatial slices.
2. **Cell vs Area Cost Ambiguity:**
   In WorldPainter, multiple cells of the same biome merge into **one** area region (`world_compile.py:1058`). If a "Great Forge" costs 8,000 GP, is that 8,000 GP per cell or 8,000 GP for the whole merged 3x3 forge? The budget engine must distinguish **room feature cost** from **cell footprint cost**.
3. **Diagonal Wall-Clipping:**
   Connecting rooms diagonally across solid wall corners creates degenerate visual and movement seams where characters pass through the microscopic intersection of two solid masonry walls. Diagonal connections must be restricted to open caverns.
4. **Budget Exhaustion Deadlocks:**
   In pure random or unconstrained Markov generation, spending budget randomly can exhaust the gold pool before connecting to mandatory landmarks (e.g. reaching the mine shaft). The generator must use **reserve partitioning** to guarantee the connectivity spine before expanding elective rooms.
5. **Sparse Grid vs Memory Melting:**
   Generating dense grids above 150x150 in Python and sending them to vis.js or Konva will freeze browser rendering. Grids must remain sparse, and large complexes must be partitioned across child scopes.
6. **The Island Link Trap:**
   If a random generator produces disconnected rooms, `world_compile.py:2312` automatically activates an `island_links` fallback, creating artificial long-distance bridges across empty voids. The generator must guarantee its own topological connectivity.
7. **Bypassing the Biome Taxonomy Schema:**
   Hardcoding room costs and compatibility rules in generator Python code violates repo architecture. Compatibility scores must live in `data/worldpainter/adjacency.json` and room costs in library metadata.
8. **Doorway Placement Invariants:**
   Doors in `world_compile.py` are minted when a `cell_kind: passable` cell sits between two `place` cells. If the generator forgets to place walls (`solid`) and leaves rooms directly touching, the compiler merges them into a single massive room (if same biome) or mints open borders without doors.
9. **Stair Step Directionality:**
   In `world_compile.py:110`, stairways record the **lower** of the two storeys and calculate `floor_step`. A generator that places vertical transitions must place passable stair cells on the boundary where floor levels change.
10. **Regeneration and Edit Preservation:**
    Per `engine/generation.py:BASE_KEY` and `interior_gen.py:diverged_cells`, manual edits made by authors in WorldPainter must survive regeneration. Any generator must track `generated_cells` baseline hashes.

---

## 8. Implementation Roadmap

### Phase 1: Subterranean Taxonomy & Adjacency Data (Unblocked)
1. Author the 18 subterranean biomes as individual JSON files in `data/library/biomes/`.
2. Create `data/worldpainter/adjacency.json` with transition weights and compatibility scores (task-884 requirement).
3. Author room footprint archetypes (prefabs) for standard dwarven facilities.

### Phase 2: Core Dungeon Scope Generator (`engine/scope_generators/`)
1. Implement `engine/scope_generators/dungeon_gen.py`:
   - Macro-Spine Minimum Spanning Tree connecting landmarks.
   - Budget allocator tracking footprint cost, passage cost, and reserve margins.
   - A* corridor and stair routing with obstacle avoidance.
   - WFC/Markov secondary chamber expansion.
   - Catastrophe decay filter (collapse, chasm cut, flooding).
2. Wire generator output to standard `(layer, x, y, value)` tuples matching `interior_gen.py`.

### Phase 3: UI Affordance & Generation Preview (task-580 / task-880)
1. Expose generator parameters in the WorldPainter child-scope toolbar:
   - Template selection (Dwarven Hold, Monster Nest, Catacomb, Mine).
   - Budget slider (GP), Seed, Catastrophe severity.
2. Render proposed paint diffs in a staging overlay before committing.

### Phase 4: Multi-Level Child Scope Stitching
1. Automate creation of child scopes for lower subterranean depths.
2. Place stairwell and lift features linking parent and child scopes via standard `way_gateway_...` nodes.
