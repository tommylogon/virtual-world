"""Tests for character AT way + relative facing (task-135, then task-313)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from virtual_world_engine import VirtualWorld
from area import Area
from player import Player
from graph import Edge, EDGE_AT, EDGE_IN, EDGE_ON, Node
from engine.character_spatial import (
    at_opening_phrase,
    default_relation_for_item,
    get_character_at_way,
    get_character_position,
    set_character_at_way,
    set_character_position,
    spatial_position_phrase,
)


def _shaft_world():
    """Three rooms whose middle one is a crawl-through shaft on the N/S ring.

    Entering the shaft from Lab A travels north, so the character faces north:
    "back" is south (the way it came) and "forward" is north (Lab B). This is
    the labs ventilation shaft's shape â€” two ways, opposite cardinals â€” with no
    transit tag, because relative facing is the default and never needed one.
    """
    world = VirtualWorld()
    world.movement.add_area(Area("Lab A", "First lab.", []))
    world.movement.add_area(Area("Ventilation Shaft", "A narrow metal shaft.", []))
    world.movement.add_area(Area("Lab B", "Second lab.", []))
    world.movement.connect_areas("Lab A", "Ventilation Shaft", "north", "south", state="open")
    world.movement.connect_areas("Ventilation Shaft", "Lab B", "north", "south", state="open")
    world.name_matcher._set_player_area(world.active_player, "Lab A")
    return world


class TestRelativeFacing:
    """The shaft, entered the way a character actually enters one (task-313).

    The old transit tests stood a character AT a way and asked for back/forward.
    That is a different situation â€” walking up to a door to examine it is not
    arriving through it â€” and it is why they were replaced rather than kept.
    """

    def test_crossing_stamps_facing_and_entry_way(self):
        world = _shaft_world()
        world.move_to_area("north")
        assert world.player.current_area == "Ventilation Shaft"
        assert world.player.facing == "north"
        assert world.player.entered_from_way == world._way_node_id("Lab A_north")

    def test_go_back_returns_the_way_you_came_in_by(self):
        world = _shaft_world()
        world.move_to_area("north")
        world.move_to_area("back")
        assert world.player.current_area == "Lab A"

    def test_go_forward_continues_the_heading(self):
        world = _shaft_world()
        world.move_to_area("north")
        world.move_to_area("forward")
        assert world.player.current_area == "Lab B"

    def test_facing_survives_a_turn_without_moving(self):
        world = _shaft_world()
        world.move_to_area("north")
        world.get_area_description()
        assert world.player.facing == "north"

    def test_look_shows_authored_handles_not_back_or_forward(self):
        """The whole point of dropping transit: the words alias, never rename."""
        world = _shaft_world()
        world.move_to_area("north")
        look = world.get_area_description()
        assert "[north] Lab B is visible beyond" in look
        assert "[back]" not in look
        assert "[forward]" not in look

    def test_authored_handle_still_resolves_alongside_relative_words(self):
        world = _shaft_world()
        world.move_to_area("north")
        world.move_to_area("north")          # the authored handle still works
        assert world.player.current_area == "Lab B"

    def test_no_facing_says_why_instead_of_a_generic_failure(self):
        world = _shaft_world()
        with pytest.raises(ValueError) as exc:
            world.move_to_area("left")
        assert "has not moved yet" in str(exc.value)


class TestCharacterAtWay:
    def test_examine_way_sets_at_edge(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.movement.add_area(Area("Room B", "Second room.", []))
        world.movement.connect_areas("Room A", "Room B", "north", "south", state="open")
        world.name_matcher._set_player_area(world.active_player, "Room A")

        world.get_item_desc("north")
        pid = world.player_manager.get_player_node_id(world.active_player)
        way_id = world.graph.get_node("way_Room A_north").id
        assert get_character_at_way(world.graph, pid) == way_id

    def test_open_door_approaches_and_sets_at(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.movement.add_area(Area("Room B", "Second room.", []))
        world.movement.connect_areas("Room A", "Room B", "north", "south", state="closed")
        world.name_matcher._set_player_area(world.active_player, "Room A")
        pid = world.player_manager.get_player_node_id(world.active_player)
        assert get_character_at_way(world.graph, pid) is None

        world.movement.toggle_way("north", "open")
        assert get_character_at_way(world.graph, pid) == world._way_node_id("Room A_north")

    def test_move_through_way_sets_at_edge(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.movement.add_area(Area("Room B", "Second room.", []))
        world.movement.connect_areas("Room A", "Room B", "north", "south", state="open")
        world.name_matcher._set_player_area(world.active_player, "Room A")

        world.move_to_area("north")
        pid = world.player_manager.get_player_node_id(world.active_player)
        # Same way node connects both rooms â€” you arrive AT it from the far side.
        assert get_character_at_way(world.graph, pid) == world._way_node_id("Room A_north")

    def test_at_opening_phrase_in_look(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.movement.add_area(Area("Room B", "Second room.", []))
        world.movement.connect_areas("Room A", "Room B", "north", "south", state="open")
        world.name_matcher._set_player_area(world.active_player, "Room A")
        world.get_item_desc("north")

        area_id = world._area_node_id("Room A")
        pid = world.player_manager.get_player_node_id(world.active_player)
        phrase = at_opening_phrase(world.graph, pid, area_id, "Room A")
        assert phrase == " at the north"


    def test_examine_room_clears_at_way(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.movement.add_area(Area("Room B", "Second room.", []))
        world.movement.connect_areas("Room A", "Room B", "north", "south", state="open")
        world.name_matcher._set_player_area(world.active_player, "Room A")
        world.get_item_desc("north")
        pid = world.player_manager.get_player_node_id(world.active_player)
        assert get_character_at_way(world.graph, pid) is not None

        world.get_item_desc("room")
        assert get_character_at_way(world.graph, pid) is None


class TestCharacterItemSpatial:
    def test_examine_item_sets_at_relation(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")
        table = Node(
            id="item_table",
            type="item",
            name="table",
            properties={"description": "A sturdy table.", "tags": ["furniture"]},
        )
        world.graph.add_node(table)
        world.graph.add_edge(Edge(source="item_table", target=world._area_node_id("Room A"), type=EDGE_IN))
        world.get_item_desc("table")
        pid = world.player_manager.get_player_node_id(world.active_player)
        pos = get_character_position(world.graph, pid)
        assert pos["target_id"] == "item_table"
        assert pos["relation"] == EDGE_AT

    def test_examine_ceiling_item_defaults_under(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")
        lamp = Node(
            id="item_chandelier",
            type="item",
            name="chandelier",
            properties={"description": "A heavy chandelier.", "tags": ["on_ceiling"]},
        )
        world.graph.add_node(lamp)
        world.graph.add_edge(Edge(source="item_chandelier", target=world._area_node_id("Room A"), type=EDGE_ON))
        assert default_relation_for_item(lamp) == "under"
        world.get_item_desc("chandelier from below")
        pid = world.player_manager.get_player_node_id(world.active_player)
        pos = get_character_position(world.graph, pid)
        assert pos["relation"] == "under"

    def test_witness_sees_item_position_in_look(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")
        piano = Node(
            id="item_piano",
            type="item",
            name="piano",
            properties={"description": "An old piano."},
        )
        world.graph.add_node(piano)
        world.graph.add_edge(Edge(source="item_piano", target=world._area_node_id("Room A"), type=EDGE_IN))
        hero = world.active_player
        jane = Player("Jane")
        jane.description = "A musician."
        jane.current_area = "Room A"
        world.player_manager.add_player(jane)
        world.set_active_player(hero)
        world.get_item_desc("piano")
        world.set_active_player("Jane")
        look = world.get_area_description()
        assert " at the piano" in look


class TestCharacterCharacterSpatial:
    def test_examine_person_sets_beside(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")
        hero = world.active_player
        jane = Player("Jane")
        jane.description = "A tall woman."
        jane.current_area = "Room A"
        world.player_manager.add_player(jane)
        world.set_active_player(hero)
        world.get_item_desc("Jane")
        pid = world.player_manager.get_player_node_id(hero)
        pos = get_character_position(world.graph, pid)
        assert pos["relation"] == "beside"
        assert pos["target_id"] == world.player_manager.get_player_node_id("Jane")

    def test_examine_self_does_not_set_position(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")
        world.get_item_desc("self")
        pid = world.player_manager.get_player_node_id(world.active_player)
        assert get_character_position(world.graph, pid) is None

    def test_attack_sets_beside_target(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")
        hero = world.active_player
        jane = Player("Jane")
        jane.description = "A tall woman."
        jane.current_area = "Room A"
        jane.vitals = {"HP": 20, "Energy": 50, "Hunger": 50, "Thirst": 50}
        jane.stats = {"STR": 10, "DEX": 10}
        world.player_manager.add_player(jane)
        world.set_active_player(hero)
        world.combat.player_attack(hero, "Jane")
        pid = world.player_manager.get_player_node_id(hero)
        pos = get_character_position(world.graph, pid)
        assert pos["relation"] == "beside"
        assert pos["target_id"] == world.player_manager.get_player_node_id("Jane")
