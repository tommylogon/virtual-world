"""The failed-examine fallback (bug-565).

A lookup miss lists what the character can examine. That list must be the
character's own room, must not repeat a node that the spatial expansion returns
twice, and must not name a concealed way or item. The log that found this had
kyrie in the foyer being told the library's prompt, and the fallback listing
`sewer_passage_back (hidden)` plus jake and kayla twice.
"""
import pytest

from area import Area
from graph import Edge, EDGE_AT, EDGE_CONNECTION, EDGE_IN, Node
from player import Player
from virtual_world_engine import VirtualWorld


def _world():
    world = VirtualWorld()
    world.movement.add_area(Area("Hall", "A dusty hall.", []))

    alice = Player("Alice")
    bob = Player("Bob")
    world.add_player(alice)
    world.add_player(bob)
    world.player_manager.active_player = "Alice"
    world.name_matcher._set_player_area("Alice", "Hall")
    world.name_matcher._set_player_area("Bob", "Hall")
    alice.relationships["Bob"] = {"closeness": 0}

    lamp = Node(
        id="item_lamp",
        type="item",
        name="lamp",
        properties={"description": "A brass lamp.", "current_state": "normal"},
    )
    world.graph.add_node(lamp)
    world.graph.add_edge(Edge(source="item_lamp", target="area_hall", type=EDGE_IN))

    # Bob stands at the lamp. The EDGE_IN expansion treats the lamp as an
    # anchor and returns this `at` edge too, so a naive walk lists Bob twice.
    world.graph.add_edge(
        Edge(source=world._player_node_id("Bob"), target="item_lamp", type=EDGE_AT)
    )

    north = Node(
        id="way_north",
        type="way",
        name="north door",
        properties={"current_state": "closed", "direction": "north"},
    )
    secret = Node(
        id="way_secret",
        type="way",
        name="secret passage",
        properties={"current_state": "hidden", "direction": "south"},
    )
    world.graph.add_node(north)
    world.graph.add_node(secret)
    world.graph.add_edge(
        Edge(
            source="area_hall",
            target="way_north",
            type=EDGE_CONNECTION,
            properties={"direction": "north"},
        )
    )
    world.graph.add_edge(
        Edge(
            source="way_north",
            target="area_hall",
            type=EDGE_CONNECTION,
            properties={"direction": "north"},
        )
    )
    world.graph.add_edge(
        Edge(
            source="area_hall",
            target="way_secret",
            type=EDGE_CONNECTION,
            properties={"direction": "south"},
        )
    )
    world.graph.add_edge(
        Edge(
            source="way_secret",
            target="area_hall",
            type=EDGE_CONNECTION,
            properties={"direction": "south"},
        )
    )
    return world


def _fallback_text(world):
    with pytest.raises(ValueError) as exc:
        world.get_item_desc("nothing at all")
    return str(exc.value)


def test_fallback_is_grouped_and_lists_the_room():
    text = _fallback_text(_world())
    assert "items: lamp" in text
    assert "people: Bob" in text
    assert "paths:" in text
    assert "north" in text


def test_fallback_does_not_duplicate_a_spatially_placed_character():
    text = _fallback_text(_world())
    assert text.count("Bob") == 1


def test_fallback_does_not_offer_a_hidden_way():
    text = _fallback_text(_world())
    assert "secret passage" not in text
    assert "hidden" not in text
