"""task-604 / task-607: the two defence axes and the selectable DR mode.

task-604 split the single ``defense`` integer into **damage reduction**
(``defense``/``damage_reduction``) and a signed **evasion** applied on the
attack side. task-607 makes the reduction a damage *expression* (``20`` or
``d8``) whose interpretation is an engine-config mode: ``flat`` (default,
historical), ``dice`` (strip damage dice before the roll), and ``percentage``
(scale-invariant).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import Node, Edge, EDGE_IN, EDGE_EQUIPPED, EDGE_CARRYING, WorldGraph
from player import Player
from engine.combat import CombatSystem
from engine.ghost import GhostSystem
from engine.logging_events import GameLogger
from engine.skills import SkillSystem
from engine.player_manager import PlayerManager
from engine.npc_behaviors import NPCBehaviorSystem
from engine.equipment_bonuses import aggregate_bonuses, parse_damage
from engine.runtime_config import config
from unittest.mock import MagicMock


@pytest.fixture
def dr_mode():
    """Set the engine-config DR mode for a test and restore it afterwards."""
    original = config.get("combat.damage_reduction_mode")

    def _set(mode):
        config._values["combat.damage_reduction_mode"] = mode

    yield _set
    config._values["combat.damage_reduction_mode"] = original


class Harness:
    def __init__(self):
        self.graph = WorldGraph()
        self.player_manager = PlayerManager(self.graph)
        self.skills = SkillSystem(self.player_manager, GameLogger())
        self.skills.get_player = self.player_manager.get_player
        self.skills.get_player_node_id = self.player_manager.get_player_node_id
        self.skills.add_log_entry = lambda *a, **k: None
        self.skills.record_turn_event = lambda *a, **k: None
        self.skills.is_slasher = lambda name: False
        self.npc = NPCBehaviorSystem(self.graph, self.player_manager, None, None)
        if not hasattr(self.npc, "process_npcs_on_combat"):
            self.npc.process_npcs_on_combat = lambda ctx: None
        self.combat = CombatSystem(self.graph, self.skills, MagicMock(spec=GhostSystem), self.npc)

    def add_player(self, name, stats=None):
        p = Player(name)
        if stats:
            p.stats.update(stats)
        self.player_manager.add_player(p)
        return p

    def equip(self, player_name, props, name="Test Armour"):
        node = Node(
            id=f"item_{name.lower().replace(' ', '_')}",
            type="item",
            name=name,
            properties={
                "name": name,
                "tags": ["armor", "clothing"],
                "actions": ["examine", "equip", "unequip"],
                **props,
            },
        )
        self.graph.add_node(node)
        pid = self.player_manager.get_player_node_id(player_name)
        self.graph.add_edge(Edge(source=node.id, target=pid, type=EDGE_EQUIPPED))
        return node


# ── parse_damage: the shared grammar ────────────────────────────────────


class TestParseDamage:
    def test_bare_d8_is_one_die(self):
        assert parse_damage("d8") == (1, 8, 0)
        assert parse_damage("D8") == (1, 8, 0)

    def test_counted_dice_and_flat(self):
        assert parse_damage("2d6+3") == (2, 6, 3)
        assert parse_damage("2d6-1") == (2, 6, -1)

    def test_plain_number_is_flat(self):
        assert parse_damage(20) == (0, 0, 20)
        assert parse_damage("20") == (0, 0, 20)


# ── aggregate_bonuses: the two axes ─────────────────────────────────────


class TestAggregateAxes:
    def test_defense_alias_reads_damage_reduction(self):
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 6})
        b = aggregate_bonuses(h.player_manager.players["T"], h.graph)
        assert b["damage_reduction"] == 6
        assert b["defense"] == 6  # legacy alias
        assert b["evasion"] == 0

    def test_damage_reduction_name_read(self):
        h = Harness()
        h.add_player("T")
        h.equip("T", {"damage_reduction": 9})
        b = aggregate_bonuses(h.player_manager.players["T"], h.graph)
        assert b["damage_reduction"] == 9

    def test_evasion_is_signed_and_summed(self):
        h = Harness()
        h.add_player("T")
        h.equip("T", {"evasion": -2}, name="Plate")
        h.equip("T", {"evasion": 1}, name="Cloak")
        b = aggregate_bonuses(h.player_manager.players["T"], h.graph)
        assert b["evasion"] == -1

    def test_dice_defense_is_collected_not_summed(self):
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": "d8"})
        b = aggregate_bonuses(h.player_manager.players["T"], h.graph)
        assert b["damage_reduction"] == 0
        assert b["damage_reduction_dice"] == (1, 8)


# ── flat mode (default) ─────────────────────────────────────────────────


class TestFlatMode:
    def test_subtracts_flat_value(self, dr_mode):
        dr_mode("flat")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 4})
        target = h.player_manager.players["T"]
        damage, amount, mode, label = h.combat._apply_damage_reduction(10, target)
        assert damage == 6 and amount == 4 and mode == "flat"
        assert "flat" in label

    def test_floor_is_one(self, dr_mode):
        dr_mode("flat")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 50})
        target = h.player_manager.players["T"]
        damage, _amount, _mode, _label = h.combat._apply_damage_reduction(3, target)
        assert damage == 1

    def test_dice_defense_rolls_per_hit(self, dr_mode):
        dr_mode("flat")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": "d8"})
        target = h.player_manager.players["T"]
        h.skills.roll_dice = lambda n, sides, bonus=0: 7
        damage, amount, mode, _label = h.combat._apply_damage_reduction(20, target)
        assert amount == 7 and damage == 13


# ── dice mode ───────────────────────────────────────────────────────────


class TestDiceMode:
    def test_strips_damage_dice(self, dr_mode):
        dr_mode("dice")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 2})
        target = h.player_manager.players["T"]
        assert h.combat._adjust_damage_dice(5, target) == (3, 2)

    def test_leaves_at_least_one_die(self, dr_mode):
        dr_mode("dice")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 99})
        target = h.player_manager.players["T"]
        assert h.combat._adjust_damage_dice(2, target) == (1, 1)

    def test_dice_mode_does_not_also_subtract_points(self, dr_mode):
        dr_mode("dice")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 2})
        target = h.player_manager.players["T"]
        # pre-roll stripping handles it; the post-roll helper is a no-op.
        assert h.combat._apply_damage_reduction(10, target) == (10, 0, "dice", "")

    def test_flat_mode_is_noop_for_dice_helper(self, dr_mode):
        dr_mode("flat")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 2})
        target = h.player_manager.players["T"]
        assert h.combat._adjust_damage_dice(5, target) == (5, 0)

    def test_dice_mode_reports_stripped_dice_in_the_combat_log(self, dr_mode):
        dr_mode("dice")
        h = Harness()
        h.add_player("Attacker", {"STR": 14, "DEX": 10})
        h.add_player("T", {"STR": 10, "DEX": 10})
        pid = h.player_manager.get_player_node_id("Attacker")
        weapon = Node(id="item_sword", type="item", name="Sword", properties={
            "name": "Sword", "damage": "3d6", "damage_type": "slashing",
            "tags": ["weapon"], "actions": ["examine", "take"],
            "current_state": "normal",
        })
        h.graph.add_node(weapon)
        h.graph.add_edge(Edge(source=weapon.id, target=pid, type=EDGE_CARRYING))
        h.equip("T", {"damage_reduction": 2})  # strips 2 dice

        logs = []
        h.skills.add_log_entry = lambda msg, *a, **k: logs.append(msg)
        calls = {"n": 0}

        def fake(n, sides, bonus=0):
            if sides == 20:
                calls["n"] += 1
                return (20 + bonus) if calls["n"] == 1 else 1
            return 1

        h.skills.roll_dice = fake
        h.combat.player_attack("Attacker", "T")

        joined = "\n".join(logs)
        assert "2 dice stripped" in joined, joined
        assert "dice armor" in joined, joined


class TestWearScanReadsNewName:
    def test_armor_authored_with_damage_reduction_wears(self):
        from virtual_world_engine import VirtualWorld
        from player import Player
        world = VirtualWorld()
        world.add_player(Player("Wearer"))
        p = world.player_manager.get_player("Wearer")
        node = Node(id="item_coat", type="item", name="Riveted Coat", properties={
            "name": "Riveted Coat", "tags": ["armor", "clothing"],
            "damage_reduction": 4, "uses": 2, "max_uses": 2,
            "weight": 4, "base_weight": 4, "equip_slots": ["torso"],
            "current_state": "normal", "actions": ["examine", "equip"],
        })
        world.graph.add_node(node)
        world.graph.add_edge(Edge(source=node.id,
                                  target=world._player_node_id("Wearer"),
                                  type=EDGE_EQUIPPED, properties={"slot": "torso"}))
        world.player_manager.get_player("Wearer").equipped.setdefault("torso", []).append(node.id)

        world.equipment.decrement_armor_uses_on_hit(p)

        assert node.properties["uses"] == 1, "the new DR name must not be skipped"


# ── percentage mode ─────────────────────────────────────────────────────


class TestPercentageMode:
    def test_reduces_by_percent(self, dr_mode):
        dr_mode("percentage")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 40})
        target = h.player_manager.players["T"]
        damage, amount, mode, label = h.combat._apply_damage_reduction(10, target)
        assert damage == 6 and amount == 4 and mode == "percentage"
        assert "%" in label

    def test_scale_invariant_across_hp_scales(self, dr_mode):
        """40% blunts a 4 HP spider, a 100 HP goblin and a 675 HP dragon alike."""
        dr_mode("percentage")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 40})
        target = h.player_manager.players["T"]
        for incoming, expected in ((4, 2), (10, 6), (100, 60), (675, 405)):
            damage, _a, _m, _l = h.combat._apply_damage_reduction(incoming, target)
            assert damage == expected, (incoming, damage)

    def test_caps_at_one(self, dr_mode):
        dr_mode("percentage")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 100})
        target = h.player_manager.players["T"]
        damage, _a, _m, _l = h.combat._apply_damage_reduction(10, target)
        assert damage == 1


# ── evasion: the second axis ────────────────────────────────────────────


class TestEvasionOnAttack:
    def _fixed_rolls(self, h, defender_dex):
        def fake(n, sides, bonus=0):
            if sides == 20:
                return 10 + bonus
            return 1
        h.skills.roll_dice = fake

    def test_positive_evasion_turns_hit_into_miss(self, dr_mode):
        dr_mode("flat")
        h = Harness()
        h.add_player("Attacker", {"STR": 14, "DEX": 10})
        h.add_player("T", {"STR": 10, "DEX": 10})
        # Both roll 10 raw: attack 12 vs defence 10 -> hit at evasion 0.
        h.skills.roll_dice = lambda n, sides, bonus=0: (10 + bonus) if sides == 20 else 1
        assert "miss" not in h.combat.player_attack("Attacker", "T").lower()

        h.equip("T", {"evasion": 3})
        h.skills.roll_dice = lambda n, sides, bonus=0: (10 + bonus) if sides == 20 else 1
        assert "miss" in h.combat.player_attack("Attacker", "T").lower()

    def test_negative_evasion_turns_miss_into_hit(self, dr_mode):
        dr_mode("flat")
        h = Harness()
        h.add_player("Attacker", {"STR": 14, "DEX": 10})
        h.add_player("T", {"STR": 10, "DEX": 18})  # DEX mod +4
        # attack 12 vs defence 14 -> miss at evasion 0.
        h.skills.roll_dice = lambda n, sides, bonus=0: (10 + bonus) if sides == 20 else 1
        assert "miss" in h.combat.player_attack("Attacker", "T").lower()

        h.equip("T", {"evasion": -4})  # heavy plate: easier to hit
        h.skills.roll_dice = lambda n, sides, bonus=0: (10 + bonus) if sides == 20 else 1
        assert "miss" not in h.combat.player_attack("Attacker", "T").lower()

    def test_omitted_evasion_is_zero(self, dr_mode):
        dr_mode("flat")
        h = Harness()
        h.add_player("T")
        h.equip("T", {"defense": 5})
        target = h.player_manager.players["T"]
        assert h.combat._get_target_evasion(target) == 0
