---
area: gameplay
wiki: "[[World Building/Rooms & Areas]]"
type: task
status: todo
priority: low
---

# Task 99: Area Grids - Movement Costs, Size/Shape, and Pathfinding

**Status**: todo
**Priority**: Medium
**Filed**: 2026-07-24
**Architectural Note (2026-10-20):** This early proposal assumed areas would internally own 2D grids (`room.grid`). WorldPainter inverted this hierarchy: world scopes own the 2D grid (`engine/world_grid.py`), and the compiler (`engine/world_compile.py`) compiles those cells *into* area and way nodes (`properties.cell = "<scope>:<x>,<y>"`). Intra-area micro-positioning and within-room movement costs remain an open question, but the spatial grid substrate now lives at the scope level. See `docs/design/procedural-generation-and-dungeon-biomes.md` and `task-884`.

## What

Currently areas are dimensionless nodes - you're either *in* a room or you're not. This task adds a 2D grid to areas, allowing movement costs, item positioning, and NPC pathfinding within areas.

## What Already Exists

- Rooms have `exits` with `blocked` state
- Movement is handled by `engine/movement.py` (directional, door-checking)
- Player manager tracks which room each character is in
- Some areas have environment properties (light, temp, etc.)

## What's Missing

### 1. Area Grid Data Model

Add a grid field to areas:
```python
room.grid = {
    "width": 10,
    "height": 10,
    "tiles": [
        ["floor", "floor", "wall", "floor", "floor", ...],
        ...
    ],
    "costs": {
        "floor": 1,
        "wall": 99,  # impassable
        "rubble": 3,
        "water": 2,
        "carpet": 1,
        "stairs": 0  # exit point
    },
    "items": {
        "item_rusty_key": {"x": 3, "y": 5},
        "item_candle": {"x": 1, "y": 1}
    },
    "characters": {
        "player_traveler": {"x": 0, "y": 0}
    },
    "exits": {
        "north": {"x": 5, "y": 0},
        "south": {"x": 5, "y": 9}
    }
}
```

### 2. Movement Within Rooms

- `move_to [x] [y]` - move to specific grid coordinate within current room
- `move_to [item]` - move adjacent to specified item
- Movement cost depends on tile type (walking on rubble costs 3 AP)
- Items/characters have positions within the grid

### 3. Pathfinding (A*)

- NPCs can pathfind across room grids to reach exits, items, or other characters
- `engine/pathfinding.py` - A* implementation using tile costs
- Consider diagonal movement (optional, user-configurable)

### 4. Area Size/Shape

- Area dimensions defined in `room.grid.width` and `room.grid.height`
- Shape defined by tile types (walls define boundaries)
- Exits positioned at specific grid edges
- Procedural room generation from templates

### 5. UI Considerations

- Area grid view in inspector (toggleable)
- Character/item positions visible on grid, draggable
- Movement cost feedback (e.g. "Moving there costs 3 energy")

## Implementation Order

1. **Phase 1**: Area grid data model + basic `move_to` command (engine + room.py)
2. **Phase 2**: A* pathfinding (new engine module)
3. **Phase 3**: Grid visualization in inspector (frontend)
4. **Phase 4**: NPC pathfinding + procedural generation

## Files

- `room.py` - add intra-area grid field with tile data, item/character positions, exit coords
- `engine/movement.py` - add `move_to` coordinate/item handlers and movement cost calculation
- `engine/pathfinding.py` - new A* module for intra-area pathfinding
- `engine/npc_behaviors.py` - use pathfinding for NPC movement within area
- `virtual_world_engine.py` - wire new movement costs
- `static/js/inspector/room-view.js` - grid visualization
- `static/js/graph/` - optional grid overlay on areas
- `data/library/` / `world_template.json` / scenario areas - intra-area grid data (authored)
- `engine/world_grid.py`, `engine/world_compile.py` - scope grid substrate (read-only reference; do not duplicate world-scale grid)

## Steps to verify

1. A* pathfinding on various grid layouts
   - expected: A* returns shortest path by tile costs on open, obstacle, and maze layouts.
   - observed: Not run live; reconnaissance confirms scope grid exists but intra-area A* not implemented.

2. Movement cost calculation
   - expected: moving across tiles with different costs (floor/rubble/water/stairs) sums costs correctly and blocks impassable tiles (wall/blocked).
   - observed: Not run live; movement.py does not currently read intra-area tile costs.

3. NPC pathfinding integration
   - expected: NPCs pathfind within area to exits/items/characters using same grid/cost rules; area-level graph location unchanged until exiting through a way.
   - observed: Not run live; engine/npc_behaviors.py not wired to intra-area pathfinding.

4. Serialization
   - expected: intra-area grid + item/character positions survive save/load.
   - observed: Not run live; intra-area grid not persisted/loaded today.

## Plan position (2026-10-20): the approach changed, the card survived

**The approach changed, and the newer work is what changed it.** This card was
filed 2026-07-24 assuming areas would internally own 2D grids (`room.grid`).
WorldPainter inverted that hierarchy: **world scopes own the 2D grid**
(`engine/world_grid.py`), and the compiler (`engine/world_compile.py`) compiles
those cells *into* area and way nodes.

