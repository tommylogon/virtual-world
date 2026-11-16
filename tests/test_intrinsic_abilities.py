"""Tests for intrinsic abilities (task-737): non-physical possession verbs and carrier grant/revoke."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import Node, Edge, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN, WorldGraph
from player import Player
from engine.equipment import EquipmentSystem, is_intrinsic_ability
from engine.player_manager import PlayerManager
from engine.logging_events import GameLogger
from engine.items.take_drop_actions import TakeDropActionsMixin
from engine.items.place_actions import PlaceActionsMixin
from engine.items.transfer_actions import TransferActionsMixin


class MockTriggerSystem:
    def _execute_triggers(self, item_node, trigger_type, target_name=None, context=None, expected_target_state=None, game_state=None):
        return []

    def _get_available_actions(self, item_node):
        return ["use"]

    def _contextual_failure(self, verb, name, available):
        return f"Cannot {verb} {name}."


class Harness(TakeDropActionsMixin, PlaceActionsMixin, TransferActionsMixin):
    def __init__(self, graph, pm):
        self.graph = graph
        self.player_manager = pm
        self.trigger_system = MockTriggerSystem()
        self.ghost_system = type("Ghost", (), {"check_ghost_action": lambda *a: None})()
        self.matching = type("Match", (), {
            "_is_item_reachable": lambda *a: True,
            "match_item_name_in_inventory": lambda *a: None,
            "_match_character_name": lambda self, name: (None, [])
        })()
        self.world = None

    def _check_player_capacity(self, pm, weight):
        return None

    def _exec_triggers(self, item_node, trigger_type):
        return []

    def _find_stack_by_name(self, name, area_id):
        return None

    def _find_pool_by_yield(self, name, area_id):
        return None


def setup_sim():
    graph = WorldGraph()
    pm = PlayerManager(graph)
    logger = GameLogger()
    triggers = MockTriggerSystem()
    eq = EquipmentSystem(graph, triggers, logger, pm)

    # Set up area with id matching area_laboratory
    area = Node(id="area_laboratory", type="area", name="Laboratory", properties={"environment": {"ambient_light": 100}})
    graph.add_node(area)

    # Set up active player
    p1 = Player(name="Alice")
    p1.current_area = "Laboratory"
    p1.state = "normal"
    pm.players["Alice"] = p1
    pm.active_player = "Alice"
    p1_node = Node(id="player_alice", type="player", name="Alice", properties={})
    graph.add_node(p1_node)
    graph.add_edge(Edge(source=p1_node.id, target=area.id, type=EDGE_IN))

    # Set up second player
    p2 = Player(name="Bob")
    p2.current_area = "Laboratory"
    p2.state = "normal"
    pm.players["Bob"] = p2
    p2_node = Node(id="player_bob", type="player", name="Bob", properties={})
    graph.add_node(p2_node)
    graph.add_edge(Edge(source=p2_node.id, target=area.id, type=EDGE_IN))

    # Wire helper methods on pm
    pm._player_node_id = lambda name: f"player_{name.lower().replace(' ', '_')}"
    pm._get_current_area_id = lambda: area.id
    pm.item_node_id = lambda name: f"item_{name.lower().replace(' ', '_')}"
    pm.lighting = type("LightingStub", (), {
        "can_see_in_dark": lambda *a: True,
        "get_ambient_light": lambda *a: 100
    })()

    def find_item_node(name):
        for n in graph.nodes.values():
            if n.type == "item" and n.name.lower() == name.lower():
                return n
        return None
    pm.find_item_node = find_item_node

    harness = Harness(graph, pm)
    return graph, pm, eq, harness, area, p1_node, p2_node


def test_is_intrinsic_ability():
    spell_node = Node(id="n1", type="item", name="invisibility", properties={"tags": ["spell", "power"]})
    physical_node = Node(id="n2", type="item", name="iron_key", properties={"tags": ["tool", "metal"]})
    assert is_intrinsic_ability(spell_node) is True
    assert is_intrinsic_ability(physical_node) is False


def test_drop_place_stow_refused():
    graph, pm, eq, harness, area, p1_node, _ = setup_sim()

    # Add an intrinsic ability to Alice
    ability = Node(id="spell_invis", type="item", name="invisibility", properties={
        "tags": ["spell", "ability", "intrinsic"],
        "weight": 0.0
    })
    graph.add_node(ability)
    graph.add_edge(Edge(source=ability.id, target=p1_node.id, type=EDGE_CARRYING))

    # drop must be refused
    with pytest.raises(ValueError, match="is an intrinsic ability, not a thing you can set down"):
        harness.drop_item(pm, "invisibility")

    # place must be refused
    table = Node(id="item_table", type="item", name="table", properties={"tags": ["furniture", "surface"]})
    graph.add_node(table)
    graph.add_edge(Edge(source=table.id, target=area.id, type=EDGE_IN))
    with pytest.raises(ValueError, match="is an intrinsic ability, not a physical object you can place"):
        harness.place_item(pm, "invisibility", "table", "on")

    # stow must be refused when held/equipped
    graph.add_edge(Edge(source=ability.id, target=p1_node.id, type=EDGE_EQUIPPED, properties={"slot": "ability"}))
    with pytest.raises(ValueError, match="is an intrinsic ability, not a physical object you can stow"):
        harness.stow_item(pm, "invisibility")


def test_take_give_steal_refused():
    graph, pm, eq, harness, area, p1_node, p2_node = setup_sim()

    # Intrinsic ability in the area cannot be taken
    ability = Node(id="spell_teleport", type="item", name="teleportation", properties={
        "tags": ["power", "innate"],
        "actions": ["take", "use"]
    })
    graph.add_node(ability)
    graph.add_edge(Edge(source=ability.id, target=area.id, type=EDGE_IN))

    with pytest.raises(ValueError, match="is an intrinsic ability, not a physical object you can take"):
        harness.take_item(pm, "teleportation")

    # Intrinsic ability carried by Alice cannot be given to Bob
    graph.remove_edges_for_node(ability.id, EDGE_IN)
    graph.add_edge(Edge(source=ability.id, target=p1_node.id, type=EDGE_CARRYING))

    with pytest.raises(ValueError, match="is an intrinsic ability, not a physical object you can give away"):
        harness.give_item(pm, "teleportation", "Bob")

    # Intrinsic ability on Bob cannot be stolen by Alice
    graph.remove_edges_for_node(ability.id, EDGE_CARRYING)
    graph.add_edge(Edge(source=ability.id, target=p2_node.id, type=EDGE_CARRYING))

    with pytest.raises(ValueError, match="is an intrinsic ability, not a physical object you can steal"):
        harness.steal_item(pm, "teleportation", "Bob")


def test_carrier_grant_and_revoke_roundtrip():
    graph, pm, eq, harness, area, p1_node, _ = setup_sim()

    # Carrier item: hacking chip that grants 'system_override'
    chip = Node(id="item_chip", type="item", name="cyber_chip", properties={
        "equip_slots": ["head"],
        "grants_ability": "system_override"
    })
    graph.add_node(chip)
    graph.add_edge(Edge(source=chip.id, target=p1_node.id, type=EDGE_CARRYING))

    # Equip carrier
    msg = eq.equip_item("cyber_chip", "head")
    assert "equip the cyber_chip" in msg

    # Verify ability was granted to Alice
    granted_edges = [e for e in graph.get_edges_for_target(p1_node.id, EDGE_EQUIPPED)
                     if "ability" in e.source or e.properties.get("slot") == "ability"]
    assert len(granted_edges) == 1
    ability_node = graph.get_node(granted_edges[0].source)
    assert ability_node.name == "system_override"
    assert is_intrinsic_ability(ability_node) is True
    assert ability_node.properties.get("granted_by") == "item_chip"

    # Unequip carrier
    msg_unequip = eq.unequip_item(item_name="cyber_chip")
    assert "unequipped" in msg_unequip or "remove" in msg_unequip

    # Verify ability was revoked
    remaining = [e for e in graph.get_edges_for_target(p1_node.id, EDGE_EQUIPPED)
                 if e.source == ability_node.id]
    assert len(remaining) == 0
    assert graph.get_node(ability_node.id) is None


def test_intrinsic_abilities_stay_out_of_appearance():
    graph, pm, eq, harness, area, p1_node, _ = setup_sim()

    # Normal shirt + intrinsic aura
    shirt = Node(id="item_shirt", type="item", name="blue_shirt", properties={"equip_slots": ["torso"]})
    aura = Node(id="spell_aura", type="item", name="flame_aura", properties={"tags": ["spell", "intrinsic"]})
    graph.add_node(shirt)
    graph.add_node(aura)

    graph.add_edge(Edge(source=shirt.id, target=p1_node.id, type=EDGE_EQUIPPED, properties={"slot": "torso"}))
    graph.add_edge(Edge(source=aura.id, target=p1_node.id, type=EDGE_EQUIPPED, properties={"slot": "aura"}))

    raw_equipment = {"torso": ["blue_shirt"], "aura": ["flame_aura"]}
    visible = eq._drop_intrinsic_abilities(raw_equipment, "Alice")
    assert "torso" in visible
    assert visible["torso"] == ["blue_shirt"]
    assert "aura" in visible
    assert visible["aura"] == []  # stripped from visible appearance


def test_effects_grant_and_revoke_ability():
    graph, pm, eq, harness, area, p1_node, _ = setup_sim()
    from engine.effects import Effects
    effects = Effects(graph, GameLogger())
    game_state = type("GameStateStub", (), {"equipment": eq, "active_player": "Alice"})()

    # grant effect
    effects.execute("grant_ability", {"ability": "shadow_meld", "target": "Alice"}, context={}, game_state=game_state)
    assert graph.get_node("ability_alice_shadow_meld") is not None

    # revoke effect
    effects.execute("revoke_ability", {"ability": "shadow_meld", "target": "Alice"}, context={}, game_state=game_state)
    assert graph.get_node("ability_alice_shadow_meld") is None
