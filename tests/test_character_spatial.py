"""Tests for character AT way + transit back/forward (task-135)."""
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
    get_transit_roles,
    is_transit_area,
    set_character_at_way,
    set_character_position,
    spatial_position_phrase,
)


def _transit_world():
    """Two rooms connected by a tagged transit shaft with two ways."""
    world = VirtualWorld()
    world.movement.add_area(Area("Lab A", "First lab.", []))
    world.movement.add_area(Area("Ventilation Shaft", "A narrow metal shaft.", []))
    shaft = world.graph.get_node(world._area_node_id("Ventilation Shaft"))
    shaft.properties["tags"] = ["transit"]
    world.movement.add_area(Area("Lab B", "Second lab.", []))
    world.movement.connect_areas("Lab A", "Ventilation Shaft", "vent", "back", state="open")
    world.movement.connect_areas("Ventilation Shaft", "Lab B", "forward", "vent", state="open")

    world.name_matcher._set_player_area(world.active_player, "Ventilation Shaft")
    return world


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
        # Same way node connects both rooms — you arrive AT it from the far side.
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


class TestTransitAreas:
    def test_is_transit_area_by_tag(self):
        world = _transit_world()
        shaft = world.graph.get_node("area_Ventilation_Shaft")
        assert is_transit_area(shaft)

    def test_transit_roles_when_at_way(self):
        world = _transit_world()
        pid = world.player_manager.get_player_node_id(world.active_player)
        area_id = world.graph.get_node("area_Ventilation_Shaft").id
        back_way = world.graph.get_node("way_Lab A_vent").id
        set_character_at_way(world.graph, pid, back_way)

        roles = get_transit_roles(world.graph, area_id, pid, "Ventilation Shaft")
        assert roles is not None
        assert roles["back_handle"] == "back"
        assert roles["forward_handle"] == "forward"
        assert roles["forward_target"] == "Lab B"

    def test_go_back_in_transit(self):
        world = _transit_world()
        pid = world.player_manager.get_player_node_id(world.active_player)
        back_way = world.graph.get_node("way_Lab A_vent").id
        set_character_at_way(world.graph, pid, back_way)

        world.move_to_area("back")
        assert world.player.current_area == "Lab A"

    def test_go_forward_in_transit(self):
        world = _transit_world()
        pid = world.player_manager.get_player_node_id(world.active_player)
        back_way = world.graph.get_node("way_Lab A_vent").id
        set_character_at_way(world.graph, pid, back_way)

        world.move_to_area("forward")
        assert world.player.current_area == "Lab B"

    def test_look_shows_back_forward_handles(self):
        world = _transit_world()
        pid = world.player_manager.get_player_node_id(world.active_player)
        back_way = world.graph.get_node("way_Lab A_vent").id
        set_character_at_way(world.graph, pid, back_way)

        look = world.get_area_description()
        assert "To the back" in look
        assert "To the forward" in look

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
