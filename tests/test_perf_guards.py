"""Performance-regression guards for the long-horizon simulation work (task-413).

These assert the *shape* of the hot paths — call counts, index usage, buffer
bounds — instead of wall-clock time, which varies far too much with host load to
be a reliable test signal. If someone reintroduces an O(n) scan on a per-tick
path, one of these should fail.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import (
    EDGE_CONNECTION,
    EDGE_IN,
    EDGE_TRIGGERS,
    Edge,
    Node,
    WorldGraph,
)
from engine.lighting import LightingSystem
from engine.logging_events import GameLogger
from virtual_world_engine import VirtualWorld


# ── GameLogger.turn_events: bounded, not O(n) per append ───────────────────


def test_turn_events_are_capped():
    """A turn that never ends must not grow the buffer without bound."""
    logger = GameLogger()
    for i in range(5000):
        logger.record_turn_event("A", "move", f"step {i}", tick=i)
    assert len(logger.turn_events) == GameLogger._MAX_TURN_EVENTS


def test_turn_events_prune_when_the_turn_changes():
    logger = GameLogger()
    logger.record_turn_event("A", "move", "one", turn=1)
    logger.record_turn_event("B", "move", "two", turn=1)
    logger.record_turn_event("C", "move", "three", turn=2)
    assert [e["turn"] for e in logger.turn_events] == [2]

    logger.clear_turn_events()
    assert logger.turn_events == []
    # The prune flag must reset, or the next turn's first event is kept wrongly.
    logger.record_turn_event("D", "move", "four", turn=3)
    assert [e["turn"] for e in logger.turn_events] == [3]


# ── graph indexes: cheap removals, correct after direct mutation ───────────


def _chain_graph(n=20):
    graph = WorldGraph()
    for i in range(n):
        graph.add_node(Node(id=f"n{i}", type="item", name=f"n{i}"))
    for i in range(n - 1):
        graph.add_edge(Edge(source=f"n{i}", target=f"n{i + 1}", type=EDGE_IN))
    return graph


def test_remove_edge_does_not_rebuild_every_index(monkeypatch):
    graph = _chain_graph()
    calls = {"n": 0}
    original = graph._rebuild_indexes

    def counting():
        calls["n"] += 1
        return original()

    monkeypatch.setattr(graph, "_rebuild_indexes", counting)
    graph.remove_edge("n0", "n1", EDGE_IN)
    assert calls["n"] == 0, "remove_edge must unindex only the removed edge"
    assert graph.get_edges_for_source("n0", EDGE_IN) == []


def test_direct_edge_mutation_is_reindexed():
    """Effect handlers that touch ``graph.edges`` directly must not break lookups."""
    graph = WorldGraph()
    graph.add_node(Node(id="a", type="area", name="a"))
    graph.add_node(Node(id="b", type="item", name="b"))
    graph.edges.append(Edge(source="b", target="a", type=EDGE_IN))
    assert len(graph.get_edges_for_source("b", EDGE_IN)) == 1


# ── trigger sweep: visits only trigger owners ──────────────────────────────


def test_fire_turn_triggers_skips_nodes_without_triggers(monkeypatch):
    world = VirtualWorld()
    world.graph.add_node(Node(id="area_x", type="area", name="X"))
    world.graph.add_node(Node(id="char_y", type="character", name="Y"))

    seen = []

    def fake_execute(node, *args, **kwargs):
        seen.append(node.id)
        return []

    monkeypatch.setattr(world.triggers, "_execute_triggers", fake_execute)
    world._fire_turn_triggers("on_turn_start")
    assert seen == [], "nodes without a matching trigger must not be executed"


def test_fire_turn_triggers_runs_only_the_owner(monkeypatch):
    world = VirtualWorld()
    world.graph.add_node(Node(id="area_x", type="area", name="X"))
    world.graph.add_node(Node(id="trig_1", type="logic_trigger", name="t"))
    world.graph.add_edge(Edge(
        source="area_x",
        target="trig_1",
        type=EDGE_TRIGGERS,
        properties={"trigger_type": "on_turn_start"},
    ))
    world.graph.add_node(Node(id="area_other", type="area", name="Other"))

    seen = []

    def fake_execute(node, *args, **kwargs):
        seen.append(node.id)
        return []

    monkeypatch.setattr(world.triggers, "_execute_triggers", fake_execute)
    world._fire_turn_triggers("on_turn_start")
    assert seen == ["area_x"]


# ── lighting: brightest source wins, and is stamped per tick ───────────────


def _lit_item(item_id, level, area_id):
    return (
        Node(id=item_id, type="item", name=item_id, properties={
            "tags": ["light_source"],
            "current_state": "lit",
            "light_level": level,
        }),
        Edge(source=item_id, target=area_id, type=EDGE_IN),
    )


def test_many_dim_lights_do_not_stack():
    graph = WorldGraph()
    graph.add_node(Node(id="area_a", type="area", name="A",
                        properties={"environment": {"light": 10}}))
    for i in range(10):
        node, edge = _lit_item(f"torch_{i}", "dim", "area_a")
        graph.add_node(node)
        graph.add_edge(edge)

    lighting = LightingSystem(graph)
    # Ten dim torches read as one dim torch (30), never as a laser.
    assert lighting.get_ambient_light("area_a", env={"light": 10}) == 30


def test_effective_light_is_the_brightest_source():
    graph = WorldGraph()
    graph.add_node(Node(id="area_a", type="area", name="A",
                        properties={"environment": {"light": 10}}))
    for i in range(3):
        node, edge = _lit_item(f"dim_{i}", "dim", "area_a")
        graph.add_node(node)
        graph.add_edge(edge)
    node, edge = _lit_item("bright_1", "normal", "area_a")
    graph.add_node(node)
    graph.add_edge(edge)

    lighting = LightingSystem(graph)
    assert lighting.get_ambient_light("area_a", env={"light": 10}) == 55


def test_area_light_is_stamped_and_invalidated_by_graph_changes():
    graph = WorldGraph()
    graph.add_node(Node(id="area_a", type="area", name="A",
                        properties={"environment": {"light": 10}}))
    node, edge = _lit_item("torch_0", "normal", "area_a")
    graph.add_node(node)
    graph.add_edge(edge)

    lighting = LightingSystem(graph)
    lighting.recompute_area_lights()
    assert lighting.get_ambient_light("area_a") == 55

    # A graph mutation bumps the revision, so the stamp is dropped and the
    # light is recomputed against the new graph.
    graph.add_node(Node(id="area_b", type="area", name="B",
                        properties={"environment": {"light": 95}}))
    assert lighting.get_ambient_light("area_b") == 95
