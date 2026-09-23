"""Two condition types added for gauge/container gating (task-410).

`uses_reached` / `uses_above` already gate on `uses`, but `uses` is remaining
charges/durability: the consume and crafting paths delete a node at `uses <= 0`,
and examine/stacking/carry-weight present it as durability. A growth counter that
starts at 0 would read as a broken item.

So counters get their own gate over the node's `parameters` dict
(`parameter_reached`) and containers get a count gate (`contains_count`), which is
what a plant needs to stop producing at its cap.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import Node, Edge, EDGE_IN


def _world():
    return create_app({"TESTING": True}).world


def _item(world, node_id, name="Thing", **properties):
    node = Node(id=node_id, type="item", name=name, properties=dict(properties))
    world.graph.add_node(node)
    return node


def _cond(world, node, **cond):
    return world.triggers._evaluate_conditions(cond, {"item_node": node})


# ── parameter_reached ────────────────────────────────────────────────────


def test_parameter_reached_gates_on_a_gauge():
    world = _world()
    node = _item(world, "item_bush", "Berry Bush")
    node.properties["parameters"] = {"growth": 0}

    assert _cond(world, node, type="parameter_reached", key="growth", value=100) is False
    node.properties["parameters"]["growth"] = 100
    assert _cond(world, node, type="parameter_reached", key="growth", value=100) is True


def test_parameter_reached_accepts_parameter_as_the_key_alias():
    world = _world()
    node = _item(world, "item_tree")
    node.properties["parameters"] = {"nuts": 5}
    assert _cond(world, node, type="parameter_reached", parameter="nuts", value=3) is True


def test_parameter_reached_operators():
    world = _world()
    node = _item(world, "item_crate")
    node.properties["parameters"] = {"charge": 5}
    assert _cond(world, node, type="parameter_reached", key="charge", value=5) is True       # default gte
    assert _cond(world, node, type="parameter_reached", key="charge", value=6) is False
    assert _cond(world, node, type="parameter_reached", key="charge", value=5, op="gt") is False
    assert _cond(world, node, type="parameter_reached", key="charge", value=4, op="gt") is True
    assert _cond(world, node, type="parameter_reached", key="charge", value=5, op="lte") is True
    assert _cond(world, node, type="parameter_reached", key="charge", value=5, op="eq") is True
    assert _cond(world, node, type="parameter_reached", key="charge", value=9, op="nonsense") is False


def test_parameter_reached_tolerates_junk_and_missing():
    world = _world()
    node = _item(world, "item_odd")
    # No parameters at all: a missing gauge reads as 0, which is the honest
    # answer for a counter that has never moved.
    assert _cond(world, node, type="parameter_reached", key="growth", value=0) is True
    assert _cond(world, node, type="parameter_reached", key="growth", value=1) is False
    # No key at all is unanswerable, not a pass.
    assert _cond(world, node, type="parameter_reached", value=1) is False
    # Non-numeric stored value fails safe rather than raising.
    node.properties["parameters"] = {"growth": "ripe"}
    assert _cond(world, node, type="parameter_reached", key="growth", value=1) is False


# ── contains_count ───────────────────────────────────────────────────────


def _containing(world, parent, children):
    for child in children:
        world.graph.add_edge(Edge(source=child.id, target=parent.id, type=EDGE_IN))


def test_contains_count_counts_held_items():
    world = _world()
    bush = _item(world, "item_bush2", "Berry Bush")
    berries = [_item(world, "item_berry_%d" % i, "Berries") for i in range(3)]
    _containing(world, bush, berries)

    assert _cond(world, bush, type="contains_count", value=3) is True
    assert _cond(world, bush, type="contains_count", value=4) is False


def test_contains_count_lt_is_the_cap_check():
    """A plant stops producing while it already holds its limit."""
    world = _world()
    bush = _item(world, "item_bush3", "Berry Bush")
    berries = [_item(world, "item_b_%d" % i, "Berries") for i in range(10)]
    _containing(world, bush, berries)

    assert _cond(world, bush, type="contains_count", value=10, op="lt") is False   # full
    assert _cond(world, bush, type="contains_count", value=11, op="lt") is True    # room left

    world.graph.remove_node("item_b_9")
    assert _cond(world, bush, type="contains_count", value=10, op="lt") is True


def test_contains_count_filters_by_name():
    world = _world()
    basket = _item(world, "item_basket", "Basket")
    _containing(world, basket, [
        _item(world, "item_apple_1", "Apple"),
        _item(world, "item_apple_2", "Apple"),
        _item(world, "item_rock_1", "Rock"),
    ])
    assert _cond(world, basket, type="contains_count", value=2, target="apple") is True
    assert _cond(world, basket, type="contains_count", value=3, target="apple") is False
    assert _cond(world, basket, type="contains_count", value=3) is True     # unfiltered


def test_contains_count_on_an_empty_container():
    world = _world()
    empty = _item(world, "item_empty_box", "Box")
    assert _cond(world, empty, type="contains_count", value=0) is True
    assert _cond(world, empty, type="contains_count", value=1) is False
    assert _cond(world, empty, type="contains_count", value=1, op="lt") is True


# ── registration ─────────────────────────────────────────────────────────


def test_both_types_are_registered_with_the_validator():
    """A condition the evaluator understands but the validator rejects would be
    stripped on save/reload."""
    from engine.trigger_validator import CONDITION_TYPES
    assert "parameter_reached" in CONDITION_TYPES
    assert "contains_count" in CONDITION_TYPES
