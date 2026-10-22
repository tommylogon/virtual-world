"""bug-566: a wrapped ``properties['triggers']`` value must not fail the load.

An item-library round trip once wrote a trigger definition wrapped under its own
key (``{"item": {...}}``, and the same wrapper around ``effects``). The
migration assumed a list and called ``.append`` on the dict, which raised
``AttributeError`` and failed the whole scenario load. These tests pin the
normalisation shape, the property-only path (no ``triggers`` edge) and the
dedupe when a legacy edge and a wrapped property entry describe the same rule.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import EDGE_TRIGGERS, Edge, Node, WorldGraph
from engine.serialization import WorldSerializer
from engine.triggers.effect_resolution import (
    normalize_trigger_entry,
    normalize_trigger_list,
)
from engine.triggers.materialize import materialize_trigger


# The shape measured on disk: a wrapper around a definition, with the effects
# wrapped twice more and trigger_type wrapped once.
WRAPPED = {
    "item": {
        "id": "trigger_item_bottle_on_use",
        "trigger_type": {"item": ["on_use", "on_drink"]},
        "conditions": "",
        "conditions_logic": "and",
        "effects": {"item": {"item": [
            {"type": "adjust_vital", "params": {"stat": "thirst", "amount": "-30"}},
            {"type": "adjust_uses", "params": {"delta": "-1"}},
        ]}},
        "success_message": "you take a drink.",
        "fail_message": "its empty",
    }
}


def _migrated(graph):
    WorldSerializer(graph, None, None)._migrate_triggers_from_nodes_to_properties()
    return graph


def _owner(graph, props):
    node = Node(id="item_bottle", type="item", name="Water bottle", properties=props)
    graph.add_node(node)
    return node


def test_wrapped_definition_normalises_to_one_entry():
    entries = normalize_trigger_list(WRAPPED)

    assert len(entries) == 1
    entry = entries[0]
    assert entry["id"] == "trigger_item_bottle_on_use"
    assert entry["trigger_type"] == ["on_use", "on_drink"]
    assert [e["type"] for e in entry["effects"]] == ["adjust_vital", "adjust_uses"]
    assert "conditions" not in entry


def test_wrapper_around_a_list_yields_every_entry():
    entries = normalize_trigger_list({"item": [WRAPPED["item"], WRAPPED["item"]]})

    assert len(entries) == 2
    assert all(e["id"] == "trigger_item_bottle_on_use" for e in entries)


def test_property_only_node_is_normalised_without_any_triggers_edge():
    graph = WorldGraph()
    owner = _owner(graph, {"triggers": WRAPPED})

    assert not [e for e in graph.edges if e.type == EDGE_TRIGGERS]
    _migrated(graph)

    assert isinstance(owner.properties["triggers"], list)
    assert len(owner.properties["triggers"]) == 1
    assert owner.properties["triggers"][0]["effects"][1]["type"] == "adjust_uses"


def test_wrapped_entry_and_legacy_edge_with_the_same_id_dedupe():
    graph = WorldGraph()
    owner = _owner(graph, {"triggers": WRAPPED})
    graph.add_node(Node(
        id="trigger_item_bottle_on_use",
        type="logic_trigger",
        name="on_use",
        properties={"trigger_type": "on_use", "effects": []},
    ))
    graph.add_edge(Edge(
        source=owner.id,
        target="trigger_item_bottle_on_use",
        type=EDGE_TRIGGERS,
        properties={"trigger_type": "on_use"},
    ))

    _migrated(graph)

    assert len(owner.properties["triggers"]) == 1
    assert graph.get_node("trigger_item_bottle_on_use") is None
    assert not [e for e in graph.edges if e.type == EDGE_TRIGGERS]


def test_a_legacy_edge_still_migrates_into_an_empty_property_list():
    graph = WorldGraph()
    owner = _owner(graph, {})
    graph.add_node(Node(
        id="trigger_item_bottle_on_eat",
        type="logic_trigger",
        name="on_eat",
        properties={"trigger_type": "on_eat", "effects": []},
    ))
    graph.add_edge(Edge(
        source=owner.id,
        target="trigger_item_bottle_on_eat",
        type=EDGE_TRIGGERS,
        properties={"effects": [{"type": "message", "params": {"message": "crunch"}}]},
    ))

    _migrated(graph)

    assert len(owner.properties["triggers"]) == 1
    entry = owner.properties["triggers"][0]
    assert entry["id"] == "trigger_item_bottle_on_eat"
    assert entry["effects"][0]["type"] == "message"


def test_materialize_repairs_a_wrapped_list_instead_of_crashing():
    graph = WorldGraph()
    owner = _owner(graph, {"triggers": WRAPPED})

    trigger_id = materialize_trigger(graph, owner.id, {
        "trigger_type": "on_take",
        "effects": [{"type": "message", "params": {"message": "taken"}}],
    })

    entries = owner.properties["triggers"]
    assert isinstance(entries, list)
    assert len(entries) == 2
    assert entries[0]["id"] == "trigger_item_bottle_on_use"
    assert any(t["id"] == trigger_id for t in entries)