| | Original plan (2026-07-24) | After WorldPainter / task-884 (2026-10-20) |
|---|---|---|
| Who owns the grid | each area, as `room.grid` | the world scope, in `engine/world_grid.py` |
| How a position is expressed | an area-local grid index | `properties.cell` = `<scope>:<x>,<y>` on the area/way node |
| What this card owns | the whole grid model | the **intra-area** layer only: micro-positioning, per-tile costs, A* |

The card must therefore **not** re-introduce a competing grid. It adds a
*second, finer* layer underneath the scope grid, for movement inside one area -
which the scope grid cannot express, because a scope cell is a place, not a
position within a place.

**Measured 2026-10-20, to confirm the surviving scope is real:**

- `engine/world_grid.py` exists, and `engine/world_compile.py` writes cell
  coordinates onto compiled nodes (`:1048`, `:2022`, `:2162`, `:2787`).
- A `room.grid`-style attribute does **not** exist: searching `engine/` for
  `room.grid` or a bare `.grid` returns **0** hits. The duplication risk the
  architectural note warns about is real and still live.
- A* is **not** implemented: the only `heapq` use in `engine/` is
  `engine/sound.py:174,216` (sound propagation), not pathfinding.
- `engine/npc_behaviors.py` is not wired to any intra-area pathfinder.

**Verdict: the approach is narrowed, not replaced.** The card remains a
distinct piece of the plan - the intra-area layer is unclaimed by anything
newer - but it is now a *sub-layer* of the scope grid rather than a
replacement for it. Its `## How` already reflects this ("Treat scope grid as
source of truth for cell identity"), and its `## Files` already flags
`engine/world_grid.py` as a read-only reference: *"do not duplicate world-scale
grid"*. No rewrite is needed; the narrowing is already written down.

## Why

The scope-level grid now owns cell structure (engine/world_grid.py and engine/world_compile.py compile cells into area/way nodes with properties.cell), so duplicating world-scale grid into rooms is not required. What remains open is intra-area micro-positioning, per-tile movement costs, item/character cell positions inside an area, and NPC pathfinding within that area. Without that, area interiors remain dimensionless and movement costs cannot vary by terrain (rubble/water/stairs), and NPCs cannot plan short-range routes to exits/items/characters inside the same area. This task adds the minimal intra-area grid model and pathfinding so within-area behavior is modeled consistently with the existing movement system.

## How

Grounded in reconnaissance: reuse existing systems (engine/movement.py directional/door checks, Player manager location) and add an intra-area grid on areas plus A*.

1. **Phase 1 - Data model + move_to**: extend area representation (room.py / area schema) to support an intra-area grid with width/height, tile types, tile costs, item/character positions, and exit cell coordinates. Add `move_to [x] [y]` and `move_to [item]` handling in engine/movement.py that reads tile costs and updates character cell position within the same area (respecting blocked/impassable tiles). Treat scope grid as source of truth for cell identity (properties.cell = "<scope>:<x>,<y>") where applicable.
2. **Phase 2 - Pathfinding**: create engine/pathfinding.py implementing A* on the intra-area grid using per-tile costs; support 4-neighborhood by default with optional diagonal toggle if authored.
3. **Phase 3 - Grid visualization**: add static/js/inspector/room-view.js grid view (toggleable) showing tile types, costs, character/item positions, and exit markers.
4. **Phase 4 - NPC integration + procedural generation**: wire engine/npc_behaviors.py to use grid pathfinding for intra-area destinations; allow library/world templates to author intra-area grid data and ensure serialization persists it. Keep graph-level area identity unchanged.

## Acceptance

- [ ] Intra-area grid data model exists on areas with width/height, tiles, costs, item/character positions, and exit coords.
- [ ] `move_to [x] [y]` and `move_to [item]` work within current area with per-tile movement costs and impassable tile blocking.
- [ ] engine/pathfinding.py provides A* over intra-area grid used by engine/npc_behaviors.py for intra-area navigation.
- [ ] Serialization persists intra-area grid and positions; reload restores them.

## Browser UI and intended live verification

Intended UI home: select an area → open its local grid/map view → move a character between cells and inspect item placement and NPC path movement within that area.

Current availability: areas are currently dimensionless graph nodes according to this card. The 2D room grid, within-area movement costs, positioned items, and NPC pathfinding are planned; this section does not claim a grid UI exists today.

Live steps when available:
1. Open a scratch area's grid, place a character and an item in distinct cells, then move the character toward the item.
   - expected: the character changes cell along a valid path and its movement cost reflects the crossed cells; the item remains at its authored position.
2. Place an obstacle between the character and target, then request movement again.
   - expected: pathfinding routes around the obstacle when a route exists and refuses movement when the grid truly blocks all routes.
3. Give an NPC a destination in the same area and let its normal movement run.
   - expected: the NPC follows the same grid path/cost rules as the controlled character; area-level graph location remains the same until it exits through a way.
4. Reload the scenario and inspect the grid and item positions.
   - expected: authored cell placement persists; runtime movement state follows its documented save behavior.

This section is not a claim that planned UI exists or works today.
