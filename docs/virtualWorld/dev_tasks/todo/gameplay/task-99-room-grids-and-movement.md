---
group: Graph & Area UX
wiki: "[[World Building/Rooms & Areas]]"
---
# Task 99: Area Grids — Movement Costs, Size/Shape, and Pathfinding

**Status**: todo
**Priority**: Medium
**Filed**: 2026-07-24

## Summary

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

## Files Affected

- `room.py` — add grid field with tile data, item/character positions, exit coords
- `engine/movement.py` — `move_to` coordinate handler, add movement cost calculation
- `engine/pathfinding.py` — new A* module
- `engine/npc_behaviors.py` — use pathfinding for NPC movement
- `virtual_world_engine.py` — wire new movement costs
- `static/js/inspector/room-view.js` — grid visualization
- `static/js/graph/` — optional grid overlay on areas
- `world_template.json` / library areas — grid data

## Tests
- A* pathfinding on various grid layouts (open, obstacles, mazes)
- Movement cost calculation
- NPC pathfinding integration
- Serialization (grid + positions survive save/load)