---
type: task
status: todo
area: world
priority: medium
wiki: "[[World Building/WorldPainter]]"
---

# task-882: 2.5D elevation and obstruction raycast line-of-sight for world and settlement grids

**Filed:** 2026-10-19
**Related:** task-677, task-499, task-498, task-877

## What

Implement a 2.5D geometric line-of-sight (LoS) raycasting system for world and settlement grids (`scope.mode in ['world', 'town']`, excluding fine interiors) that accurately models sightlines across elevation and obscuring terrain.

Vision must **not** traverse the movement graph (which bypasses mountains along roads). Instead, it casts straight Bresenham rays across the coordinate lattice $(x, y, z)$ where:
- $(x, y)$ are cell coordinates.
- $z$ is the elevation / floor value (with 1 floor = 3m / 1 storey, single source of truth `METRES_PER_STOREY = 3`).
- Biome/structure properties declare:
  - `height`: height in floors/storeys (e.g. sparse woods = 1-2 floors, watchtower = 5 floors, mountains = 20 floors).
  - `obscurity`: floating-point value between $0.0$ and $1.0$ (e.g. open grassland = $0.0$, sparse woods = $0.4$, dense woods = $1.0$, masonry wall = $1.0$).
- Obscurity accumulates along the ray at line height: passing through two sparse forests ($0.4 + 0.4 = 0.8$) leaves $0.2$ visibility; a third drops it to $0.0$ (blocked).
- When a ray elevation is strictly higher than tile $(z + \text{height})$, sight passes freely over the obstruction without accumulating obscurity.
- Beyond 60 cells (~5 km horizon at 1 cell = 80m / 1 min walk), effective elevation drops by $-1$ per cell to model horizon curvature without spherical math.

## Minimap Integration (Tied to task-677)

The visible cells calculated by the raycast feed directly into the character's minimap / fog-of-war reveal:
1. **Three Fog/Visibility Tiers:**
   - **Currently visible cells** (bright / active LoS): calculated each tick from the character's current cell and elevation.
   - **Visited cells** ("you have been here"): permanently revealed terrain from `player.visited_areas`.
   - **Unseen cells**: masked by fog of war.
2. **Long-Range Silhouette Resolution (LoD by Distance):**
   - **Far range (20-60 cells):** Sights high-elevation landmarks (mountains, towers, settlement silhouettes).
   - **Medium range (6-20 cells):** Sights biome terrain types and large structures/settlements on the minimap.
   - **Close range (1-5 cells):** Sights characters and interactable entities.
3. **Scope Background Art Reveal:**
   - Unveils the scope's background reference/rendered image as fog is cleared by the raycast.

## Agent Spatial Awareness Without Context Flooding

To prevent 3,600 grid cells or hundreds of visited coordinate strings from blowing up the LLM's context window:
1. **Passive Immediate Horizon (`room-context.ts`):**
   - Injects a compact, 2-3 line section listing only prominent high-elevation landmarks or major terrain boundaries in active LoS (e.g. *"On the horizon: Kraktooth Spire (18 cells SE, high ground), Great River (6 cells S)"*).
   - Cost: ~30 tokens per turn. Never lists raw coordinates or empty wilderness cells.
2. **Active Spatial Query (Free-Tier `recall` Action):**
   - Reuses the existing `FREE` tier action `recall` (`engine/action_tiers.py:125`, task-736).
   - An agent queries its own mental map on demand without spending a turn: `recall path to <place>` or `recall landmarks`.
   - Returns a compact natural-language summary from visited areas and belief-based travel memory (task-467): *"You recall the route to Eldenford: south along the wagon trail (about 12 minutes walk)."*

## Performance & Caching Model

- **Stationary Turns Cost Zero:** If the actor does not move or change elevation, the computed `visibleCells` set is cached and reused.
- **Early Termination:** In dense wilderness or settlement grids, rays terminate within 4-12 cells upon hitting $\ge 1.0$ obscurity or terrain steps, so average ray cost is small (~8 steps).
- **Radial Sweeps (Perimeter / Octant Shadowcasting):** Instead of testing 3,600 individual target cells, raycasting fires outward in 360 radial steps or uses 8-octant recursive shadowcasting (skipping shaded sectors), keeping total step operations well under $0.5\text{ms}$ per movement.

## Technical Invariants & Edge Cases

