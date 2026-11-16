"""Tests for area grids, intra-area micro-positioning, movement costs, and A* pathfinding (task-99)."""

import pytest
from graph import Node, Edge, EDGE_IN
from area import Area
from engine import pathfinding
from engine.serialization import WorldSerializer


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _sample_grid():
    return {
        "width": 5,
        "height": 5,
        "tiles": [
            ["floor", "floor", "wall", "floor", "floor"],
            ["floor", "floor", "wall", "floor", "floor"],
            ["floor", "floor", "floor", "floor", "floor"],
            ["water", "water", "wall", "rubble", "floor"],
            ["floor", "floor", "wall", "floor", "floor"],
        ],
        "costs": {
            "floor": 1,
            "wall": 99,
            "water": 2,
            "rubble": 3,
            "carpet": 1,
            "stairs": 1,
        },
        "characters": {
            "player_traveler": {"x": 0, "y": 0},
        },
        "items": {
            "item_key": {"x": 4, "y": 0},
        },
        "exits": {
            "north": {"x": 2, "y": 0},
        },
    }


def test_pathfinding_astar_navigates_around_walls():
    grid = _sample_grid()
    # From (1, 0) to (3, 0) - directly blocked by wall at (2, 0) and (2, 1)
    # Must navigate down through (2, 2)
    path = pathfinding.find_path(grid, (1, 0), (3, 0))
    assert path is not None
    assert path[0] == (1, 0)
    assert path[-1] == (3, 0)
    # Wall coordinates must not be in path
    assert (2, 0) not in path
    assert (2, 1) not in path
    # Must pass through row 2 (where wall has a gap)
    assert any(p[1] == 2 for p in path)


def test_pathfinding_respects_tile_costs():
    grid = {
        "width": 3,
        "height": 3,
        "tiles": [
            ["floor", "rubble", "floor"],
            ["floor", "rubble", "floor"],
            ["floor", "floor", "floor"],
        ],
        "costs": {
            "floor": 1,
            "rubble": 5,
            "wall": 99,
        },
    }
    # Direct route through rubble: (0, 0) -> (1, 0) -> (2, 0) costs 5 + 1 = 6
    # Route around rubble: (0,0) -> (0,1) -> (0,2) -> (1,2) -> (2,2) -> (2,1) -> (2,0) costs 1*6 = 6
    # Now make rubble cost 10:
    grid["costs"]["rubble"] = 10
    path = pathfinding.find_path(grid, (0, 0), (2, 0))
    assert path is not None
    # Path should avoid rubble entirely
    for x, y in path:
        assert grid["tiles"][y][x] != "rubble"


def test_pathfinding_blocked_returns_none():
    grid = {
        "width": 3,
        "height": 3,
        "tiles": [
            ["floor", "wall", "floor"],
            ["wall", "wall", "wall"],
            ["floor", "wall", "floor"],
        ],
    }
    path = pathfinding.find_path(grid, (0, 0), (2, 2))
    assert path is None


def test_movement_move_to_coord_and_energy_cost():
    w = _world()
    hero = w.get_active_player_obj()
    hero.vitals["Energy"] = 100

    # Create area with grid
    area = Area("Courtyard", "A paved courtyard.", items=[], grid=_sample_grid())
    w.add_area(area)
    w.set_current_area("Courtyard")

    # Move hero to (0, 2)
    res = w.movement.move_to_coord(hero.name, 0, 2)
    assert res["ok"]
    assert res["x"] == 0 and res["y"] == 2
    # Moving (0, 0) -> (0, 1) [floor=1] -> (0, 2) [floor=1]: total cost = 2
    assert res["cost"] == 2
    assert hero.vitals["Energy"] == 98
    assert hero.position == {"x": 0, "y": 2}

    # Verify grid has updated character position
    grid = w.movement.get_area_grid("Courtyard")
    assert grid["characters"][hero.name] == {"x": 0, "y": 2}


def test_movement_impassable_tile_refusal():
    w = _world()
    hero = w.get_active_player_obj()
    area = Area("Hall", "A hall.", items=[], grid=_sample_grid())
    w.add_area(area)
    w.set_current_area("Hall")

    # (2, 0) is a wall
    with pytest.raises(ValueError, match="impassable"):
        w.movement.move_to_coord(hero.name, 2, 0)


def test_movement_move_to_item():
    w = _world()
    hero = w.get_active_player_obj()
    hero.vitals["Energy"] = 100

    grid = _sample_grid()
    # Key is at (4, 0)
    area = Area("Armory", "An armory.", items=[], grid=grid)
    w.add_area(area)
    w.set_current_area("Armory")

    res = w.movement.move_to_item(hero.name, "item_key")
    assert res["ok"]
    assert res["x"] == 4 and res["y"] == 0
    assert hero.position == {"x": 4, "y": 0}
    assert hero.vitals["Energy"] < 100


def test_npc_intra_area_movement():
    w = _world()
    from player import Player
    npc = Player(name="Guard Bob")
    npc.vitals["Energy"] = 100
    w.players["Guard Bob"] = npc

    area = Area("Barracks", "Guard barracks.", items=[], grid=_sample_grid())
    w.add_area(area)
    npc.current_area = "Barracks"

    log_msg = w.npc_behaviors.execute_go_action("Guard Bob", {"mode": "move_to", "x": 1, "y": 2})
    assert "[Guard Bob]" in log_msg
    assert npc.position == {"x": 1, "y": 2}
    assert npc.vitals["Energy"] < 100


def test_area_grid_serialization_roundtrip():
    w = _world()
    grid = _sample_grid()
    area = Area("Garden", "A peaceful garden.", items=[], grid=grid)
    w.add_area(area)

    data = w.to_scenario_dict()

    # Load into new world instance
    w2 = _world()
    w2.load_from_dict(data)

    restored_grid = w2.movement.get_area_grid("Garden")
    assert restored_grid is not None
    assert restored_grid["width"] == 5
    assert restored_grid["height"] == 5
    assert restored_grid["tiles"][0][2] == "wall"
    assert restored_grid["costs"]["rubble"] == 3
    assert restored_grid["items"]["item_key"] == {"x": 4, "y": 0}
