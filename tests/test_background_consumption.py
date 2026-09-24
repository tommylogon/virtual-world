"""Background consumption uses the authored path (task-424)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node, Edge, EDGE_IN, EDGE_TRIGGERS
from player import Player
from engine.background_simulation import BackgroundSimulation, MEAL_RESTORE, DRINK_RESTORE


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _area(w, name="Test Larder"):
    from area import Area
    w.movement.add_area(Area(name, "Empty.", []))
    return name


def _forager(w, area, hunger=80, thirst=0):
    p = Player("Forager")
    w.add_player(p)
    p.current_area = area
    w.set_player_area("Forager", area)
    p.simulation_mode = "background"
    p.state = "idle"
    p.activity = None
    p.vitals.update({"Hunger": hunger, "Thirst": thirst, "Energy": 100, "Bladder": 0})
    return p


def _item(w, area, name, tags, *, triggers=None):
    node = Node(id=f"item_{name}", type="item", name=name,
                properties={"name": name, "tags": list(tags), "actions": [],
                            "weight": 0.1, "count": 1})
    w.graph.add_node(node)
    w.graph.add_edge(Edge(source=node.id, target=w.area_node_id(area), type=EDGE_IN))
    for trigger in (triggers or []):
        tid = f"trigger_{node.id}_{trigger['trigger_type']}"
        trig = Node(id=tid, type="logic_trigger", name=tid,
                    properties={"trigger_type": trigger["trigger_type"],
                                "effects": trigger["effects"]})
        w.graph.add_node(trig)
        w.graph.add_edge(Edge(source=node.id, target=tid, type=EDGE_TRIGGERS,
                              properties=dict(trig.properties)))
    return node


def test_authored_consumption_runs_the_items_trigger():
    w = _world()
    area = _area(w)
    p = _forager(w, area)
    node = _item(w, area, "hearty stew", ["food"], triggers=[{
        "trigger_type": "on_eat",
        "effects": [
            {"type": "adjust_vital", "params": {"stat": "Hunger", "amount": -20}},
            {"type": "remove_item", "params": {"item_id": "item_hearty stew"}},
        ],
    }])
    used = BackgroundSimulation(w).take_action(p, served=set(), remaining=10.0)
    assert p.vitals["Hunger"] == 60, "did not use the authored -20, not MEAL_RESTORE"
    assert p.vitals["Hunger"] != 80 - MEAL_RESTORE
    assert w.graph.get_node(node.id) is None, "the authored remove did not run"


def test_authored_drink_runs_the_items_trigger():
    w = _world()
    area = _area(w)
    p = _forager(w, area, hunger=0, thirst=90)
    node = _item(w, area, "cold tea", ["drink"], triggers=[{
        "trigger_type": "on_drink",
        "effects": [
            {"type": "adjust_vital", "params": {"stat": "Thirst", "amount": -35}},
            {"type": "remove_item", "params": {"item_id": "item_cold tea"}},
        ],
    }])
    BackgroundSimulation(w).take_action(p, served=set(), remaining=10.0)
    assert p.vitals["Thirst"] == 55
    assert w.graph.get_node(node.id) is None


def test_fallback_consumption_is_unchanged_for_silent_items():
    w = _world()
    area = _area(w)
    p = _forager(w, area)
    node = _item(w, area, "plain bread", ["food"])
    BackgroundSimulation(w).take_action(p, served=set(), remaining=10.0)
    assert p.vitals["Hunger"] == 80 - MEAL_RESTORE
    assert w.graph.get_node(node.id) is None


def test_an_item_without_authored_tags_is_not_eaten():
    w = _world()
    area = _area(w)
    p = _forager(w, area)
    node = _item(w, area, "heavy rock", ["stone"])
    BackgroundSimulation(w).take_action(p, served=set(), remaining=10.0)
    assert p.vitals["Hunger"] == 80
    assert w.graph.get_node(node.id) is not None
