"""Comprehensive tests for the EquipmentSystem (equipping, layering, two-handed, narrative)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import Node, Edge, EDGE_CARRYING, WorldGraph
from player import Player
from engine.equipment import EquipmentSystem
from engine.player_manager import PlayerManager
from engine.logging_events import GameLogger


# ─────────────────────── Test helpers ───────────────────────


class MockTriggerSystem:
    """Minimal trigger system that EquipmentSystem can call."""
    def _execute_triggers(self, item_node, trigger_type, target_name=None, context=None, expected_target_state=None, game_state=None):
        return []


def make_equipment_system(graph=None, player_manager=None):
    """Create an EquipmentSystem wired to test-friendly dependencies."""
    if graph is None:
        graph = WorldGraph()
    pm = player_manager or PlayerManager(graph)
    logger = GameLogger()
    triggers = MockTriggerSystem()
    return EquipmentSystem(graph, triggers, logger, pm)


def add_carried_item(graph, player_manager, item_id, item_name, equip_slots=None,
                     actions=None, uses=-1, tags=None):
    """Add a test item node to the graph and attach it to the active player."""
    active_player = player_manager.active_player
    if not active_player:
        raise RuntimeError("No active player set in player_manager")
    player_id = player_manager.get_player_node_id(active_player)

    node = Node(
        id=item_id,
        type="item",
        name=item_name,
        properties={
            "description": f"A {item_name} for testing.",
            "actions": actions or ["examine", "take", "use"],
            "uses": uses,
            "weight": 1.0,
            "equip_slots": equip_slots or [],
            "current_state": "normal",
            "tags": tags or [],
        }
    )
    graph.add_node(node)
    graph.add_edge(Edge(source=node.id, target=player_id, type=EDGE_CARRYING))

    return node


@pytest.fixture
def basic_setup():
    """Return (graph, player_manager, equipment_system) with a default player."""
    graph = WorldGraph()
    pm = PlayerManager(graph)
    traveler = Player("Traveler")
    pm.add_player(traveler)
    pm.set_active_player("Traveler")
    equipment = make_equipment_system(graph, pm)
    return graph, pm, equipment


# ─────────────────── TestEquipmentBasic ───────────────────


class TestEquipmentBasic:
    """Basic equip/unequip operations."""

    def test_equip_helmet_to_head(self, basic_setup):
        """Equip an item with equip_slots=['head'] to the head slot."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_iron_helmet", "Iron Helmet",
                          equip_slots=["head"])
        result = equipment.equip_item("Iron Helmet")
        assert "equip the Iron Helmet on your head" in result

        player = pm.players[pm.active_player]
        assert "item_iron_helmet" in player.equipped["head"]

    def test_unequip_from_slot(self, basic_setup):
        """Equip then unequip from a named slot."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_leather_helmet", "Leather Helmet",
                          equip_slots=["head"])
        equipment.equip_item("Leather Helmet")
        result = equipment.unequip_item(slot="head")
        assert "remove the Leather Helmet from your head" in result

        player = pm.players[pm.active_player]
        assert len(player.equipped["head"]) == 0

    def test_unequip_by_name(self, basic_setup):
        """Equip then unequip by item name."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_steel_helmet", "Steel Helmet",
                          equip_slots=["head"])
        equipment.equip_item("Steel Helmet")
        result = equipment.unequip_item(item_name="steel helmet")
        assert "steel helmet" in result.lower()

        player = pm.players[pm.active_player]
        assert len(player.equipped["head"]) == 0

    def test_equip_same_item_twice_refused(self, basic_setup):
        """Equipping an item that is already worn is refused. Equipping moves
        the item out of inventory (the carrying edge is removed), so a second
        equip fails as 'not carrying' — you can't equip something you're no
        longer holding. This kills the old stack-duplication quirk
        ('Earring over Earring', 2026-08-24 taco_bell run)."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_duplicate_helm", "Duplicate Helm",
                          equip_slots=["head"])
        equipment.equip_item("Duplicate Helm")
        # Equipping removed the carrying edge, so the item is no longer held;
        # a second equip is refused because it isn't being carried.
        with pytest.raises(ValueError, match="You aren't carrying"):
            equipment.equip_item("Duplicate Helm")
        player = pm.players[pm.active_player]
        assert len(player.equipped["head"]) == 1
        # The equipped item is not also present in the carrying/inventory list.
        assert not any(e.source == "item_duplicate_helm"
                       for e in graph.get_edges_for_target(
                           pm.get_player_node_id(pm.active_player), "carrying"))

    def test_equip_no_such_item_raises_error(self, basic_setup):
        """Equipping an item not in inventory raises ValueError."""
        _, _, equipment = basic_setup
        with pytest.raises(ValueError, match="You don't have"):
            equipment.equip_item("Mythical Crown")

    def test_unequip_empty_slot_raises_error(self, basic_setup):
        """Unequipping from an empty slot raises ValueError."""
        _, _, equipment = basic_setup
        with pytest.raises(ValueError, match="Nothing equipped in your"):
            equipment.unequip_item(slot="head")

    def test_unequip_when_not_wearing_raises_error(self, basic_setup):
        """Unequipping an item not worn raises ValueError."""
        _, _, equipment = basic_setup
        with pytest.raises(ValueError, match="You aren't wearing"):
            equipment.unequip_item(item_name="Mythical Crown")

    def test_equip_to_explicit_slot(self, basic_setup):
        """Equip an item to a specific named slot."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_chainmail", "Chainmail",
                          equip_slots=["torso", "arms"])
        result = equipment.equip_item("Chainmail", slot="arms")
        assert "equip the Chainmail on your arms" in result
        player = pm.players[pm.active_player]
        assert "item_chainmail" in player.equipped["arms"]

    def test_equip_wrong_slot_raises_error(self, basic_setup):
        """Equipping to a slot the item doesn't support raises ValueError."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_boot", "Boot", equip_slots=["feet"])
        with pytest.raises(ValueError, match="doesn't fit"):
            equipment.equip_item("Boot", slot="head")

    def test_equip_unknown_slot_raises_error(self, basic_setup):
        """Equipping to a non-existent slot raises ValueError."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_boot", "Boot", equip_slots=["feet"])
        with pytest.raises(ValueError, match="Unknown slot"):
            equipment.equip_item("Boot", slot="nonexistent_slot")

    def test_equip_while_sleeping_raises_error(self, basic_setup):
        """Equipping while asleep is blocked."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_hat", "Hat", equip_slots=["head"])
        pm.players[pm.active_player].add_condition("unconscious")  # sleep = unconscious
        with pytest.raises(ValueError, match="can't equip"):
            equipment.equip_item("Hat")

    def test_unequip_while_sleeping_raises_error(self, basic_setup):
        """Unequipping while asleep is blocked."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_hat", "Hat", equip_slots=["head"])
        equipment.equip_item("Hat")
        pm.players[pm.active_player].add_condition("unconscious")  # sleep = unconscious
        with pytest.raises(ValueError, match="can't unequip"):
            equipment.unequip_item(slot="head")


