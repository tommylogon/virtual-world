"""task-442: trigger definitions materialise into ordinary logic_trigger nodes.

The blueprint (trigger graph) editor compiles to the trigger-definition JSON
contract; these tests pin the Python half — materialising that contract creates
the same ``logic_trigger`` node + ``triggers`` edge every other authoring path
creates, the edge/node copies agree, and a condition branch reaches the engine.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import EDGE_TRIGGERS, EDGE_IN, Edge, Node, WorldGraph
from engine.triggers.materialize import (
    materialize_trigger,
    materialize_triggers,
    trigger_properties,
)
from engine.trigger_system import TriggerSystem
from engine.skills import SkillSystem
from engine.player_manager import PlayerManager
from engine.logging_events import GameLogger


def _trigger_system(graph):
    return TriggerSystem(graph, SkillSystem(PlayerManager(None), GameLogger()), GameLogger())


def _item(graph, item_id="item_lamp", props=None):
    node = Node(id=item_id, type="item", name="Lamp", properties=props or {"uses": 3})
    graph.add_node(node)
    return node


def test_materialize_creates_logic_trigger_node_and_triggers_edge():
    graph = WorldGraph()
    item = _item(graph)
    tid = materialize_trigger(graph, item.id, {
        "trigger_type": "on_use",
        "effects": [{"type": "message", "params": {"message": "The lamp glows."}}],
    })

    node = graph.get_node(tid)
    assert node is not None and node.type == "logic_trigger"
    assert node.properties["trigger_type"] == "on_use"
    assert node.properties["effects"][0]["type"] == "message"

    edges = graph.get_edges_for_source(item.id, EDGE_TRIGGERS)
    assert len(edges) == 1
    assert edges[0].target == tid
    # The engine reads the edge first; the node is the fallback. Both copies agree.
    assert edges[0].properties == node.properties


def test_legacy_effect_type_normalises_and_resolves():
    graph = WorldGraph()
    item = _item(graph)
    tid = materialize_trigger(graph, item.id, {
        "trigger_type": "on_use",
        "effect_type": "adjust_vital",
        "effect_params": {"stat": "Hunger", "amount": 20},
    })
    edge = graph.get_edges_for_source(item.id, EDGE_TRIGGERS)[0]
    from engine.triggers.effect_resolution import _resolve_trigger_effects
    effects = _resolve_trigger_effects(edge, graph)
    assert effects == [{"type": "adjust_vital", "params": {"stat": "Hunger", "amount": 20}}]


def test_condition_branch_reaches_the_engine():
    graph = WorldGraph()
    item = _item(graph)
    tree = {"operator": "or", "conditions": [
        {"type": "eq", "target": "a", "value": "yes"},
        {"type": "eq", "target": "b", "value": "yes"},
    ]}
    materialize_trigger(graph, item.id, {
        "trigger_type": "on_use", "conditions": tree,
        "effects": [{"type": "message", "params": {"message": "ok"}}],
    })
    edge = graph.get_edges_for_source(item.id, EDGE_TRIGGERS)[0]
    ts = _trigger_system(graph)
    # One branch true -> OR passes; both false -> OR fails.
    assert ts._evaluate_conditions(edge.properties["conditions"],
                                   {"a": "no", "b": "yes"}, game_state=None) is True
    assert ts._evaluate_conditions(edge.properties["conditions"],
                                   {"a": "no", "b": "no"}, game_state=None) is False


def test_flat_conditions_keep_their_logic():
    graph = WorldGraph()
    item = _item(graph)
    materialize_trigger(graph, item.id, {
        "trigger_type": "on_use",
        "conditions": [{"type": "eq", "target": "a", "value": "yes"}],
        "conditions_logic": "or",
        "effects": [{"type": "message", "params": {"message": "ok"}}],
    })
    edge = graph.get_edges_for_source(item.id, EDGE_TRIGGERS)[0]
    assert edge.properties["conditions_logic"] == "or"
    assert edge.properties["conditions"] == [{"type": "eq", "target": "a", "value": "yes"}]


def test_empty_effects_are_dropped_not_faked():
    props = trigger_properties({"trigger_type": "on_use", "effects": [], "conditions": []})
    assert "effects" not in props
    assert "conditions" not in props
    assert props == {"trigger_type": "on_use"}


def test_materialize_triggers_skips_empty_entries():
    graph = WorldGraph()
    item = _item(graph)
    ids = materialize_triggers(graph, item.id, [
        {"trigger_type": "on_use", "effects": [{"type": "message", "params": {}}]},
        {},
        None,
        {"trigger_type": "on_take", "effects": [{"type": "message", "params": {}}]},
    ])
    assert len(ids) == 2
    assert len(graph.get_edges_for_source(item.id, EDGE_TRIGGERS)) == 2


def test_attach_route_materialises_onto_a_live_node():
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    node = Node(id="item_bp_target", type="item", name="Target", properties={"uses": -1})
    world.graph.add_node(node)

    client = app.test_client()
    resp = client.post("/api/triggers/attach", json={
        "node_id": "item_bp_target",
        "trigger": {
            "trigger_type": "on_use",
            "conditions": {"operator": "and", "conditions": [
                {"type": "eq", "target": "a", "value": "yes"}]},
            "effects": [{"type": "message", "params": {"message": "attached"}}],
        },
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "success" and len(body["trigger_ids"]) == 1
    tid = body["trigger_ids"][0]
    assert world.graph.get_node(tid).type == "logic_trigger"

    missing = client.post("/api/triggers/attach",
                          json={"node_id": "nope", "trigger": {"trigger_type": "on_use"}})
    assert missing.status_code == 404
