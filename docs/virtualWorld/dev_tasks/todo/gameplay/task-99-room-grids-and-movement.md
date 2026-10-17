---
area: gameplay
wiki: "[[World Building/Rooms & Areas]]"
type: task
status: todo
priority: low
---

# Task 99: Area Grids — Movement Costs, Size/Shape, and Pathfinding

**Status**: todo
**Priority**: Medium
**Filed**: 2026-07-24

## What

Currently areas are dimensionless nodes — you're either *in* a room or you're not. This task adds a 2D grid to areas, allowing movement costs, item positioning, and NPC pathfinding within areas.

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

- `move_to [x] [y]` — move to specific grid coordinate within current room
- `move_to [item]` — move adjacent to specified item
- Movement cost depends on tile type (walking on rubble costs 3 AP)
- Items/characters have positions within the grid

### 3. Pathfinding (A*)

- NPCs can pathfind across room grids to reach exits, items, or other characters
- `engine/pathfinding.py` — A* implementation using tile costs
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

- `room.py` — add grid field with tile data, item/character positions, exit coords
- `engine/movement.py` — `move_to` coordinate handler, add movement cost calculation
- `engine/pathfinding.py` — new A* module
- `engine/npc_behaviors.py` — use pathfinding for NPC movement
- `virtual_world_engine.py` — wire new movement costs
- `static/js/inspector/room-view.js` — grid visualization
- `static/js/graph/` — optional grid overlay on areas
- `world_template.json` / library areas — grid data

## Steps to verify

- A* pathfinding on various grid layouts (open, obstacles, mazes)
- Movement cost calculation
- NPC pathfinding integration
- Serialization (grid + positions survive save/load)

## Why

TODO

## How

TODO

## Acceptance

- [ ] TODO

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