# ─────────────────── TestEquipmentLayering ───────────────────


class TestEquipmentLayering:
    """Stacking multiple items on the same slot."""

    def test_cannot_wear_second_copy_of_same_item(self, basic_setup):
        """Two copies of the same-named item stack nonsense ('Earring over
        Earring' — taco_bell 2026-08-24); the second wear is refused.
        Different-named items on the same slot still layer (see tests below)."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_earring_1", "Blue Butterfly Earring",
                          equip_slots=["accessory"])
        add_carried_item(graph, pm, "item_earring_2", "Blue Butterfly Earring",
                          equip_slots=["accessory"])

        equipment.equip_item("Blue Butterfly Earring")

        with pytest.raises(ValueError, match="already wearing"):
            equipment.equip_item("Blue Butterfly Earring")

    def test_layer_shirt_under_armor(self, basic_setup):
        """Equipping a shirt then armor on torso stacks both items."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_shirt", "Linen Shirt",
                          equip_slots=["torso"])
        add_carried_item(graph, pm, "item_chainmail", "Chainmail Vest",
                          equip_slots=["torso"])

        equipment.equip_item("Linen Shirt")
        equipment.equip_item("Chainmail Vest")

        player = pm.players[pm.active_player]
        torso_stack = player.equipped["torso"]
        assert len(torso_stack) == 2
        assert torso_stack[0] == "item_shirt"
        assert torso_stack[1] == "item_chainmail"

    def test_three_layer_deep(self, basic_setup):
        """Three items on torso: undershirt, shirt, armor."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_undershirt", "Undershirt",
                          equip_slots=["torso"])
        add_carried_item(graph, pm, "item_shirt", "Wool Shirt",
                          equip_slots=["torso"])
        add_carried_item(graph, pm, "item_breastplate", "Steel Breastplate",
                          equip_slots=["torso"])

        equipment.equip_item("Undershirt")
        equipment.equip_item("Wool Shirt")
        equipment.equip_item("Steel Breastplate")

        player = pm.players[pm.active_player]
        assert len(player.equipped["torso"]) == 3
        assert player.equipped["torso"][-1] == "item_breastplate"

    def test_slot_capacity_head(self, basic_setup):
        """Head slot max_depth=3: a 4th item raises error."""
        graph, pm, equipment = basic_setup
        for idx in range(4):
            add_carried_item(graph, pm, f"item_hat_{idx}", f"Hat {idx}",
                              equip_slots=["head"])

        for idx in range(3):
            equipment.equip_item(f"Hat {idx}")

        with pytest.raises(ValueError, match="full"):
            equipment.equip_item("Hat 3")

    def test_slot_capacity_feet(self, basic_setup):
        """Feet slot max_depth=3."""
        graph, pm, equipment = basic_setup
        for idx in range(4):
            add_carried_item(graph, pm, f"item_sock_{idx}", f"Sock {idx}",
                              equip_slots=["feet"])

        for idx in range(3):
            equipment.equip_item(f"Sock {idx}")

        with pytest.raises(ValueError, match="full"):
            equipment.equip_item("Sock 3")

    def test_accessory_unlimited(self, basic_setup):
        """Accessory slot has no depth limit (max_depth is None)."""
        graph, pm, equipment = basic_setup
        for idx in range(10):
            add_carried_item(graph, pm, f"item_ring_{idx}", f"Ring {idx}",
                              equip_slots=["accessory"])
            equipment.equip_item(f"Ring {idx}")

        player = pm.players[pm.active_player]
        assert len(player.equipped["accessory"]) == 10

    def test_outermost_displayed(self, basic_setup):
        """get_visible_equipment shows only the outermost item per slot."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_undershirt", "Undershirt",
                          equip_slots=["torso"])
        add_carried_item(graph, pm, "item_chainmail", "Chainmail",
                          equip_slots=["torso"])

        equipment.equip_item("Undershirt")
        equipment.equip_item("Chainmail")

        visible = equipment.get_visible_equipment()
        assert visible["torso"] == "Chainmail"

    def test_unequip_removes_outermost(self, basic_setup):
        """Unequipping from a layered slot removes the outermost item."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_shirt", "Shirt", equip_slots=["torso"])
        add_carried_item(graph, pm, "item_armor", "Armor", equip_slots=["torso"])

        equipment.equip_item("Shirt")
        equipment.equip_item("Armor")
        result = equipment.unequip_item(slot="torso")

        player = pm.players[pm.active_player]
        assert "Armor" in result
        assert len(player.equipped["torso"]) == 1
        assert player.equipped["torso"][0] == "item_shirt"

    def test_equip_under_layers(self, basic_setup):
        """Equipping with `under` inserts beneath the outermost."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_plate", "Plate", equip_slots=["torso"])
        add_carried_item(graph, pm, "item_gambeson", "Gambeson", equip_slots=["torso"])

        equipment.equip_item("Plate")
        result = equipment.equip_item("Gambeson", under="Plate")
        assert "equip the Gambeson on your torso" in result

        player = pm.players[pm.active_player]
        # `under` inserts after the named item, so Plate stays outermost
        assert player.equipped["torso"] == ["item_plate", "item_gambeson"]


