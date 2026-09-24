"""Consume-path depletion: spent items vanish, empty containers persist (task-424)."""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node, Edge, EDGE_IN, EDGE_TRIGGERS
from engine.background_simulation import BackgroundSimulation


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _area(w, name=None):
    # A fresh create_app world already ships a "Kitchen", and areas (unlike
    # items) hard-error on an id collision, so each test gets its own area name.
    from area import Area
    name = name or f"Depletion Room {uuid.uuid4().hex[:8]}"
    w.movement.add_area(Area(name, "Empty.", []))
    w.set_player_area(w.active_player, name)
    return name


def _item(w, area, name, *, tags, uses, triggers=()):
    node = Node(id=f"item_{name}", type="item", name=name,
                properties={"name": name, "tags": list(tags), "actions": [],
                            "weight": 0.1, "uses": uses, "current_state": "normal"})
    w.graph.add_node(node)
    w.graph.add_edge(Edge(source=node.id, target=w.area_node_id(area), type=EDGE_IN))
    for trigger in triggers:
        tid = f"trigger_{node.id}_{trigger['trigger_type']}"
        props = {"trigger_type": trigger["trigger_type"],
                 "effects": trigger["effects"]}
        if trigger.get("condition"):
            props["conditions"] = [trigger["condition"]]
        trig = Node(id=tid, type="logic_trigger", name=tid, properties=props)
        w.graph.add_node(trig)
        w.graph.add_edge(Edge(source=node.id, target=tid, type=EDGE_TRIGGERS,
                              properties=dict(props)))
    return node


def _eat(w, name):
    # The engine is the game-state facade the consume path expects (it exposes
    # `apply_action`); `world.eat_item` is the same public entry routes use.
    return w.eat_item(name)


def _drink(w, name):
    return w.drink_item(name)


def _spend_and_eat():
    return [
        {"trigger_type": "on_eat", "effects": [
            {"type": "adjust_vital", "params": {"stat": "Hunger", "amount": -45}},
            {"type": "adjust_uses", "params": {"node_id": "self", "delta": -1}},
        ]},
    ]


def test_authored_food_vanishes_at_last_use():
    w = _world()
    area = _area(w)
    node = _item(w, area, "bread", tags=["food"], uses=1, triggers=_spend_and_eat())
    w.player.vitals["Hunger"] = 80
    _eat(w, "bread")
    assert w.player.vitals["Hunger"] == 35, "the authored adjust_vital did not fire"
    assert w.graph.get_node(node.id) is None, "spent food was not consumed"


def test_an_empty_container_persists():
    w = _world()
    area = _area(w)
    node = _item(w, area, "glass", tags=["drink"], uses=1, triggers=[
        {"trigger_type": "on_drink", "effects": [
            {"type": "adjust_vital", "params": {"stat": "Thirst", "amount": -30}},
            {"type": "adjust_uses", "params": {"node_id": "self", "delta": -1}},
        ]},
        {"trigger_type": "on_depleted", "effects": [
            {"type": "set_state", "params": {"state": "empty",
                                             "message": "The glass is empty."}},
        ]},
    ])
    w.player.vitals["Thirst"] = 90
    _drink(w, "glass")
    kept = w.graph.get_node(node.id)
    assert kept is not None, "an emptied glass should stay in the world"
    assert kept.properties["current_state"] == "empty"
    assert kept.properties["uses"] == 0


def test_a_permanent_item_is_never_destroyed():
    w = _world()
    area = _area(w)
    node = _item(w, area, "everfull cup", tags=["drink"], uses=-1, triggers=[
        {"trigger_type": "on_drink", "effects": [
            {"type": "adjust_vital", "params": {"stat": "Thirst", "amount": -10}},
        ]},
    ])
    w.player.vitals["Thirst"] = 90
    _drink(w, "everfull cup")
    assert w.graph.get_node(node.id) is not None
    assert w.player.vitals["Thirst"] == 80


def test_an_empty_container_cannot_be_drunk_again():
    w = _world()
    area = _area(w)
    node = _item(w, area, "glass", tags=["drink"], uses=1, triggers=[
        {"trigger_type": "on_drink", "effects": [
            {"type": "adjust_uses", "params": {"node_id": "self", "delta": -1}},
        ]},
        {"trigger_type": "on_depleted", "effects": [
            {"type": "set_state", "params": {"state": "empty"}},
        ]},
    ])
    _drink(w, "glass")
    assert w.graph.get_node(node.id).properties["uses"] == 0
    try:
        _drink(w, "glass")
    except ValueError as e:
        assert "empty" in str(e).lower()
        return
    raise AssertionError("an empty glass was drinkable again")


def test_a_refilled_container_works_again():
    w = _world()
    area = _area(w)
    node = _item(w, area, "glass", tags=["drink"], uses=1, triggers=[
        {"trigger_type": "on_drink", "effects": [
            {"type": "adjust_vital", "params": {"stat": "Thirst", "amount": -20}},
            {"type": "adjust_uses", "params": {"node_id": "self", "delta": -1}},
        ]},
        {"trigger_type": "on_depleted", "effects": [
            {"type": "set_state", "params": {"state": "empty"}},
        ]},
    ])
    w.player.vitals["Thirst"] = 90
    _drink(w, "glass")
    # Refill: the same node is still here, so a refill makes it drinkable again.
    node.properties["uses"] = 1
    node.properties["current_state"] = "normal"
    _drink(w, "glass")
    assert w.player.vitals["Thirst"] == 50


def test_background_eating_uses_the_same_depletion():
    w = _world()
    area = _area(w)
    from player import Player
    p = Player("Forager")
    w.add_player(p)
    p.current_area = area
    w.set_player_area("Forager", area)
    p.simulation_mode = "background"
    p.state = "idle"
    p.activity = None
    p.vitals.update({"Hunger": 80, "Thirst": 0, "Energy": 100, "Bladder": 0})
    node = _item(w, area, "bread", tags=["food"], uses=1, triggers=_spend_and_eat())
    BackgroundSimulation(w).take_action(p, served=set(), remaining=10.0)
    assert p.vitals["Hunger"] == 35
    assert w.graph.get_node(node.id) is None
