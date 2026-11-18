"""Tests for bug-588: visible held/worn equipment on People here without leaking stowed inventory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from graph import Node, Edge, EDGE_CARRYING, EDGE_EQUIPPED
from player import Player


def _make_world(light=80):
    from virtual_world_engine import VirtualWorld

    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "A plain room.", [], environment={"light": light}))
    for name in ("Viewer", "Guard"):
        p = Player(name)
        p.description = f"{name} stands ready."
        world.add_player(p)
        world.name_matcher._set_player_area(name, "Room A")
    world.set_active_player("Viewer")
    return world


def _add_item(world, owner, node_id, name, props=None):
    node = Node(
        id=node_id,
        type="item",
        name=name,
        properties={
            "name": name,
            "weight": 1.0,
            "current_state": "normal",
            "actions": ["examine", "take", "drop"],
            "tags": [],
            **(props or {}),
        },
    )
    world.graph.add_node(node)
    world.graph.add_edge(Edge(source=node.id, target=world._player_node_id(owner), type=EDGE_CARRYING))
    return node


def _equip_direct(world, owner, node, slot):
    player = world.player_manager.get_player(owner)
    world.graph.remove_edge(node.id, world._player_node_id(owner), EDGE_CARRYING)
    world.graph.add_edge(
        Edge(source=node.id, target=world._player_node_id(owner), type=EDGE_EQUIPPED, properties={"slot": slot})
    )
    player.equipped.setdefault(slot, []).append(node.id)


class TestGetPlayersInAreaEquipment:
    def test_exposes_held_and_outer_worn_and_hides_stowed_and_concealed(self):
        world = _make_world(light=80)
        pistol = _add_item(world, "Guard", "item_pistol", "Pistol", {"equip_slots": ["hand_right"]})
        _equip_direct(world, "Guard", pistol, "hand_right")

        shirt = _add_item(world, "Guard", "item_shirt", "Undershirt", {"equip_slots": ["torso"]})
        coat = _add_item(world, "Guard", "item_coat", "Trenchcoat", {"equip_slots": ["torso"]})
        _equip_direct(world, "Guard", shirt, "torso")
        _equip_direct(world, "Guard", coat, "torso")

        # Stowed pocket item (EDGE_CARRYING only)
        _add_item(world, "Guard", "item_keycard", "Keycard")
        # Concealed equipped item
        backup = _add_item(world, "Guard", "item_backup", "Backup Knife", {"concealed": True})
        _equip_direct(world, "Guard", backup, "hand_left")
        # Hidden state equipped item
        amulet = _add_item(world, "Guard", "item_amulet", "Hidden Amulet", {"current_state": "hidden"})
        _equip_direct(world, "Guard", amulet, "neck")

        people = world.player_manager.get_players_in_area("Room A")
        assert len(people) == 1
        guard = people[0]
        assert guard["name"] == "Guard"
        assert guard["holding"] == ["Pistol"]
        assert guard["wearing"] == ["Trenchcoat"]
        assert "Keycard" not in guard["holding"] and "Keycard" not in guard["wearing"]
        assert "Undershirt" not in guard["wearing"]
        assert "Backup Knife" not in guard["holding"]
        assert "Hidden Amulet" not in guard["wearing"]

    def test_two_handed_weapon_deduplicated_in_holding(self):
        world = _make_world(light=80)
        rifle = _add_item(world, "Guard", "item_rifle", "Rifle", {"tags": ["two_handed"]})
        _equip_direct(world, "Guard", rifle, "hand_right")
        world.player_manager.get_player("Guard").equipped.setdefault("hand_left", []).append("__multi_slot_item_rifle")

        people = world.player_manager.get_players_in_area("Room A")
        assert people[0]["holding"] == ["Rifle"]

    def test_dim_and_pitch_black_gate_equipment_unless_dark_vision(self):
        for light_val in (30, 10):  # dim (<=40) and pitch_black (<=20)
            world = _make_world(light=light_val)
            pistol = _add_item(world, "Guard", "item_pistol", "Pistol")
            _equip_direct(world, "Guard", pistol, "hand_right")
            coat = _add_item(world, "Guard", "item_coat", "Coat")
            _equip_direct(world, "Guard", coat, "torso")

            people = world.player_manager.get_players_in_area("Room A")
            assert people[0]["holding"] == []
            assert people[0]["wearing"] == []

            # Grant dark_vision to Viewer
            viewer = world.player_manager.get_player("Viewer")
            viewer.traits["dark_vision"] = True
            people_dv = world.player_manager.get_players_in_area("Room A")
            assert people_dv[0]["holding"] == ["Pistol"]
            assert people_dv[0]["wearing"] == ["Coat"]


class TestAreaDescriptionEquipmentVisibility:
    def test_area_description_uses_visible_equipment_and_hides_stowed(self):
        world = _make_world(light=80)
        pistol = _add_item(world, "Guard", "item_pistol", "Pistol")
        _equip_direct(world, "Guard", pistol, "hand_right")
        coat = _add_item(world, "Guard", "item_coat", "Trenchcoat")
        _equip_direct(world, "Guard", coat, "torso")
        _add_item(world, "Guard", "item_pocket_watch", "Pocket Watch")
        concealed = _add_item(world, "Guard", "item_shiv", "Concealed Shiv", {"concealed": True})
        _equip_direct(world, "Guard", concealed, "hand_left")

        text = world.area_description.get_area_description()
        assert "[wearing: Trenchcoat]" in text
        assert "[holding: Pistol]" in text
        assert "Pocket Watch" not in text
        assert "Concealed Shiv" not in text

    def test_area_description_dim_light_hides_gear(self):
        world = _make_world(light=30)
        pistol = _add_item(world, "Guard", "item_pistol", "Pistol")
        _equip_direct(world, "Guard", pistol, "hand_right")

        text = world.area_description.get_area_description()
        assert "Pistol" not in text
        assert "[holding:" not in text
