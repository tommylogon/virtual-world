"""Incorporeal undead defences (task-490).

The other side of task-309's identities: not what an undead *is*, but what
cannot be done to one. A 5e ghost cannot be cut by a mundane blade, cannot be
chilled, poisoned or necrotically burned, and has nothing that can be grabbed.

The identities are tag checks (`engine/player_manager.is_undead` /
`is_incorporeal`); the profile they imply lives in `engine/undead.py`, and the
two hook points are damage resolution in `engine/combat` and condition
application in `engine/conditions`.

The arithmetic is deliberately *not* the item aggregate's flat subtraction:
5e resistance halves and immunity negates, and a halved point of damage is
nothing. Several tests below pin that distinction, because folding this into
`aggregate_bonuses` would be the obvious wrong move.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import create_app
from area import Area
from graph import Node
from player import Player

from engine import undead
from engine.undead import (
    GHOST_IMMUNE_CONDITIONS,
    NONMAGICAL_WEAPON,
    UNDEAD_IMMUNE_CONDITIONS,
    UNDEAD_IMMUNE_DAMAGE,
    apply_damage_resistance,
    condition_immunities,
    damage_profile,
    hit_line,
    is_immune_to_condition,
    is_incorporeal_undead,
    is_nonmagical_weapon,
    resistance_for_weapon,
)

AREA = "Verdant Hollow"


def _world():
    world = create_app({"TESTING": True}).world
    world.movement.add_area(Area(AREA, "A hollow.", []))
    return world


def _undead(world, name, tags):
    player = Player(name)
    player.tags = list(tags)
    world.add_player(player)
    world.set_player_area(name, AREA)
    return player


def _ghost(world, name="Wraith", manifested=True):
    """A *manifested* ghost.

    task-309 made an unmanifested ghost invisible, and combat refuses to strike
    what it cannot see — so an unmanifested ghost never reaches the damage hooks
    at all. Manifested is the state in which the resistances below actually
    apply, and `TestVisibilityGate` pins the interaction separately.
    """
    ghost = _undead(world, name, ["undead", "ghost"])
    ghost.manifested = manifested
    return ghost


def _zombie(world, name="Shambler"):
    """Corporeal undead: has a body, so it can be grappled and it bleeds."""
    return _undead(world, name, ["undead"])


def _mortal(world, name="Wraithbane"):
    # A name the world template does not already use: a duplicate display name
    # gets a suffixed registry key, and apply_condition() looks players up by
    # name, so a collision silently tests the template's character instead.
    return _undead(world, name, ["human"])


# ── identity ──

class TestIdentity:

    def test_a_ghost_is_undead_and_incorporeal(self):
        world = _world()
        assert is_incorporeal_undead(_ghost(world)) is True

    def test_a_zombie_is_not_incorporeal(self):
        """`is_undead_ghost` is the broad alias and would wrongly say yes."""
        world = _world()
        assert is_incorporeal_undead(_zombie(world)) is False
        assert _zombie(world).tags == ["undead"]

    def test_a_mortal_is_neither(self):
        world = _world()
        assert is_incorporeal_undead(_mortal(world)) is False

    def test_the_engine_identities_still_agree(self):
        """The profile must key off the same tags task-309 reads."""
        world = _world()
        ghost = _ghost(world)
        pm = world.player_manager
        assert pm.is_undead(ghost.name) is True
        assert pm.is_incorporeal(ghost.name) is True
        assert undead.damage_profile(ghost)["immune"]


# ── damage ──

class TestDamageProfile:

    def test_an_ordinary_character_has_no_profile(self):
        world = _world()
        profile = damage_profile(_mortal(world))
        assert profile["resist"] == set()
        assert profile["immune"] == set()

    def test_a_ghost_is_immune_to_cold_poison_and_necrotic(self):
        world = _world()
        immune = damage_profile(_ghost(world))["immune"]
        assert {"cold", "necrotic", "poison"} <= immune

    def test_a_zombie_shares_the_damage_immunities(self):
        world = _world()
        assert damage_profile(_zombie(world))["immune"] == \
            damage_profile(_ghost(world))["immune"]

    def test_no_profile_is_none(self):
        """A caller applies the result without branching on character type."""
        assert damage_profile(_mortal(_world())) is not None


class TestResistanceArithmetic:

    def test_immunity_negates(self):
        outcome = apply_damage_resistance(10, "cold", {"immune": {"cold"}})
        assert outcome["damage"] == 0
        assert outcome["immune"] is True

    def test_resistance_halves(self):
        outcome = apply_damage_resistance(10, "force", {"resist": {"force"}})
        assert outcome["damage"] == 5
        assert outcome["resisted"] is True

    def test_resistance_halves_rather_than_subtracts(self):
        """This is the whole reason for a separate profile."""
        flat = 10 - 3
        assert apply_damage_resistance(10, "force", {"resist": {"force"}})["damage"] \
            != flat

    def test_a_halved_point_of_damage_is_nothing(self):
        assert apply_damage_resistance(1, "force", {"resist": {"force"}})["damage"] == 0

    def test_immunity_beats_resistance(self):
        outcome = apply_damage_resistance(9, "cold",
                                         {"resist": {"cold"}, "immune": {"cold"}})
        assert outcome["damage"] == 0
        assert outcome["immune"] is True

    def test_an_unrelated_type_is_untouched(self):
        outcome = apply_damage_resistance(9, "slashing", {"immune": {"cold"}})
        assert outcome["damage"] == 9
        assert not outcome["immune"] and not outcome["resisted"]

    def test_damage_type_matching_is_case_insensitive(self):
        assert apply_damage_resistance(5, "COLD", {"immune": {"cold"}})["damage"] == 0

    def test_a_blank_damage_type_is_untouched(self):
        assert apply_damage_resistance(5, "", {"immune": {"cold"}})["damage"] == 5

    def test_no_profile_leaves_damage_alone(self):
        assert apply_damage_resistance(7, "cold", None)["damage"] == 7

    def test_the_poison_spelling_variant_is_covered(self):
        assert "poisoned" in UNDEAD_IMMUNE_DAMAGE


class TestWeaponMagicalness:
    """The 5e rule is about the *weapon*, not the injury.

    A ghost resists a mundane blade whether it cuts, bludgeons or pierces.
    Keying the resistance on ``slashing`` would miss every other weapon, so the
    profile carries a ``NONMAGICAL_WEAPON`` sentinel and the caller says where
    the hit came from.
    """

    def test_a_ghost_resists_any_mundane_weapon(self):
        world = _world()
        profile = damage_profile(_ghost(world))
        for damage_type in ("slashing", "bludgeoning", "piercing"):
            outcome = apply_damage_resistance(10, damage_type, profile,
                                              from_nonmagical_weapon=True)
            assert outcome["resisted"] is True, damage_type
            assert outcome["damage"] == 5

    def test_the_same_weapon_hurts_a_mortal(self):
        world = _world()
        profile = damage_profile(_mortal(world))
        assert apply_damage_resistance(10, "slashing", profile,
                                       from_nonmagical_weapon=True)["damage"] == 10

    def test_a_zombie_is_not_weapon_resistant(self):
        """It has a body. A blade works on a zombie; it does not on a ghost."""
        world = _world()
        profile = damage_profile(_zombie(world))
        assert NONMAGICAL_WEAPON not in profile["resist"]
        assert apply_damage_resistance(10, "slashing", profile,
                                       from_nonmagical_weapon=True)["damage"] == 10

    def test_a_magical_blade_goes_through(self):
        world = _world()
        profile = resistance_for_weapon(_ghost(world),
                                        {"damage_type": "slashing", "magical": True})
        assert NONMAGICAL_WEAPON not in profile["resist"]
        assert apply_damage_resistance(10, "slashing", profile,
                                       from_nonmagical_weapon=False)["damage"] == 10

    def test_an_enchanted_blade_goes_through(self):
        world = _world()
        profile = resistance_for_weapon(_ghost(world), {"enchanted": True})
        assert NONMAGICAL_WEAPON not in profile["resist"]

    def test_a_spell_goes_through(self):
        world = _world()
        profile = resistance_for_weapon(_ghost(world), {"spell_id": "magic-missile"})
        assert NONMAGICAL_WEAPON not in profile["resist"]

    def test_an_unstated_blade_is_mundane(self):
        """The world has to say a weapon is enchanted for it to be."""
        assert is_nonmagical_weapon({"damage": "1d8"}) is True

    def test_a_magical_flag_makes_it_not_mundane(self):
        assert is_nonmagical_weapon({"magical": True}) is False

    def test_a_bare_fist_is_not_a_nonmagical_weapon(self):
        """A ghost is hard to hurt with a sword, not with a fist through it."""
        assert is_nonmagical_weapon({}) is False
        assert is_nonmagical_weapon(None) is False

    def test_a_false_magical_flag_is_still_mundane(self):
        assert is_nonmagical_weapon({"magical": False}) is True

    def test_magicalness_does_not_grant_damage_type_immunity(self):
        """A magic sword is still not a cold weapon."""
        world = _world()
        profile = resistance_for_weapon(_ghost(world), {"magical": True})
        assert "cold" in profile["immune"]

    def test_a_mortal_is_unaffected_by_weapon_magicalness(self):
        world = _world()
        profile = resistance_for_weapon(_mortal(world), {"magical": True})
        assert profile["resist"] == set() and profile["immune"] == set()

    def test_the_damage_type_resistances_still_work_without_a_weapon(self):
        """`lightning` is in the resist table as a plain damage type."""
        world = _world()
        profile = damage_profile(_ghost(world))
        assert apply_damage_resistance(10, "lightning", profile)["resisted"] is True


class TestFlavourLines:

    def test_an_immune_hit_has_a_line(self):
        world = _world()
        line = hit_line(10, "cold", damage_profile(_ghost(world)), "Wraith")
        assert "Wraith" in line

    def test_a_resisted_hit_has_a_line(self):
        world = _world()
        line = hit_line(10, "force", damage_profile(_ghost(world)), "Wraith")
        assert "Wraith" in line

    def test_a_normal_hit_has_no_line(self):
        world = _world()
        assert hit_line(10, "slashing", damage_profile(_mortal(world)), "Lyrie") == ""

    def test_a_line_never_mentions_hit_points(self):
        """Combat reports wounds, not numbers."""
        world = _world()
        for line in undead.IMMUNE_HIT_LINES + undead.RESIST_HIT_LINES:
            assert "HP" not in line and "damage" not in line.lower()

    def test_every_line_formats(self):
        for table in (undead.IMMUNE_HIT_LINES, undead.RESIST_HIT_LINES):
            for template in table:
                assert "{target}" in template
                assert template.format(target="Wraith")


# ── conditions ──

class TestConditionImmunities:

    def test_a_ghost_cannot_be_grappled_restrained_or_proned(self):
        world = _world()
        for condition in ("grappled", "restrained", "prone", "paralysed", "petrified"):
            assert is_immune_to_condition(_ghost(world), condition) is True

    def test_a_ghost_does_not_tire(self):
        """5e: all conditions except exhaustion. Dropping it would rewrite the rule."""
        world = _world()
        assert is_immune_to_condition(_ghost(world), "exhausted") is False

    def test_a_zombie_can_be_grappled(self):
        """It has a body. Only the exhaustion and sensation list applies."""
        world = _world()
        zombie = _zombie(world)
        assert is_immune_to_condition(zombie, "grappled") is False
        assert is_immune_to_condition(zombie, "exhausted") is True

    def test_a_mortal_is_immune_to_nothing(self):
        world = _world()
        for condition in ("grappled", "restrained", "exhausted", "poisoned"):
            assert is_immune_to_condition(_mortal(world), condition) is False

    def test_the_two_lists_are_the_fivee_shape(self):
        assert "grappled" in GHOST_IMMUNE_CONDITIONS
        assert "restrained" in GHOST_IMMUNE_CONDITIONS
        assert "prone" in GHOST_IMMUNE_CONDITIONS
        assert "exhausted" not in GHOST_IMMUNE_CONDITIONS

    def test_the_lists_differ_by_exactly_exhaustion(self):
        """5e: a ghost is immune to everything *except* exhaustion."""
        assert UNDEAD_IMMUNE_CONDITIONS - GHOST_IMMUNE_CONDITIONS == {"exhausted"}
        assert UNDEAD_IMMUNE_CONDITIONS <= (GHOST_IMMUNE_CONDITIONS | {"exhausted"})

    def test_every_listed_condition_is_a_real_condition(self):
        from engine.player_conditions import CONDITION_DEFINITIONS
        for condition in GHOST_IMMUNE_CONDITIONS | UNDEAD_IMMUNE_CONDITIONS:
            assert condition in CONDITION_DEFINITIONS, \
                f"{condition} is listed as immune but is not a condition"


# ── the hooks ──

class TestConditionApplicationHook:

    def test_a_ghost_refuses_grappled(self):
        world = _world()
        ghost = _ghost(world)
        assert world.conditions.apply_condition(ghost.name, "grappled") is False
        assert not ghost.has_condition("grappled")

    def test_a_ghost_accepts_exhausted(self):
        world = _world()
        ghost = _ghost(world)
        assert world.conditions.apply_condition(ghost.name, "exhausted") is True
        assert ghost.has_condition("exhausted")

    def test_a_mortal_is_unaffected(self):
        world = _world()
        mortal = _mortal(world)
        assert world.conditions.apply_condition(mortal.name, "grappled") is True
        assert mortal.has_condition("grappled")

    def test_a_refusal_returns_false_not_none(self):
        """A refusal must be distinguishable from a missing player."""
        world = _world()
        ghost = _ghost(world)
        assert world.conditions.apply_condition(ghost.name, "prone") is False
        assert world.conditions.apply_condition("Nobody At All", "prone") is False

    def test_a_ghost_still_accepts_an_ordinary_condition(self):
        world = _world()
        ghost = _ghost(world)
        assert world.conditions.apply_condition(ghost.name, "injured") is False
        assert world.conditions.apply_condition(ghost.name, "exhausted") is True

    def test_allow_immune_bypasses_the_check(self):
        """The ghost system's own path puts a character INTO ghost state."""
        world = _world()
        ghost = _ghost(world)
        assert world.conditions.apply_condition(
            ghost.name, "prone", allow_immune=True) is True
        assert ghost.has_condition("prone")

    def test_exhaustion_reaches_a_zombie_refusal(self):
        world = _world()
        zombie = _zombie(world)
        assert world.conditions.apply_condition(zombie.name, "exhausted") is False
        assert not zombie.has_condition("exhausted")


