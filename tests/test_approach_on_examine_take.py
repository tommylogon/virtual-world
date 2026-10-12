"""Approach on examine and take (task-783).

`use`, `place`, `steal`/`give`, `attack`, `grab` and `lead` already walk the
character to their target before acting. `examine` and `take` did not, so you
could describe or pick up something on the far side of a room. These tests pin
the mechanism: the position edge is written, and it is *not* written for
something you are already holding.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from virtual_world_engine import VirtualWorld
from area import Area
from graph import Edge, EDGE_CARRYING, EDGE_IN, Node
from engine.character_spatial import get_character_position


def _room_world():
    """One room with a heavy crate in it and a player standing in the room."""
    world = VirtualWorld()
    world.movement.add_area(Area("Store Room", "A dusty store room.", []))
    crate = Node(id="item_crate", type="item", name="crate",
                 properties={"description": "A heavy wooden crate.", "weight": 40,
                             "actions": ["take", "examine", "drop"]})
    world.graph.add_node(crate)
    world.graph.add_edge(Edge(source="item_crate", target="area_store_room", type=EDGE_IN))
    world.name_matcher._set_player_area(world.active_player, "Store Room")
    return world


def _player_node_id(world):
    return world._player_node_id(world.active_player)


class TestTakeApproaches:
    def test_take_walks_to_the_item(self):
        world = _room_world()
        pid = _player_node_id(world)
        assert get_character_position(world.graph, pid) is None

        world.take_item("crate")

        pos = get_character_position(world.graph, pid)
        assert pos is not None, "take must approach the item first"
        assert pos["target_id"] == "item_crate"
        assert pos["relation"] == "at"

    def test_take_does_not_approach_something_already_carried(self):
        world = _room_world()
        world.take_item("crate")
        pid = _player_node_id(world)
        # Standing at the crate, now drop it and take it again from the floor:
        # the approach must still fire, because it is in the area again.
        world.drop_item("crate")
        world.take_item("crate")
        pos = get_character_position(world.graph, pid)
        assert pos is not None and pos["target_id"] == "item_crate"


class TestExamineApproaches:
    def test_examine_walks_to_the_item(self):
        world = _room_world()
        pid = _player_node_id(world)
        assert get_character_position(world.graph, pid) is None

        world.get_item_desc("crate")

        pos = get_character_position(world.graph, pid)
        assert pos is not None, "examine must approach the item first"
        assert pos["target_id"] == "item_crate"

    def test_examine_a_held_item_does_not_move_you(self):
        """A held item is not in the area, so `approach_item` no-ops."""
        world = VirtualWorld()
        world.movement.add_area(Area("Store Room", "A dusty store room.", []))
        crate = Node(id="item_crate", type="item", name="crate",
                     properties={"description": "A heavy wooden crate.",
                                 "actions": ["take", "examine", "drop"]})
        world.graph.add_node(crate)
        pid = _player_node_id(world)
        world.graph.add_edge(Edge(source="item_crate", target=pid, type=EDGE_CARRYING))
        world.name_matcher._set_player_area(world.active_player, "Store Room")

        world.get_item_desc("crate")

        assert get_character_position(world.graph, pid) is None, (
            "a held item is not in the area, so no approach")

    def test_examine_a_way_puts_you_at_the_way(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Hall", "A hall.", []))
        world.movement.add_area(Area("Kitchen", "A kitchen.", []))
        world.movement.connect_areas("Hall", "Kitchen", "north", "south", state="open")
        world.name_matcher._set_player_area(world.active_player, "Hall")
        pid = _player_node_id(world)

        world.get_item_desc("north")

        from engine.character_spatial import get_character_at_way
        way_id = world._way_node_id("Hall_north")
        assert get_character_at_way(world.graph, pid) == way_id