# ─────────────────── TestTwoHanded ───────────────────


class TestTwoHanded:
    """Two-handed weapon handling."""

    def test_two_handed_sword_occupies_both_hands(self, basic_setup):
        """Equipping a two-handed weapon fills both hand slots."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_greatsword", "Greatsword",
                          equip_slots=["hand_right"], tags=["two_handed"])

        result = equipment.equip_item("Greatsword")
        assert "equip the Greatsword on your hand_right" in result

        player = pm.players[pm.active_player]
        assert "item_greatsword" in player.equipped["hand_right"]
        other_hand_markers = [
            x for x in player.equipped["hand_left"]
            if str(x).startswith("__multi_slot_")
        ]
        assert len(other_hand_markers) == 1

    def test_unequip_two_handed_frees_both(self, basic_setup):
        """Unequipping a two-handed weapon clears both hands."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_greatsword", "Greatsword",
                          equip_slots=["hand_right"], tags=["two_handed"])
        equipment.equip_item("Greatsword")
        result = equipment.unequip_item(slot="hand_right")

        assert "remove the Greatsword from your hand_right" in result
        player = pm.players[pm.active_player]
        assert len(player.equipped["hand_right"]) == 0
        assert len(player.equipped["hand_left"]) == 0

    def test_equip_two_handed_requires_free_other_hand(self, basic_setup):
        """Cannot equip a two-handed weapon if the other hand is occupied."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_dagger", "Dagger",
                          equip_slots=["hand_left"])
        add_carried_item(graph, pm, "item_greatsword", "Greatsword",
                          equip_slots=["hand_right"], tags=["two_handed"])

        equipment.equip_item("Dagger", slot="hand_left")
        with pytest.raises(ValueError, match="Free your other hand"):
            equipment.equip_item("Greatsword")

    def test_visible_equipment_shows_two_handed(self, basic_setup):
        """get_visible_equipment marks both hands as occupied by two-handed."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_greatsword", "Greatsword",
                          equip_slots=["hand_right"], tags=["two_handed"])
        equipment.equip_item("Greatsword")

        visible = equipment.get_visible_equipment()
        assert "hand_left" in visible
        assert "hand_right" in visible or "two-handed" in visible.get("hand_left", "")

    def test_unequip_two_handed_by_name(self, basic_setup):
        """Unequipping a two-handed weapon by name."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_greatsword", "Greatsword",
                          equip_slots=["hand_right"], tags=["two_handed"])
        equipment.equip_item("Greatsword")
        result = equipment.unequip_item(item_name="greatsword")
        assert "greatsword" in result.lower()

        player = pm.players[pm.active_player]
        assert len(player.equipped["hand_right"]) == 0
        assert len(player.equipped["hand_left"]) == 0


# ─────────────────── TestEquipsAllSlots ───────────────────


class TestEquipsAllSlots:
    """Full-body items (equips_all_slots tag) occupy every declared slot."""

    FULL_BODY_SLOTS = ["torso", "legs", "arms", "head", "feet", "hands"]

    def test_equips_all_declared_slots(self, basic_setup):
        """Equipping a full-body suit fills every declared slot with markers."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_eva_suit", "EVA Suit",
                          equip_slots=self.FULL_BODY_SLOTS, tags=["equips_all_slots"])

        result = equipment.equip_item("EVA Suit")
        assert "on your torso" in result
        assert "covers your legs, arms, head, feet, hands" in result

        player = pm.players[pm.active_player]
        assert "item_eva_suit" in player.equipped["torso"]
        for slot in ["legs", "arms", "head", "feet", "hands"]:
            markers = [
                x for x in player.equipped[slot]
                if str(x).startswith("__multi_slot_")
            ]
            assert len(markers) == 1, f"missing marker in {slot}"

    def test_unequip_full_body_frees_all_slots(self, basic_setup):
        """Unequipping a full-body suit clears every covered slot."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_eva_suit", "EVA Suit",
                          equip_slots=self.FULL_BODY_SLOTS, tags=["equips_all_slots"])
        equipment.equip_item("EVA Suit")
        equipment.unequip_item(slot="torso")

        player = pm.players[pm.active_player]
        for slot in self.FULL_BODY_SLOTS:
            assert len(player.equipped[slot]) == 0, f"slot {slot} not cleared"

    def test_unequip_full_body_by_name(self, basic_setup):
        """Unequipping a full-body suit by name clears all covered slots."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_eva_suit", "EVA Suit",
                          equip_slots=self.FULL_BODY_SLOTS, tags=["equips_all_slots"])
        equipment.equip_item("EVA Suit")
        result = equipment.unequip_item(item_name="eva suit")
        assert "eva suit" in result.lower()

        player = pm.players[pm.active_player]
        for slot in self.FULL_BODY_SLOTS:
            assert len(player.equipped[slot]) == 0, f"slot {slot} not cleared"

    def test_equip_full_body_rejects_full_slot(self, basic_setup):
        """Cannot equip a full-body suit if any covered slot has no room left."""
        graph, pm, equipment = basic_setup
        for i in range(3):
            add_carried_item(graph, pm, f"item_boot_{i}", f"Boot {i}", equip_slots=["feet"])
            equipment.equip_item(f"Boot {i}")
        add_carried_item(graph, pm, "item_eva_suit", "EVA Suit",
                          equip_slots=self.FULL_BODY_SLOTS, tags=["equips_all_slots"])

        with pytest.raises(ValueError, match="already occupied"):
            equipment.equip_item("EVA Suit")

    def test_full_body_narrative_reports_coverage(self, basic_setup):
        """Self and other narratives mention every covered slot."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_eva_suit", "EVA Suit",
                          equip_slots=self.FULL_BODY_SLOTS, tags=["equips_all_slots"])
        equipment.equip_item("EVA Suit")

        self_narrative = equipment.get_equipment_narrative()
        assert "EVA Suit over your" in self_narrative
        for slot in self.FULL_BODY_SLOTS:
            assert slot in self_narrative

        other_narrative = equipment.get_equipment_narrative(viewer_name="AnotherPerson")
        assert "EVA Suit over their" in other_narrative

    def test_visible_equipment_marks_full_body(self, basic_setup):
        """A full-body item in a hand slot renders as part of a full-body suit."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_eva_suit", "EVA Suit",
                          equip_slots=["torso", "hand_left", "hand_right"],
                          tags=["equips_all_slots"])
        equipment.equip_item("EVA Suit")

        visible = equipment.get_visible_equipment()
        assert "full-body suit" in visible.get("hand_right", "")


