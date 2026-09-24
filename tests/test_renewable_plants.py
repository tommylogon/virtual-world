"""Renewable plant cycle: growth, spawn, reset, cap (task-410 verification).

Drives the real trigger pipeline on a **library-hydrated** berry bush, which is
the path a spawned plant takes. The scenario embeds its bushes directly; this
also covers the hydrate path (`_materialize_spawn_triggers`).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from graph import Node, Edge, EDGE_IN


AREA = "Deep Forest"


def _world():
    from virtual_world_engine import VirtualWorld
    w = VirtualWorld()
    w.time_per_tick_minutes = 1
    w.movement.add_area(Area(AREA, "Tall trees and undergrowth.", []))
    w.name_matcher._set_player_area(w.active_player, AREA)
    return w


def _place_plant(w):
    node, _lib = w.effects._hydrate_item("bush_of_berries", {}, always_fresh=True)
    area_id = w.get_current_area_id()
    w.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
    return node


def _fire(w, plant):
    return w.triggers._execute_triggers(plant, "on_tick", game_state=w)


def _produce(w, plant):
    return [w.graph.get_node(e.source)
            for e in w.graph.get_edges_for_target(plant.id, EDGE_IN)]


def _berry(w, plant, name="Berries"):
    node = Node(id=f"item_{name}_{id(plant)}_{len(_produce(w, plant))}",
                type="item", name=name,
                properties={"name": name, "tags": ["food"], "actions": [],
                            "count": 1, "weight": 0.1})
    w.graph.add_node(node)
    w.graph.add_edge(Edge(source=node.id, target=plant.id, type=EDGE_IN))
    return node


def test_growth_increments_by_game_minute():
    w = _world()
    plant = _place_plant(w)
    assert plant.properties["parameters"]["growth"] == 0
    _fire(w, plant)
    assert plant.properties["parameters"]["growth"] == 1, \
        "the hydrated plant's on_tick growth trigger did not fire"


def test_mature_plant_spawns_produce_and_resets():
    w = _world()
    plant = _place_plant(w)
    plant.properties["parameters"]["growth"] = 100
    _fire(w, plant)

    produce = _produce(w, plant)
    assert produce, "a mature plant produced nothing"
    assert w.graph.get_node(plant.id) is not None, "the plant itself was removed"
    assert plant.properties["parameters"]["growth"] == 0, "growth did not reset"


def test_plant_respects_the_produce_cap():
    w = _world()
    plant = _place_plant(w)
    for _ in range(10):
        _berry(w, plant)
    plant.properties["parameters"]["growth"] = 100
    _fire(w, plant)

    assert len(_produce(w, plant)) == 10, "the plant exceeded its 10-produce cap"
    assert plant.properties["parameters"]["growth"] == 100, \
        "growth reset even though nothing was spawned"


def test_the_plant_itself_is_not_food():
    w = _world()
    plant = _place_plant(w)
    tags = {str(t).lower() for t in (plant.properties.get("tags") or [])}
    assert "food" not in tags, "a plant tagged food would be eaten and deleted"
