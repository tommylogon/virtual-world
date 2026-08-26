"""Regression: PlayerManager.current_area + find_item_node must resolve area
ids case-insensitively.

Scenario files create area nodes with lowercase ids (e.g. "area_task_7")
while player.current_area stores the display name ("Task 7"). The derived
id "area_Task_7" doesn't match the node, so the current_area property
returned None and find_item_node could never see room objects — `use Button
7` in the same room said "You don't have 'button 7'."
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import WorldGraph, Node, Edge, EDGE_IN
from player import Player
from engine.player_manager import PlayerManager


def _case_graph():
    g = WorldGraph()
    g.add_node(Node(id="area_task_7", type="area", name="Task 7",
                    properties={"description": "A room."}))
    g.add_node(Node(id="item_button_7", type="item", name="Button 7",
                    properties={"actions": ["examine", "use"]}))
    g.add_edge(Edge(source="item_button_7", target="area_task_7", type=EDGE_IN))
    return g


def test_find_item_node_resolves_room_object_case_insensitive():
    g = _case_graph()
    pm = PlayerManager(g)
    player = Player("John")
    player.current_area = "Task 7"  # display name, node id is area_task_7
    pm.add_player(player)
    pm.set_active_player("John")

    assert pm.current_area is not None
    assert pm.current_area.name == "Task 7"

    node = pm.find_item_node("Button 7")
    assert node is not None
    assert node.name == "Button 7"


def test_graph_lookups_are_case_insensitive():
    """The graph layer itself must resolve ids case-insensitively so no
    caller ever has to remember to lowercase (the root cause of the
    'You don't have button 7' bug)."""
    g = _case_graph()

    # get_node with wrong case
    assert g.get_node("AREA_TASK_7") is not None
    assert g.get_node("Area_Task_7") is not None
    assert g.get_node("item_BUTTON_7") is not None
    # edge lookups with wrong case on either endpoint
    assert len(g.get_edges_for_source("ITEM_BUTTON_7", EDGE_IN)) == 1
    assert len(g.get_edges_for_target("AREA_TASK_7", EDGE_IN)) == 1
    # remove_edge case-insensitive
    g.remove_edge("ITEM_BUTTON_7", "AREA_TASK_7", EDGE_IN)
    assert len(g.get_edges_for_source("item_button_7", EDGE_IN)) == 0
    # remove_node case-insensitive
    g.remove_node("AREA_TASK_7")
    assert g.get_node("area_task_7") is None


def test_graph_edge_dedup_is_case_insensitive():
    g = _case_graph()
    # duplicate add with different case must not double up
    g.add_edge(Edge(source="ITEM_BUTTON_7", target="AREA_TASK_7", type=EDGE_IN))
    assert len([e for e in g.edges if e.type == EDGE_IN]) == 1


def test_graph_index_survives_load_round_trip():
    g = _case_graph()
    data = g.to_dict()
    g2 = WorldGraph()
    g2.load_from_dict(data)
    assert g2.get_node("AREA_TASK_7") is not None
    assert len(g2.get_edges_for_target("AREA_TASK_7", EDGE_IN)) == 1
