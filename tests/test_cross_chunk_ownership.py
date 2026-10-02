"""Cross-chunk ownership: what survives an unload (task-584).

A character and its carried/equipped items are owned by the character, not by
the chunk they stand in; a live trigger is owned by whatever triggers it; a
delayed event aimed at an evicted node is loaded on demand, or deferred
explicitly — never dropped silently.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.world.index import GlobalScopeIndex
from graph import (EDGE_CARRYING, EDGE_IN, EDGE_TRIGGERS, Edge, Node,
                   WorldGraph)
from virtual_world_engine import VirtualWorld


def _world():
    world = VirtualWorld()
    world.player_manager.players = {}
    world.player_manager.active_player = None
    world.graph.add_node(Node(id="area_town", type="area", name="Town",
                              properties={"world_scope_id": "town"}))
    world.graph.add_node(Node(id="player_Traveler", type="character", name="Traveler"))
    world.graph.add_edge(Edge(source="player_Traveler", target="area_town", type=EDGE_IN))
    world.graph.add_node(Node(id="item_lamp", type="item", name="Lamp"))
    world.graph.add_edge(Edge(source="item_lamp", target="area_town", type=EDGE_IN))
    # A carried item is owned by the character, never by the chunk.
    world.graph.add_node(Node(id="item_sword", type="item", name="Sword"))
    world.graph.add_edge(Edge(source="item_sword", target="player_Traveler",
                              type=EDGE_CARRYING))
    world.world_index.reindex(world.graph, {"town": {"id": "town"}})
    return world


def _area_payload():
    return {"nodes": {"area_town": Node(
        id="area_town", type="area", name="Town",
        properties={"world_scope_id": "town"}).to_dict()}, "edges": []}


def test_character_and_carried_item_survive_an_unload():
    world = _world()
    result = world.world_index.unload(world.graph, "town")

    assert result["removed"] == ["area_town"]
    assert world.graph.get_node("player_Traveler") is not None
    assert world.graph.get_node("item_sword") is not None
    # The carried edge never touched the chunk.
    assert world.graph.get_edges_for_source("item_sword", EDGE_CARRYING)
    # Location of the survivors is remembered by id.
    assert result["recorded_locations"]["player_Traveler"] == "area_town"
    assert result["recorded_locations"]["item_lamp"] == "area_town"
    assert world.world_index.character_location("player_Traveler") == "area_town"


def test_location_edge_is_restored_when_the_scope_reloads():
    world = _world()
    world.world_index.unload(world.graph, "town")
    assert world.graph.get_edges_for_source("player_Traveler", EDGE_IN) == []

    world.world_index.register_loader(lambda scope_id: _area_payload()
                                      if scope_id == "town" else None)
    assert world.world_index.ensure_scope_loaded("town", world.graph)

    char_edges = world.graph.get_edges_for_source("player_Traveler", EDGE_IN)
    assert [e.target for e in char_edges] == ["area_town"]
    item_edges = world.graph.get_edges_for_source("item_lamp", EDGE_IN)
    assert [e.target for e in item_edges] == ["area_town"]


def test_restore_locations_is_idempotent():
    world = _world()
    world.world_index.register_loader(lambda scope_id: None)
    assert world.world_index.restore_locations(world.graph, "town") == 0


# ── triggers ────────────────────────────────────────────────────────────


def test_a_trigger_only_referenced_by_an_unloaded_node_is_removed():
    graph = WorldGraph()
    graph.add_node(Node(id="area_s", type="area", name="S",
                        properties={"world_scope_id": "s"}))
    graph.add_node(Node(id="item_hand", type="item", name="Hand Item"))
    graph.add_node(Node(id="trigger_orphan", type="logic_trigger", name="Orphan"))
    graph.add_node(Node(id="trigger_kept", type="logic_trigger", name="Kept"))
    graph.add_edge(Edge(source="area_s", target="trigger_orphan", type=EDGE_TRIGGERS))
    graph.add_edge(Edge(source="item_hand", target="trigger_kept", type=EDGE_TRIGGERS))

    result = graph.unload_scope("s")

    assert result["orphaned_triggers"] == ["trigger_orphan"]
    assert graph.get_node("trigger_orphan") is None
    # A trigger shared with a surviving owner is not cleaned up.
    assert graph.get_node("trigger_kept") is not None


# ── delayed events ──────────────────────────────────────────────────────


def _delayed_world(with_loader):
    world = _world()
    world.graph.add_node(Node(
        id="trigger_far", type="logic_trigger", name="Far Trigger",
        properties={"generated": {"scope_id": "inn"}}))
    world.world_index.reindex(world.graph, {"town": {"id": "town"}, "inn": {"id": "inn"}})
    if with_loader:
        payload = {"nodes": {"trigger_far": Node(
            id="trigger_far", type="logic_trigger", name="Far Trigger",
            properties={"generated": {"scope_id": "inn"}}).to_dict()}, "edges": []}
        world.world_index.register_loader(lambda scope_id: payload
                                          if scope_id == "inn" else None)
    world.delayed_events.schedule(0, "trigger_far", "on_delayed", "far event")
    world.time_ticks = 0
    return world


def test_a_due_event_loads_its_scope_and_fires():
    world = _delayed_world(with_loader=True)
    world.graph.remove_node("trigger_far")  # premise: evicted
    assert world.graph.get_node("trigger_far") is None

    world.time_ticks = 1
    world._process_delayed_events()

    assert world.graph.get_node("trigger_far") is not None
    assert world.delayed_events.events == []
    assert world.deferred_delayed_events == []
    assert world.unresolved_delayed_events == []


def test_a_due_event_with_an_unloadable_target_is_deferred_not_dropped():
    world = _delayed_world(with_loader=False)
    world.graph.remove_node("trigger_far")

    world.time_ticks = 1
    world._process_delayed_events()

    assert len(world.delayed_events.events) == 1, "the event must be requeued"
    assert world.delayed_events.events[0]["deferrals"] == 1
    assert world.deferred_delayed_events

    # After the bounded attempts it is recorded as unresolved, still never
    # silently discarded.
    for tick in range(2, 15):
        world.time_ticks = tick
        world._process_delayed_events()
    assert world.unresolved_delayed_events
    assert world.delayed_events.events == []