1. **Supercover Rasterization (No Diagonal Wall Leaks):**
   - Rays must use conservative supercover cell traversal so diagonal wall joints `(10, 10)` and `(11, 11)` do not leak sightlines between corners.
2. **Observer Eye-Level Offset:**
   - Ray origin is $z_{\text{start}} = z_{\text{origin}} + \text{EyeHeight}$ (default $+0.5$ floors / 1.5m), preventing an observer standing on grass from being blinded by their own tile's 1-storey hedge or low wall.
3. **Front-Face Visibility:**
   - An obstacle that blocks sight (e.g. `obscurity: 1.0` or accumulating $\ge 1.0$) must register the **blocking tile itself as visible** (rendering the front face of the cliff or wall), but terminate propagation into the shadow behind it.
4. **Ambient Light and Weather Clamping:**
   - Ray length is capped by the current environment: daylight = up to 60 cells; dusk/moonlight = 15 cells; pitch-black night (`engine/lighting.py`) = 1 cell; dense fog/blizzard (`engine/weather.py`) = 2 cells.
5. **Continuous 3D Ray Interpolation:**
   - Ray elevation is tested continuously per step: $z_{\text{ray}}(d) = z_{\text{origin}} + (z_{\text{target}} - z_{\text{origin}}) \times (d / D)$, correctly distinguishing steep downward glances (thin canopy transit) from horizontal chord walks (thick canopy transit).
6. **Performance & Execution Budget:**
   - 360-degree all-cell raycasting is strictly reserved for the **active viewer** (human turn / inspect). Headless soak runs and simple NPCs perform targeted checks on demand or use coarse radial sector sweeps.
7. **Scope Containment:**
   - Raycasting stays strictly within the active grid scope. On a `world` grid, settlements are single feature tiles; inside a `settlement` scope, raycasts are bounded by the settlement perimeter.
8. **Directional Facing Arc (Cone vs Peripheral Awareness):**
   - Reuses `player.facing` (`room-context.ts:530`).
   - Primary vision cone ($120^\circ$ arc forward): Full Level-of-Detail (characters, items, terrain).
   - Peripheral / rear awareness ($240^\circ$ remainder): Limited range (2-3 cells for movement sounds; high-elevation horizon landmarks only). Enables stealth and rear ambush mechanics without artificial omniscience.
9. **Dynamic Tile and Area Overrides:**
   - If an Area node sits on a cell `(x, y)` (`properties.cell`), any authored `properties.height` or `properties.obscurity` overrides or stacks with the underlying biome tile.
10. **Delta Caching and Movement Events:**
   - Stationary turns cost 0ms (cached `visible_cells` set reused).
   - When moving, the engine evaluates `visible_new - visible_old` to fire arrival perception events ("You spot a goblin patrol 5 cells south!") without re-evaluating the entire world.

## Acceptance

- [ ] Biome vocabulary (`data/worldpainter/biomes.json`) supports `height` (floors) and `obscurity` (0.0 to 1.0) with sensible defaults.
- [ ] 2.5D Raycast function `cast_sight_ray(origin, target, grid_data)` implemented in `engine/world_grid.py` (with TypeScript counterpart in `static/js/worldpainter/grid-model.ts`).
- [ ] Supercover line stepping prevents diagonal wall leakage.
- [ ] Observer eye-level offset (+0.5 floors) prevents self-tile occlusion.
- [ ] Blocking obstacle tiles remain visible on their front face while casting rear shadows.
- [ ] Obscurity accumulation and elevation clearance correctly pass over lower obstacles and block through thick terrain.
- [ ] Directional facing cone ($120^\circ$ primary LoD, $240^\circ$ peripheral) respects `player.facing`.
- [ ] 60-cell horizon curvature drop simulated.
- [ ] Environmental clamping applies weather and ambient light caps to maximum sight distance.
- [ ] Visible cells output connects to character minimap state (`GET /api/players/<name>/map` in `task-677`).
- [ ] WorldPainter Character Vision Lens toggle and interactive raycast occlusion debugger tool available in editor.
- [ ] Unit tests verify ray elevation clearance, obscurity accumulation, supercover wall blocking, facing arcs, and horizon drop.

## Files

- `data/worldpainter/biomes.json`
- `engine/world_grid.py`
- `static/js/worldpainter/grid-model.ts`
- `tools/unit/test_worldpainter.js`
- `tests/test_world_grid.py`