class TestCombatHook:

    def _armed(self, world, item_id="item_rusty_sword", name="rusty sword",
               **extra):
        props = {"damage": "1d8", "damage_type": "slashing"}
        props.update(extra)
        world.graph.add_node(Node(id=item_id, type="item", name=name,
                                  properties=props))
        return world.graph.get_node(item_id)

    def _brute(self, world, name="Brute"):
        """An attacker that cannot miss: STR 30 beats any d20 + DEX."""
        attacker = _undead(world, name, ["human"])
        attacker.stats["STR"] = 30
        return attacker

    def _fight(self, world, attacker, target, weapon):
        return world.combat.player_attack(attacker.name, target.name, weapon_node=weapon)

    def test_a_mundane_blade_is_resisted_by_a_ghost(self):
        world = _world()
        ghost = _ghost(world)
        hp_before = ghost.vitals["HP"]
        message = self._fight(world, self._brute(world), ghost, self._armed(world))
        assert "barely takes hold" in message or "lost to" in message
        assert ghost.vitals["HP"] < hp_before, "a resisted blow should still wound"
        assert ghost.vitals["HP"] > hp_before - 30, "but not for full damage"

    def test_a_magic_blade_hurts_a_ghost(self):
        """The 5e rule, and the reason a ghost is a problem to fight."""
        world = _world()
        ghost = _ghost(world)
        weapon = self._armed(world, item_id="item_enchanted",
                             name="enchanted sword", magical=True)
        hp_before = ghost.vitals["HP"]
        self._fight(world, self._brute(world), ghost, weapon)
        assert ghost.vitals["HP"] < hp_before

    def test_a_ghost_takes_no_injury_from_an_immune_blow(self):
        """Cold damage is negated outright, so nothing is cut."""
        world = _world()
        ghost = _ghost(world)
        weapon = self._armed(world, item_id="item_icy", name="frost brand",
                             damage_type="cold")
        self._fight(world, self._brute(world), ghost, weapon)
        assert ghost.vitals["HP"] == ghost.vitals.get("Max_HP", 100)
        assert not any(cid in ghost.conditions for cid in ("injured", "bleeding"))

    def test_an_ordinary_character_takes_normal_damage(self):
        world = _world()
        mortal = _mortal(world)
        hp_before = mortal.vitals["HP"]
        self._fight(world, self._brute(world), mortal, self._armed(world))
        assert mortal.vitals["HP"] < hp_before

    def test_the_combat_hook_does_not_change_a_mortal_message(self):
        world = _world()
        mortal = _mortal(world)
        message = self._fight(world, self._brute(world), mortal, self._armed(world))
        assert "passes straight through" not in message
        assert "not touched" not in message


class TestVisibilityGateStillWins:
    """task-309 and task-490 are two layers, and order matters."""

    def test_an_unmanifested_ghost_is_never_struck(self):
        world = _world()
        ghost = _ghost(world, "Wraith", manifested=False)
        weapon = TestCombatHook()._armed(world, item_id="item_ench",
                                         name="enchanted sword", magical=True)
        message = TestCombatHook()._fight(world, TestCombatHook()._brute(world),
                                          ghost, weapon)
        assert "not there to hit" in message
        assert ghost.vitals["HP"] == 100

    def test_manifesting_is_what_lets_a_magical_blade_through(self):
        """The two gates, in order: see it, then hurt it."""
        world = _world()
        combat = TestCombatHook()
        for manifested, expects_damage in ((False, False), (True, True)):
            ghost = _ghost(world, f"Wraith{manifested}", manifested=manifested)
            weapon = combat._armed(world, item_id=f"item_ench{manifested}",
                                   name="enchanted sword", magical=True)
            before = ghost.vitals["HP"]
            combat._fight(world, combat._brute(world, f"Brute{manifested}"),
                          ghost, weapon)
            assert (ghost.vitals["HP"] < before) is expects_damage