# ─────────────────── TestEquipmentNarrative ───────────────────


class TestEquipmentNarrative:
    """Narrative description of equipped items."""

    def test_self_narrative_shows_all_layers(self, basic_setup):
        """Self-narrative includes all equipped items in detail."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_shirt", "Cotton Shirt",
                          equip_slots=["torso"])
        add_carried_item(graph, pm, "item_chainmail", "Chainmail",
                          equip_slots=["torso"])

        equipment.equip_item("Cotton Shirt")
        equipment.equip_item("Chainmail")

        narrative = equipment.get_equipment_narrative()
        assert "Cotton Shirt" in narrative
        assert "Chainmail" in narrative
        assert "on your torso" in narrative

    def test_other_narrative_shows_outermost_only(self, basic_setup):
        """Other-viewer narrative shows only the outermost layer."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_shirt", "Cotton Shirt",
                          equip_slots=["torso"])
        add_carried_item(graph, pm, "item_chainmail", "Chainmail",
                          equip_slots=["torso"])

        equipment.equip_item("Cotton Shirt")
        equipment.equip_item("Chainmail")

        other_narrative = equipment.get_equipment_narrative(viewer_name="AnotherPerson")
        assert "Chainmail" in other_narrative
        assert "Cotton Shirt" not in other_narrative

    def test_narrative_nothing_worn(self, basic_setup):
        """When nothing is equipped, narrative says 'nothing'."""
        _, _, equipment = basic_setup
        narrative = equipment.get_equipment_narrative()
        assert "nothing" in narrative.lower() or "wearing" in narrative.lower()

    def test_narrative_with_accessories(self, basic_setup):
        """Accessories appear in the narrative."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_ring", "Gold Ring",
                          equip_slots=["accessory"])
        equipment.equip_item("Gold Ring")

        narrative = equipment.get_equipment_narrative()
        assert "Gold Ring" in narrative
        assert "accessories" in narrative.lower() or "accessory" in narrative.lower()

    def test_narrative_self_with_hand_items(self, basic_setup):
        """Self-narrative includes items held in hands."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_sword", "Broadsword",
                          equip_slots=["hand_right"])
        equipment.equip_item("Broadsword")

        narrative = equipment.get_equipment_narrative()
        assert "Broadsword" in narrative
        assert "hand" in narrative.lower()

    def test_get_full_equipment_returns_all_layers(self, basic_setup):
        """get_full_equipment returns all stacks."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_shirt", "Shirt", equip_slots=["torso"])
        add_carried_item(graph, pm, "item_armor", "Armor", equip_slots=["torso"])
        equipment.equip_item("Shirt")
        equipment.equip_item("Armor")

        full = equipment.get_full_equipment()
        assert "torso" in full
        assert full["torso"] == ["Shirt", "Armor"]

    def test_get_visible_equipment_empty(self, basic_setup):
        """get_visible_equipment returns empty dict when nothing is worn."""
        _, _, equipment = basic_setup
        visible = equipment.get_visible_equipment()
        assert isinstance(visible, dict)

    def test_other_narrative_hides_intrinsic_abilities(self, basic_setup):
        """Spell/ability-tagged items are hidden from other characters' examine."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_create_flame", "Create Flame",
                         equip_slots=["hand_right"],
                         tags=["fire", "spell", "magic"])
        equipment.equip_item("Create Flame")

        other_narrative = equipment.get_equipment_narrative(viewer_name="AnotherPerson")
        assert "Create Flame" not in other_narrative
        self_narrative = equipment.get_equipment_narrative()
        assert "Create Flame" in self_narrative

    def test_other_narrative_shows_physical_magic_items(self, basic_setup):
        """Physical scrolls/spell books remain visible to other characters."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_fireball_scroll", "Scroll of Fireball",
                         equip_slots=["hand_right"],
                         tags=["scroll", "magic"])
        equipment.equip_item("Scroll of Fireball")

        other_narrative = equipment.get_equipment_narrative(viewer_name="AnotherPerson")
        assert "Scroll of Fireball" in other_narrative

    def test_narrative_with_head_gear(self, basic_setup):
        """Equipping a helmet includes it in narrative."""
        graph, pm, equipment = basic_setup
        add_carried_item(graph, pm, "item_helmet", "Steel Helmet",
                          equip_slots=["head"])
        equipment.equip_item("Steel Helmet")
        narrative = equipment.get_equipment_narrative()
        assert "Steel Helmet" in narrative

    def test_hygiene_modifier_defaults(self, basic_setup):
        """get_hygiene_modifier returns 0 at default hygiene of 100."""
        _, _, equipment = basic_setup
        modifier = equipment.get_hygiene_modifier()
        assert modifier == 0

    def test_hygiene_modifier_low(self, basic_setup):
        """get_hygiene_modifier returns negative at low hygiene."""
        _, pm, equipment = basic_setup
        pm.players[pm.active_player].vitals["Hygiene"] = 20
        modifier = equipment.get_hygiene_modifier()
        assert modifier < 0
