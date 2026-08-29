"""Authored `known` registry: entity refs a character knows from the start.

Hidden ways become visible (way_visible_to), and the player-update route
persists the list (inspector "Known by" control saves through it).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node
from engine.room_perception import way_visible_to


def _world():
    from virtual_world_engine import VirtualWorld
    return VirtualWorld()


def test_known_way_is_visible_to_viewer():
    world = _world()
    viewer = world.player_manager.players[world.active_player]
    way = Node(id="way_secret_passage", type="way", name="secret passage",
               properties={"current_state": "hidden"})
    viewer.known = ["way_secret_passage"]
    assert way_visible_to(viewer, world.player_manager, world.active_player,
                          way, "slaughterhouse", "sewer_passage") is True


def test_unknown_way_stays_hidden_for_non_slasher():
    world = _world()
    viewer = world.player_manager.players[world.active_player]
    way = Node(id="way_secret_passage", type="way", name="secret passage",
               properties={"current_state": "hidden"})
    viewer.known = []
    assert way_visible_to(viewer, world.player_manager, world.active_player,
                          way, "slaughterhouse", "sewer_passage") is False


def test_known_area_reveals_its_ways():
    world = _world()
    viewer = world.player_manager.players[world.active_player]
    way = Node(id="way_secret_passage", type="way", name="secret passage",
               properties={"current_state": "hidden"})
    viewer.known = ["slaughterhouse"]
    assert way_visible_to(viewer, world.player_manager, world.active_player,
                          way, "slaughterhouse", "sewer_passage") is True


def test_known_item_is_visible_when_hidden():
    from graph import WorldGraph, Edge, EDGE_IN
    from engine.room_perception import visible_area_items
    world = _world()
    viewer = world.player_manager.players[world.active_player]
    g = WorldGraph()
    area = Node(id="area_test", type="area", name="Test Room", properties={"description": "x"})
    stash = Node(id="item_stash", type="item", name="Hidden Stash",
                 properties={"current_state": "hidden"})
    g.add_node(area)
    g.add_node(stash)
    g.add_edge(Edge(source=stash.id, target=area.id, type=EDGE_IN))

    assert [n.name for n in visible_area_items(g, area.id)] == []
    viewer.known = ["item_stash"]
    assert "Hidden Stash" in [n.name for n in visible_area_items(g, area.id, player=viewer)]


def test_update_player_known_route():
    from app import create_app
    app = create_app({"TESTING": True})
    name = next(iter(app.world.player_manager.players))
    client = app.test_client()
    resp = client.post(f"/api/players/{name}",
                       json={"known": ["way_secret_passage", "area_foyer"]})
    assert resp.status_code == 200
    player = app.world.player_manager.players[name]
    assert "way_secret_passage" in player.known
    assert "area_foyer" in player.known

    resp2 = client.post(f"/api/players/{name}", json={"known": []})
    assert resp2.status_code == 200
    assert player.known == []
