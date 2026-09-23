"""Skill-checked foraging in the soak tier (task-469).

Finding something in the field is a Perception check, so a clumsy character can
go hungry where a perceptive one eats; carried food never needs a check.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node, Edge, EDGE_IN, EDGE_CARRYING
from player import Player
from engine.background_simulation import (
    BackgroundSimulation, TASK_MINUTES, MEAL_RESTORE,
)


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _area(w):
    return w.get_active_player_obj().current_area


def _fresh_area(w, name="Test Larder"):
    """An area with nothing in it, so only the fixture under test can be found."""
    from area import Area
    w.movement.add_area(Area(name, "Empty.", []))
    return name


def _forager(w, area, hunger=80):
    p = Player("Forager")
    w.add_player(p)
    p.current_area = area
    w.set_player_area("Forager", area)
    p.simulation_mode = "background"
    p.state = "idle"
    p.activity = None
    p.vitals.update({"Hunger": hunger, "Thirst": 0, "Energy": 100, "Bladder": 0})
    return p


def _food(w, area, name="dried meat", carried_by=None, in_container=None):
    node = Node(id=f"item_{name.replace(' ', '_')}", type="item", name=name,
                properties={"name": name, "tags": ["food"], "actions": [],
                            "weight": 1, "count": 1})
    w.graph.add_node(node)
    if carried_by is not None:
        pid = w._player_node_id(carried_by.name)
        w.graph.add_edge(Edge(source=node.id, target=pid, type=EDGE_CARRYING))
    elif in_container is not None:
        w.graph.add_edge(Edge(source=node.id, target=in_container.id, type=EDGE_IN))
    else:
        w.graph.add_edge(Edge(source=node.id, target=w.area_node_id(area),
                              type=EDGE_IN))
    return node


def _basket(w, area, name="basket"):
    node = Node(id=f"item_{name}", type="item", name=name,
                properties={"name": name, "tags": [], "actions": [], "weight": 1})
    w.graph.add_node(node)
    w.graph.add_edge(Edge(source=node.id, target=w.area_node_id(area), type=EDGE_IN))
    return node


def _log_text(w):
    logger = w.game_logger
    return "\n".join(getattr(logger, "game_log", []) or [])


def test_a_failed_forage_leaves_the_character_hungry():
    w = _world()
    area = _fresh_area(w)
    p = _forager(w, area)
    node = _food(w, area, in_container=_basket(w, area))
    w.skill_check = lambda *a, **k: (False, 0, "")
    used = BackgroundSimulation(w).take_action(p, served=set(), remaining=1.0)
    assert used == TASK_MINUTES["forage"]
    assert p.vitals["Hunger"] == 80, "ate despite a failed check"
    assert w.graph.get_node(node.id) is not None, "food vanished on a miss"
    assert "finds nothing" in _log_text(w)
    assert p.activity and p.activity.get("type") == "foraging"


def test_a_successful_forage_eats():
    w = _world()
    area = _fresh_area(w)
    p = _forager(w, area)
    node = _food(w, area, in_container=_basket(w, area))
    w.skill_check = lambda *a, **k: (True, 20, "")
    used = BackgroundSimulation(w).take_action(p, served=set(), remaining=10.0)
    assert used == TASK_MINUTES["eat"]
    assert p.vitals["Hunger"] == 80 - MEAL_RESTORE
    assert w.graph.get_node(node.id) is None, "food was not consumed"


def test_open_food_needs_no_check():
    """A visible stew in the camp is maintenance, not a Perception puzzle."""
    w = _world()
    area = _fresh_area(w)
    p = _forager(w, area)
    node = _food(w, area)
    w.skill_check = lambda *a, **k: (False, 0, "")
    used = BackgroundSimulation(w).take_action(p, served=set(), remaining=10.0)
    assert used == TASK_MINUTES["eat"]
    assert p.vitals["Hunger"] == 80 - MEAL_RESTORE
    assert w.graph.get_node(node.id) is None


def test_carried_food_needs_no_check():
    w = _world()
    p = _forager(w, _area(w))
    node = _food(w, _area(w), carried_by=p)
    w.skill_check = lambda *a, **k: (False, 0, "")
    used = BackgroundSimulation(w).take_action(p, served=set(), remaining=10.0)
    assert used == TASK_MINUTES["eat"]
    assert p.vitals["Hunger"] == 80 - MEAL_RESTORE
    assert w.graph.get_node(node.id) is None


def test_no_food_present_is_not_a_failed_search():
    from area import Area
    w = _world()
    w.movement.add_area(Area("Empty Field", "Nothing here.", []))
    p = _forager(w, "Empty Field")
    w.skill_check = lambda *a, **k: (False, 0, "")
    BackgroundSimulation(w).take_action(p, served=set(), remaining=1.0)
    assert "finds nothing" not in _log_text(w), \
        "there was nothing to find, so no search should have happened"
