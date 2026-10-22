"""bug-568: the use guards read properties.triggers, not only legacy edges.

`use_actions` decided whether an item could be used by counting `triggers`
edges. After the task-886 migration a rule lives in
``properties['triggers']`` and has no edge, so a correctly authored item was
refused with "you can't use that". These tests pin both guards against both
stores.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from graph import Node, Edge, EDGE_IN, EDGE_TRIGGERS


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _area(w):
    from area import Area
    name = f"Guard Room {uuid.uuid4().hex[:8]}"
    w.movement.add_area(Area(name, "Empty.", []))
    w.set_player_area(w.active_player, name)
    return name


def _item(w, area, name, triggers=None, properties=None):
    props = {
        "name": name,
        "tags": [],
        "actions": [],
        "weight": 0.1,
        "uses": 3,
        "current_state": "normal",
    }
    if triggers is not None:
        props["triggers"] = triggers
    props.update(properties or {})
    node = Node(id=f"item_{name}", type="item", name=name, properties=props)
    w.graph.add_node(node)
    w.graph.add_edge(Edge(source=node.id, target=w.area_node_id(area), type=EDGE_IN))
    return node


def _definition(trigger_type, suffix=""):
    return {
        "id": f"trigger_item_guard_{trigger_type}{suffix}",
        "trigger_type": trigger_type,
        "effects": [{"type": "message", "params": {"message": f"{trigger_type} ran"}}],
    }


def test_use_is_allowed_by_an_on_use_property_trigger():
    w = _world()
    area = _area(w)
    _item(w, area, "guarded tonic", triggers=[_definition("on_use")])

    assert w.use_item("guarded tonic")


def test_use_runs_every_on_use_property_trigger():
    w = _world()
    area = _area(w)
    _item(w, area, "twice tonic", triggers=[
        {"id": "t_first", "trigger_type": "on_use",
         "effects": [{"type": "message", "params": {"message": "first fire"}}]},
        {"id": "t_second", "trigger_type": "on_use",
         "effects": [{"type": "message", "params": {"message": "second fire"}}]},
    ])

    out = w.use_item("twice tonic")

    assert "first fire" in out and "second fire" in out


def test_use_is_refused_without_any_trigger_or_action():
    w = _world()
    area = _area(w)
    _item(w, area, "plain pebble")

    with pytest.raises(ValueError):
        w.use_item("plain pebble")


def test_use_on_is_allowed_by_an_on_use_on_property_trigger():
    w = _world()
    area = _area(w)
    _item(w, area, "guarded key", triggers=[_definition("on_use_on")])
    _item(w, area, "guarded lock", properties={"tags": ["lock"]})

    assert w.use_item_on("guarded key", "guarded lock")


def test_use_on_still_reads_the_legacy_edge_store():
    w = _world()
    area = _area(w)
    node = _item(w, area, "legacy key")
    props = _definition("on_use_on")
    trig = Node(id=props["id"], type="logic_trigger", name=props["id"], properties=props)
    w.graph.add_node(trig)
    w.graph.add_edge(Edge(source=node.id, target=trig.id, type=EDGE_TRIGGERS,
                          properties=dict(props)))
    _item(w, area, "legacy lock", properties={"tags": ["lock"]})

    assert w.use_item_on("legacy key", "legacy lock")
