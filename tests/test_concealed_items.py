"""task-516: concealed carried items (hidden pouches, backup knives).

`concealed: true` is owner-visible and other-hidden: it lists in the owner's
inventory and can be drawn, but it is skipped in what others see and cannot be
stolen until a `search <character>` Perception check reveals it. Equipping it
ends concealment.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch

from area import Area
from graph import Node, Edge, EDGE_CARRYING, EDGE_EQUIPPED
from player import Player


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    for name in ("Thief", "Target"):
        world.add_player(Player(name))
        world.name_matcher._set_player_area(name, "Room A")
    world.set_active_player("Thief")
    return world


def add_carried(world, owner, node_id, name, concealed=True, props=None):
    node = Node(id=node_id, type="item", name=name, properties={
        "name": name, "weight": 0.3, "current_state": "normal",
        "actions": ["examine", "take", "drop"], "tags": [],
        "concealed": True, **(props or {}),
    })
    world.graph.add_node(node)
    world.graph.add_edge(Edge(source=node.id, target=world._player_node_id(owner),
                              type=EDGE_CARRYING))
    return node


class TestConcealmentProperty:
    def test_library_property_is_bridged(self):
        from engine.library_nodes import library_item_properties
        props = library_item_properties({"concealed": True, "name": "Pouch"}, "pouch")
        assert props.get("concealed") is True

    def test_absent_flag_stays_absent(self):
        from engine.library_nodes import library_item_properties
        props = library_item_properties({"name": "Rock"}, "rock")
        assert "concealed" not in props


class TestOwnerVisibility:
    def test_owner_inventory_lists_a_concealed_item(self):
        world = make_world()
        add_carried(world, "Thief", "item_pouch", "Hidden Pouch")
        assert any("Hidden Pouch" in line for line in world.get_inventory())

    def test_concealed_item_hidden_from_other_character_equipment(self):
        world = make_world()
        node = add_carried(world, "Target", "item_knife", "Backup Knife")
        # Simulate it being worn while concealed (authored state).
        world.graph.remove_edge(node.id, world._player_node_id("Target"), EDGE_CARRYING)
        world.graph.add_edge(Edge(source=node.id, target=world._player_node_id("Target"),
                                  type=EDGE_EQUIPPED, properties={"slot": "hand"}))
        world.player_manager.get_player("Target").equipped.setdefault("hand", []).append(node.id)

        visible = world.equipment.get_visible_equipment("Target")
        assert "Backup Knife" not in list(visible.values())
        full = world.equipment.get_full_equipment("Target")
        assert "Backup Knife" in [n for names in full.values() for n in names]


class TestStealRequiresSearch:
    def test_stealing_a_concealed_item_is_refused(self):
        world = make_world()
        add_carried(world, "Target", "item_knife", "Backup Knife")
        try:
            world.steal_item("Backup Knife", "Target")
            assert False, "expected a refusal"
        except ValueError as exc:
            assert "hidden" in str(exc).lower() or "search" in str(exc).lower()

    def test_searching_reveals_and_then_stealing_works(self):
        world = make_world()
        node = add_carried(world, "Target", "item_knife", "Backup Knife")

        with patch.object(world.skills, "skill_check", return_value=(True, 20, "")):
            result = world.search_character("Target")
        assert "Backup Knife" in result
        assert not node.properties.get("concealed")

        world.player_manager.get_player("Thief").skills["Sleight of Hand"] = 20
        world.player_manager.get_player("Target").skills["Perception"] = 0
        with patch("engine.items.transfer_actions.random.randint", return_value=20):
            out = world.steal_item("Backup Knife", "Target")
        assert "steal" in out.lower() or "slip" in out.lower()
        assert world.player_manager.get_player("Thief")
        carried = [e.source for e in world.graph.get_edges_for_target(
            world._player_node_id("Thief"), EDGE_CARRYING)]
        assert "item_knife" in carried

    def test_failed_search_keeps_it_concealed(self):
        world = make_world()
        node = add_carried(world, "Target", "item_knife", "Backup Knife")
        with patch.object(world.skills, "skill_check", return_value=(False, 1, "You fail.")):
            world.search_character("Target")
        assert node.properties.get("concealed") is True


class TestEquipReveals:
    def test_equipping_clears_concealment(self):
        world = make_world()
        node = add_carried(world, "Thief", "item_knife", "Backup Knife",
                           props={"equip_slots": ["hands"], "damage": "1d4",
                                  "tags": ["weapon", "knife"]})
        assert node.properties.get("concealed")
        world.equipment.equip_item("Backup Knife")
        assert not node.properties.get("concealed")


class TestAuthoredContent:
    def _load(self, rel):
        import json
        return json.loads((Path(__file__).parent.parent / rel).read_text(encoding="utf-8-sig"))

    def test_krikka_hidden_pouch(self):
        d = self._load("data/library/items/krikka_hidden_pouch.json")
        assert d.get("concealed") is True
        assert "container" in d["tags"]
        assert d["contents"]

    def test_zikka_backup_knife(self):
        d = self._load("data/library/items/zikka_backup_knife.json")
        assert d.get("concealed") is True
        assert "weapon" in d["tags"] and d["damage"]

    def test_characters_carry_their_hidden_gear(self):
        krikka = self._load("data/library/characters/Krikka.json")
        zikka = self._load("data/library/characters/Zikka.json")
        assert "krikka_hidden_pouch" in krikka["inventory"]
        assert "zikka_backup_knife" in zikka["inventory"]
