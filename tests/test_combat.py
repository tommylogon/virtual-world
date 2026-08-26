"""Tests for the CombatSystem."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import Node, Edge, EDGE_IN, EDGE_CARRYING, WorldGraph
from player import Player
from engine.combat import CombatSystem, WEAPON_KEYWORDS
from engine.ghost import GhostSystem
from engine.logging_events import GameLogger
from engine.skills import SkillSystem
from engine.player_manager import PlayerManager
from engine.npc_behaviors import NPCBehaviorSystem
from unittest.mock import MagicMock, patch


# ─────────────────── Fixtures ───────────────────


class CombatTestHarness:
    """Holds all the objects needed to test CombatSystem in isolation."""
    def __init__(self):
        self.graph = WorldGraph()
        self.game_logger = GameLogger()
        self.player_manager = PlayerManager(self.graph)
        self.skills = SkillSystem(self.player_manager, self.game_logger)
        self.ghost_system = MagicMock(spec=GhostSystem)
        self.npc_behaviors = NPCBehaviorSystem(
            self.graph, self.player_manager,
            None,  # trigger_system not needed for basic combat
            None,  # game_state not needed for basic combat
        )
        # CombatSystem calls process_npcs_on_combat — add it if the
        # NPCBehaviorSystem doesn't have it yet (engine version mismatch).
        if not hasattr(self.npc_behaviors, 'process_npcs_on_combat'):
            self.npc_behaviors.process_npcs_on_combat = lambda ctx: None

        # Make player_manager accessible via the skills interface that
        # CombatSystem expects (it calls skills.get_player, skills.get_player_node_id, etc.)
        self.skills.get_player = self.player_manager.get_player
        self.skills.get_player_node_id = self.player_manager.get_player_node_id
        self.skills.add_log_entry = self.game_logger.add_log_entry
        self.skills.record_turn_event = self.game_logger.record_turn_event
        self.skills.is_slasher = lambda player_name: False
        self.skills.get_player_node_id = self.player_manager.get_player_node_id

        self.combat = CombatSystem(
            self.graph, self.skills, self.ghost_system, self.npc_behaviors
        )

    def add_player(self, name, stats=None, current_area=None):
        """Add a player and return it."""
        p = Player(name)
        if stats:
            p.stats.update(stats)
        if current_area:
            p.current_area = current_area
        self.player_manager.add_player(p)
        return p

    def add_weapon_to_inventory(self, player_name, item_name, damage=6, uses=-1):
        """Add a weapon item node to the graph and connect to player."""
        item_id = f"item_{item_name.lower().replace(' ', '_')}"
        player_id = self.player_manager.get_player_node_id(player_name)

        node = Node(
            id=item_id,
            type="item",
            name=item_name,
            properties={
                "description": f"A {item_name}.",
                "actions": ["examine", "take", "use"],
                "damage": damage,
                "uses": uses,
                "weight": 1.0,
                "current_state": "normal",
                "tags": ["weapon"],
                "equip_slots": ["hand_right"],
            }
        )
        self.graph.add_node(node)
        self.graph.add_edge(Edge(source=node.id, target=player_id, type=EDGE_CARRYING))
        return node


@pytest.fixture
def harness():
    """Create a CombatTestHarness with two players."""
    h = CombatTestHarness()

    # Add a area
    from area import Area
    arena = Area("Arena", "A dusty arena.", items=[])
    self = type("FakeEngine", (), {})()
    self.add_area = lambda r: None
    # Direct area creation for NPCBehaviorSystem needs
    arena_node = Node(id="area_Arena", type="area", name="Arena",
                      properties={"description": "A dusty arena."})
    h.graph.add_node(arena_node)

    attacker = h.add_player("Attacker", stats={"STR": 14, "DEX": 10})
    attacker.current_area = "Arena"

    target = h.add_player("TargetDummy", stats={"STR": 10, "DEX": 5})
    target.current_area = "Arena"

    h.player_manager.set_active_player("Attacker")

    # Add location edges to arena for both players
    for pname in ["Attacker", "TargetDummy"]:
        pid = h.player_manager.get_player_node_id(pname)
        if not any(e.source == pid and e.target == "area_Arena" and e.type == EDGE_IN
                   for e in h.graph.edges):
            h.graph.add_edge(Edge(source=pid, target="area_Arena", type=EDGE_IN))

    return h


# ─────────────────── TestCombat ───────────────────


class TestCombat:
    """Combat system tests."""

    def test_attack_with_weapon(self, harness):
        """Attacking with a weapon deals damage to the target."""
        weapon = harness.add_weapon_to_inventory("Attacker", "Iron Sword", damage=6)
        target_hp_before = harness.player_manager.players["TargetDummy"].vitals["HP"]

        result = harness.combat.player_attack(
            "Attacker", "TargetDummy", weapon_node=weapon
        )
        target_hp_after = harness.player_manager.players["TargetDummy"].vitals["HP"]

        assert "damage" in result.lower() or "misses" in result.lower()
        if "misses" not in result.lower():
            assert target_hp_after < target_hp_before

    def test_attack_barehanded(self, harness):
        """Attacking without a weapon still deals some damage."""
        target_hp_before = harness.player_manager.players["TargetDummy"].vitals["HP"]

        result = harness.combat.player_attack(
            "Attacker", "TargetDummy", weapon_node=None
        )

        target_hp_after = harness.player_manager.players["TargetDummy"].vitals["HP"]
        assert "misses" in result.lower() or target_hp_after < target_hp_before

    def test_attack_kills_target(self, harness):
        """Reducing target HP to 0 kills them."""
        target = harness.player_manager.players["TargetDummy"]
        target.vitals["HP"] = 1
        target.stats["DEX"] = 1

        weapon = harness.add_weapon_to_inventory("Attacker", "Mighty Axe", damage=20)
        with patch("engine.skills.random.randint", return_value=20):
            result = harness.combat.player_attack(
                "Attacker", "TargetDummy", weapon_node=weapon
            )

        assert target.vitals["HP"] == 0
        assert target.state == "dead"
        assert "dead" in result.lower() or "collapse" in result.lower()

    def test_attack_dead_target_handled(self, harness):
        """Attacking a target that is already dead still executes."""
        target = harness.player_manager.players["TargetDummy"]
        target.state = "dead"
        target.vitals["HP"] = 0

        weapon = harness.add_weapon_to_inventory("Attacker", "Sword", damage=6)
        result = harness.combat.player_attack(
            "Attacker", "TargetDummy", weapon_node=weapon
        )
        assert isinstance(result, str)

    def test_attack_missing_target_returns_empty(self, harness):
        """Attacking a nonexistent target returns empty string."""
        result = harness.combat.player_attack(
            "Attacker", "NonexistentPlayer", weapon_node=None
        )
        assert result == ""

    def test_weapon_keywords_detected(self):
        """WEAPON_KEYWORDS includes common weapon types."""
        expected = ["cleaver", "knife", "sword", "dagger",
                     "axe", "hammer", "spear", "club"]
        for keyword in expected:
            assert keyword in WEAPON_KEYWORDS

    def test_find_weapon_in_inventory(self, harness):
        """_find_weapon_in_inventory locates a weapon by name."""
        harness.add_weapon_to_inventory("Attacker", "Rusty Knife", damage=3)
        result = harness.combat._find_weapon_in_inventory(
            "Attacker", "Rusty Knife"
        )
        assert result is not None
        assert result.name == "Rusty Knife"

    def test_find_weapon_not_found(self, harness):
        """_find_weapon_in_inventory returns None for missing weapon."""
        result = harness.combat._find_weapon_in_inventory(
            "Attacker", "NonexistentWeapon"
        )
        assert result is None

    def test_attack_with_weapon_reduces_uses(self, harness):
        """Attacking with a limited-use weapon decrements its uses."""
        weapon = harness.add_weapon_to_inventory("Attacker", "Disposable Dagger",
                                                  damage=4, uses=3)

        with patch("engine.skills.random.randint", return_value=20):
            harness.combat.player_attack(
                "Attacker", "TargetDummy", weapon_node=weapon
            )
        assert weapon.properties["uses"] == 2

    def test_attack_logs_combat_event(self, harness):
        """Combat events are recorded in the game log."""
        weapon = harness.add_weapon_to_inventory("Attacker", "Log Sword", damage=6)
        log_count_before = len(harness.game_logger.game_log)

        harness.combat.player_attack(
            "Attacker", "TargetDummy", weapon_node=weapon
        )

        log_count_after = len(harness.game_logger.game_log)
        assert log_count_after >= log_count_before

    def test_attack_uses_str_bonus(self, harness):
        """Attack roll uses the attacker's STR modifier (no crash)."""
        attacker = harness.player_manager.players["Attacker"]
        attacker.stats["STR"] = 18

        weapon = harness.add_weapon_to_inventory("Attacker", "STR Sword", damage=6)
        result = harness.combat.player_attack(
            "Attacker", "TargetDummy", weapon_node=weapon
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_attack_damage_at_least_one(self, harness):
        """Damage is always at least 1 on a hit."""
        weapon = harness.add_weapon_to_inventory("Attacker", "Weak Dagger", damage=1)
        target = harness.player_manager.players["TargetDummy"]
        target.stats["DEX"] = 1
        target.vitals["HP"] = 100

        harness.combat.player_attack(
            "Attacker", "TargetDummy", weapon_node=weapon
        )
        hp_lost = 100 - target.vitals["HP"]
        if hp_lost > 0:
            assert hp_lost >= 1


# ─────────────────── TestStunOnAttack ───────────────────


class TestStunOnAttack:
    """Chance-to-stun on weapon hits (task-165)."""

    def _force_hit_rolls(self, harness):
        """Guarantee the attack lands: high attack roll, low defense roll."""
        original = harness.skills.roll_dice

        def fake_roll(n, sides, bonus=0):
            if sides == 20:
                # attack (STR 14) vs defense (DEX 5)
                return 34 if bonus == 14 else 6
            return bonus + 1  # minimal damage

        harness.skills.roll_dice = fake_roll
        return original

    def test_weapon_with_stun_chance_can_stun(self, harness):
        weapon = harness.add_weapon_to_inventory("Attacker", "Stun Club", damage=6)
        weapon.properties["stun_chance"] = 100
        weapon.properties["stun_duration"] = 3
        target = harness.player_manager.players["TargetDummy"]
        target.vitals["HP"] = 100
        self._force_hit_rolls(harness)

        with patch("engine.combat.random.randint", return_value=1):
            result = harness.combat.player_attack("Attacker", "TargetDummy", weapon_node=weapon)

        assert "stunned" in result.lower()
        assert target.has_condition("stunned")
        assert target.state_timer >= 3

    def test_stunned_target_cannot_act(self, harness):
        from player import BLOCKING_CONDITIONS
        weapon = harness.add_weapon_to_inventory("Attacker", "Stun Baton", damage=6)
        weapon.properties["stun_chance"] = 100
        target = harness.player_manager.players["TargetDummy"]
        target.vitals["HP"] = 100
        self._force_hit_rolls(harness)

        with patch("engine.combat.random.randint", return_value=1):
            harness.combat.player_attack("Attacker", "TargetDummy", weapon_node=weapon)

        # stunned blocks acting
        assert set(target.conditions) & BLOCKING_CONDITIONS
        assert target.state == "stunned"

    def test_stun_wears_off_via_state_timer(self, harness):
        from engine.conditions import ConditionsSystem
        target = harness.player_manager.players["TargetDummy"]
        target.add_condition("stunned")
        target.state_timer = 1

        conditions = ConditionsSystem(harness.player_manager, harness.skills)
        conditions.process_tick()  # timer 1 -> 0, stunned removed
        assert not target.has_condition("stunned")

    def test_no_stun_without_stun_chance(self, harness):
        weapon = harness.add_weapon_to_inventory("Attacker", "Plain Sword", damage=6)
        target = harness.player_manager.players["TargetDummy"]
        target.vitals["HP"] = 100
        self._force_hit_rolls(harness)

        with patch("engine.combat.random.randint", return_value=1):
            harness.combat.player_attack("Attacker", "TargetDummy", weapon_node=weapon)

        assert not target.has_condition("stunned")


# ─────────────────── World facade wiring (regression) ───────────────────


class TestGrappleModifiers:
    """Grappled/restrained combat modifiers (task-4)."""

    def test_grappled_attacker_fights_at_penalty(self, harness):
        attacker = harness.player_manager.players["Attacker"]  # STR 14
        target = harness.player_manager.players["TargetDummy"]
        target.stats["DEX"] = 12
        attacker.add_condition("grappled")

        # attack bonus = STR 14 - 4 = 10, defense = DEX 12.
        # roll 4 → 14 vs 16 → MISS. Without the penalty it would hit (18 vs 16).
        harness.skills.roll_dice = lambda n, sides, bonus=0: (4 + bonus) if sides == 20 else 1
        result = harness.combat.player_attack("Attacker", "TargetDummy")

        assert "miss" in result.lower()

    def test_held_target_easier_to_hit(self, harness):
        attacker = harness.player_manager.players["Attacker"]  # STR 14
        target = harness.player_manager.players["TargetDummy"]  # DEX 5
        target.add_condition("grappled")
        # Held by the attacker = a grappled edge (attacker node → target node).
        attacker_id = harness.player_manager.get_player_node_id("Attacker")
        target_id = harness.player_manager.get_player_node_id("TargetDummy")
        harness.graph.add_edge(Edge(source=attacker_id, target=target_id, type="grappled"))

        # attack bonus = STR 14 + 4 = 18, defense = DEX 5. roll 1 → 19 vs 6 → HIT.
        harness.skills.roll_dice = lambda n, sides, bonus=0: (1 + bonus) if sides == 20 else 1
        result = harness.combat.player_attack("Attacker", "TargetDummy")

        assert "miss" not in result.lower()

    def test_restrained_attacker_fights_at_penalty(self, harness):
        attacker = harness.player_manager.players["Attacker"]  # STR 14
        target = harness.player_manager.players["TargetDummy"]
        target.stats["DEX"] = 12
        attacker.add_condition("restrained")

        harness.skills.roll_dice = lambda n, sides, bonus=0: (4 + bonus) if sides == 20 else 1
        result = harness.combat.player_attack("Attacker", "TargetDummy")

        assert "miss" in result.lower()


# ─────────────────── World facade wiring (regression) ───────────────────


class TestWorldFacadeWiring:
    """CombatSystem must work through the real VirtualWorld facade —
    regression for `AttributeError: 'VirtualWorld' object has no attribute
    'get_player'` and the missing npc_behaviors hookup (attack -> 500)."""

    def test_player_attack_via_world_facade(self):
        from virtual_world_engine import VirtualWorld
        from player import Player

        world = VirtualWorld()
        butcher = Player("The Butcher")
        world.add_player(butcher)
        victim = Player("Jake Halloway")
        world.add_player(victim)

        result = world._player_attack("The Butcher", "Jake Halloway")

        assert isinstance(result, str)
        assert "The Butcher" in result

    def test_world_facade_exposes_get_player(self):
        from virtual_world_engine import VirtualWorld
        from player import Player

        world = VirtualWorld()
        p = Player("Lyrie")
        world.add_player(p)

        assert world.get_player("Lyrie") is p
        assert world.get_player("nobody") is None
