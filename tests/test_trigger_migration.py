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


def test_legacy_unlocks_edge_migrates_to_on_use_on_trigger():
    from graph import EDGE_UNLOCKS
    graph = WorldGraph()
    key = Node(id="item_rusty_key", type="item", name="Rusty Key", properties={})
    door = Node(id="way_dungeon_door", type="way", name="Heavy Iron Door", properties={"current_state": "locked"})
    graph.add_node(key)
    graph.add_node(door)
    graph.add_edge(Edge(source="item_rusty_key", target="way_dungeon_door", type=EDGE_UNLOCKS))

    serializer = WorldSerializer(graph, None, None)
    serializer._migrate_unlocks_edges_to_triggers()

    assert not any(e.type == EDGE_UNLOCKS for e in graph.edges)
    triggers = key.properties.get("triggers", [])
    assert len(triggers) == 1
    t = triggers[0]
    assert t["trigger_type"] == "on_use_on"
    assert t["target_name"] == "Heavy Iron Door"
    assert len(t["effects"]) == 1
    assert t["effects"][0]["type"] == "unlock_way"
    assert t["effects"][0]["params"]["way_id"] == "way_dungeon_door"


def test_get_trigger_sources_indexes_property_triggers():
    graph = WorldGraph()
    candle = Node(
        id="item_candle",
        type="item",
        name="Candle",
        properties={"triggers": [{"trigger_type": "on_tick"}, {"trigger_type": ["on_turn_start", "on_turn_end"]}]}
    )
    graph.add_node(candle)

    assert set(graph.get_trigger_sources("on_tick")) == {"item_candle"}
    assert set(graph.get_trigger_sources("on_turn_start")) == {"item_candle"}
    assert set(graph.get_trigger_sources("on_turn_end")) == {"item_candle"}
    assert graph.get_trigger_sources("on_take") == []


def test_migrate_legacy_item_effect_props():
    """task-332: Legacy effect_stat/effect_amount/effect_target props migrated to triggers on load."""
    graph = WorldGraph()
    apple = Node(
        id="item_apple",
        type="item",
        name="Juicy Apple",
        properties={
            "effect_stat": "Hunger",
            "effect_amount": 20,
            "effect_target": "player",
            "actions": ["use"],
            "uses": 1,
        }
    )
    lamp = Node(
        id="item_lamp",
        type="item",
        name="Brass Lantern",
        properties={
            "effect_stat": "light",
            "effect_amount": 0,
            "effect_target": "room",
            "actions": ["use"],
        }
    )
    c4 = Node(
        id="item_c4",
        type="item",
        name="C4 Explosive",
        properties={
            "effect_stat": "broken",
            "effect_amount": 0,
            "effect_target": "connection",
            "actions": ["use"],
        }
    )
    null_item = Node(
        id="item_stick",
        type="item",
        name="Stick",
        properties={
            "effect_stat": None,
            "effect_amount": 0,
            "effect_target": None,
        }
    )
    graph.add_node(apple)
    graph.add_node(lamp)
    graph.add_node(c4)
    graph.add_node(null_item)

    serializer = WorldSerializer(graph, None, None)
    serializer._migrate_legacy_item_effects()

    # 1. Vital conversion
    assert "effect_stat" not in apple.properties
    assert "effect_amount" not in apple.properties
    assert "effect_target" not in apple.properties
    apple_triggers = apple.properties.get("triggers", [])
    assert len(apple_triggers) == 1
    assert apple_triggers[0]["trigger_type"] == "on_use"
    assert apple_triggers[0]["effects"][0]["type"] == "adjust_vital"
    assert apple_triggers[0]["effects"][0]["params"]["vital"] == "Hunger"
    assert apple_triggers[0]["effects"][0]["params"]["amount"] == 20

    # 2. Light conversion
    assert "effect_stat" not in lamp.properties
    assert "light_source" in lamp.properties["tags"]
    assert "toggle" in lamp.properties["actions"]
    assert lamp.properties["light_level"] == "normal"
    assert lamp.properties["current_state"] == "unlit"

    # 3. Connection conversion
    assert "effect_stat" not in c4.properties
    c4_triggers = c4.properties.get("triggers", [])
    assert len(c4_triggers) == 1
    assert c4_triggers[0]["trigger_type"] == "on_use_on"
    assert c4_triggers[0]["effects"][0]["type"] == "set_state"
    assert c4_triggers[0]["effects"][0]["params"]["state"] == "broken"

    # 4. Null stripping
    assert "effect_stat" not in null_item.properties
    assert "effect_amount" not in null_item.properties
    assert "effect_target" not in null_item.properties
    assert "triggers" not in null_item.properties
