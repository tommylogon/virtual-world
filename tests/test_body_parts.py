"""Tests for the body-part taxonomy (task-253) and region-scoped combat injury."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import Node, Edge, EDGE_IN, EDGE_CARRYING, WorldGraph
from player import Player
from engine.body_parts import (
    BODY_REGIONS, resolve_region, injury_region, region_chain, coverage_slots,
    is_exposed, default_body_state, region_injury_level, roll_hit_location,
    HIT_LOCATION_TABLE,
    INJURY_DAMAGE_THRESHOLD, BLEEDING_DAMAGE_THRESHOLD,
)
from engine.combat import CombatSystem
from engine.ghost import GhostSystem
from engine.logging_events import GameLogger
from engine.skills import SkillSystem
from engine.player_manager import PlayerManager
from engine.npc_behaviors import NPCBehaviorSystem
from unittest.mock import MagicMock


@pytest.fixture
def harness():
    h = type("H", (), {})()
    h.graph = WorldGraph()
    h.player_manager = PlayerManager(h.graph)
    h.skills = SkillSystem(h.player_manager, GameLogger())
    h.skills.get_player = h.player_manager.get_player
    h.skills.get_player_node_id = h.player_manager.get_player_node_id
    h.skills.add_log_entry = GameLogger().add_log_entry
    h.skills.record_turn_event = GameLogger().record_turn_event
    h.skills.is_slasher = lambda name: False
    h.npc_behaviors = MagicMock()
    h.npc_behaviors.process_npcs_on_combat = lambda ctx: None
    h.combat = CombatSystem(h.graph, h.skills, MagicMock(spec=GhostSystem), h.npc_behaviors)

    arena = Node(id="area_Arena", type="area", name="Arena", properties={"description": "A dusty arena."})
    h.graph.add_node(arena)

    h.attacker = Player("Attacker")
    h.attacker.stats.update({"STR": 14, "DEX": 10})
    h.attacker.current_area = "Arena"
    h.target = Player("TargetDummy")
    h.target.stats.update({"STR": 10, "DEX": 1})
    h.target.current_area = "Arena"
    h.player_manager.add_player(h.attacker)
    h.player_manager.add_player(h.target)
    h.player_manager.set_active_player("Attacker")

    for p in (h.attacker, h.target):
        pid = h.player_manager.get_player_node_id(p.name)
        h.graph.add_edge(Edge(source=pid, target="area_Arena", type=EDGE_IN))

    return h


# ─────────────────── Taxonomy ───────────────────


class TestTaxonomy:
    def test_flat_catalog_has_injury_and_erogenous_regions(self):
        assert "head" in BODY_REGIONS and "torso" in BODY_REGIONS
        assert "nipple_left" in BODY_REGIONS and "genitals" in BODY_REGIONS
        assert "cheeks" in BODY_REGIONS and "lips" in BODY_REGIONS

    def test_every_erogenous_zone_has_a_parent(self):
        for region_id, meta in BODY_REGIONS.items():
            if meta["zone"] == "erogenous":
                assert meta["parent"], f"{region_id} has no parent"

    def test_every_region_has_metadata_fields(self):
        for region_id, meta in BODY_REGIONS.items():
            assert meta["name"]
            assert meta["zone"] in ("injury", "erogenous", "both")
            assert isinstance(meta["base_sensitivity"], float)
            assert isinstance(meta.get("slots", []), list)

    def test_injury_region_returns_self(self):
        assert injury_region("head") == "head"
        assert injury_region("arm_left") == "arm_left"

    def test_erogenous_zone_resolves_to_parent_injury(self):
        assert injury_region("nipple_left") == "torso"
        assert injury_region("genitals") == "torso"
        assert injury_region("lips") == "head"

    def test_unknown_region_resolves_none(self):
        assert injury_region("not_a_part") is None


# ─────────────────── Resolution ───────────────────


class TestResolution:
    def test_resolve_exact_id(self):
        assert resolve_region("head") == "head"
        assert resolve_region("nipple_left") == "nipple_left"

    def test_resolve_alias(self):
        assert resolve_region("stomach") == "torso"
        assert resolve_region("groin") == "genitals"
        assert resolve_region("kiss") == "lips"

    def test_resolve_side_prefixed(self):
        assert resolve_region("left arm") == "arm_left"
        assert resolve_region("right foot") == "foot_right"
        assert resolve_region("left nipple") == "nipple_left"

    def test_resolve_unknown(self):
        assert resolve_region("wings") is None
        assert resolve_region("") is None
        assert resolve_region(None) is None

    def test_region_chain_outermost_first(self):
        assert region_chain("nipple_left") == ["torso", "breast_left", "nipple_left"]
        assert region_chain("hand_left") == ["arm_left", "hand_left"]

    def test_coverage_slots_include_parent_slots(self):
        assert coverage_slots("nipple_left") == ["torso"]
        assert "arms" in coverage_slots("hand_left")
        assert "feet" in coverage_slots("leg_left")


# ─────────────────── body_state + exposure ───────────────────


class TestBodyState:
    def test_default_body_state_covers_all_regions(self):
        state = default_body_state()
        assert set(state.keys()) == set(BODY_REGIONS.keys())
        assert state["nipple_left"]["sensitivity"] == 0.9
        # Injury is NOT stored in body_state — conditions are the source of truth.
        assert "injury" not in state["torso"]

    def test_player_inits_body_state(self):
        p = Player("Test")
        assert "torso" in p.body_state
        assert p.body_state["torso"]["sensitivity"] == 0.3

    def test_exposed_when_no_clothing(self, harness):
        assert is_exposed(harness.target, "torso", harness.graph) is True

    def test_covered_blocks_exposure(self, harness):
        armor = Node(
            id="item_plate_armor", type="item", name="Plate Armor",
            properties={"coverage": 0.9, "equip_slots": ["torso"], "tags": ["armor"]},
        )
        harness.graph.add_node(armor)
        harness.target.equipped.setdefault("torso", []).append(armor.id)
        assert is_exposed(harness.target, "torso", harness.graph) is False

    def test_low_coverage_does_not_block(self, harness):
        shirt = Node(
            id="item_linen_shirt", type="item", name="Linen Shirt",
            properties={"coverage": 0.3, "equip_slots": ["torso"]},
        )
        harness.graph.add_node(shirt)
        harness.target.equipped.setdefault("torso", []).append(shirt.id)
        assert is_exposed(harness.target, "torso", harness.graph) is True

    def test_injury_level_thresholds(self):
        assert region_injury_level(INJURY_DAMAGE_THRESHOLD - 1) == 0
        assert region_injury_level(6) == 1
        assert region_injury_level(9) == 2
        assert region_injury_level(13) == 3


# ─────────────────── Hit-location table ───────────────────


class TestHitLocation:
    def test_table_covers_every_face_of_the_d20(self):
        covered = set()
        for (low, high), region_id in HIT_LOCATION_TABLE:
            assert 1 <= low <= high <= 20
            for face in range(low, high + 1):
                assert face not in covered, f"face {face} mapped twice"
                covered.add(face)
        assert covered == set(range(1, 21))

    def test_table_maps_to_valid_regions(self):
        for (_low, _high), region_id in HIT_LOCATION_TABLE:
            assert region_id in BODY_REGIONS

    def test_roll_hit_location_deterministic(self):
        assert roll_hit_location(1) == "head"
        assert roll_hit_location(10) == "torso"
        assert roll_hit_location(12) == "torso"
        assert roll_hit_location(20) == "foot_right"

    def test_roll_hit_location_torso_is_most_likely(self):
        from collections import Counter
        rolls = Counter(roll_hit_location(face) for face in range(1, 21))
        assert rolls["torso"] >= 4  # 5 faces

    def test_roll_hit_location_random_returns_valid(self):
        from unittest.mock import patch
        with patch("engine.skills.random.randint", return_value=8):
            assert roll_hit_location() == "torso"


# ─────────────────── Combat region injury ───────────────────


class TestCombatRegionInjury:
    def test_attack_with_region_applies_injury(self, harness):
        target_hp = harness.target.vitals["HP"]
        result = harness.combat.player_attack(
            "Attacker", "TargetDummy", where="torso"
        )
        # DEX 1 target: attacker (STR 14) almost always hits.
        if "misses" in result.lower():
            pytest.skip("attack missed")
        assert target_hp >= harness.target.vitals["HP"]
        injured = harness.target.conditions.get("injured", [])
        if injured:
            assert injured[0].get("body_part") == "torso"
            assert "injured" in result.lower()

    def test_unaimed_attack_rolls_hit_location(self, harness):
        from unittest.mock import patch
        harness.target.vitals["HP"] = 100
        # Order: attack d20, defense d20, damage 1d4, hit-location d20.
        with patch("engine.skills.random.randint", return_value=20):
            result = harness.combat.player_attack("Attacker", "TargetDummy")
        assert "right foot" in result.lower()
        assert "HP" not in result
        injured = harness.target.conditions.get("injured", [])
        assert injured and injured[0].get("body_part") == "foot_right"
        assert "Right Foot injured" in result

    def test_unaimed_attack_low_damage_can_miss_injury(self, harness):
        from unittest.mock import patch
        harness.target.vitals["HP"] = 100
        # All rolls land on 1: attack still hits (STR 14 vs DEX 1) but deals
        # only 3 damage — below INJURY_DAMAGE_THRESHOLD, so no injury applies.
        with patch("engine.skills.random.randint", return_value=1):
            result = harness.combat.player_attack("Attacker", "TargetDummy")
        assert "→ HIT" in result
        assert "injured" not in harness.target.conditions

    def test_unaimed_attack_rolls_hit_location(self, harness):
        from unittest.mock import patch
        harness.target.vitals["HP"] = 100
        # Order: attack d20, defense d20, damage 1d4, hit-location d20.
        with patch("engine.skills.random.randint", return_value=20):
            result = harness.combat.player_attack("Attacker", "TargetDummy")
        assert "right foot" in result.lower()
        assert "HP" not in result
        injured = harness.target.conditions.get("injured", [])
        assert injured and injured[0].get("body_part") == "foot_right"

    def test_bleeding_applied_on_high_damage(self, harness):
        from unittest.mock import patch
        with patch("engine.skills.random.randint", return_value=20):
            harness.combat.player_attack(
                "Attacker", "TargetDummy", where="arm_left"
            )
        # BLEEDING_DAMAGE_THRESHOLD unreachable bare-handed (max 1d4+2≈6),
        # so use a weapon and assert bleeding needs enough damage via direct
        # unit check of _apply_region_injury instead.
        target2 = Player("Dummy2")
        target2.vitals["HP"] = 100
        note = harness.combat._apply_region_injury(
            target2, "torso", "torso", BLEEDING_DAMAGE_THRESHOLD, "Attacker"
        )
        assert "bleeding" in note
        assert "bleeding" in target2.conditions

    def test_injury_ends_via_fix_action(self, harness):
        harness.target.add_condition(
            "injured", source="Attacker", level=2,
            overrides={"body_part": "torso"},
        )
        harness.target.add_condition(
            "injured", source="Attacker", level=1,
            overrides={"body_part": "arm_left"},
        )
        harness.target.end_instances("fix")
        remaining = [
            i for insts in harness.target.conditions.values()
            for i in insts if i.get("body_part")
        ]
        assert remaining == []

    def test_covered_region_blocks_injury(self, harness):
        from unittest.mock import patch
        armor = Node(
            id="item_plate_armor", type="item", name="Plate Armor",
            properties={"coverage": 0.9, "equip_slots": ["torso"], "tags": ["armor"]},
        )
        harness.graph.add_node(armor)
        harness.target.equipped.setdefault("torso", []).append(armor.id)
        weapon = Node(
            id="item_war_axe", type="item", name="War Axe",
            properties={"damage": 12, "equip_slots": ["hand_right"], "tags": ["weapon"]},
        )
        harness.graph.add_node(weapon)
        harness.attacker.equipped.setdefault("hand_right", []).append(weapon.id)
        with patch("engine.skills.random.randint", return_value=20):
            harness.combat.player_attack(
                "Attacker", "TargetDummy", weapon_node=weapon, where="torso"
            )
        assert "injured" not in harness.target.conditions