"""Tests for faction-scoped hostility and group-aware fear (task-742)."""

import pytest
from app import create_app
from area import Area
from player import Player
from engine.hostility import is_hostile_to, hunted_groups
from engine.fear import fear_sources_for_character, fear_sources


def _world():
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _add_player(world, name, area, tags=None, traits=None, fear_tags=None):
    p = Player(name)
    p.current_area = area
    world.add_player(p)
    world.set_player_area(name, area)
    if tags:
        p.tags = list(tags)
    if traits:
        p.traits = dict(traits)
    if fear_tags:
        p.fear_tags = list(fear_tags)
    return p


# ─────────────────────────────────────────────────────────────────────────────
# 1. Mechanism tests: Hostility relation
# ─────────────────────────────────────────────────────────────────────────────

def test_same_faction_creatures_ignore_each_other():
    """Two faction:lich_a undead do not target each other."""
    w = _world()
    z1 = _add_player(w, "Zombie_A1", "Crypt", tags=["undead", "faction:lich_a"], traits={"slasher": True})
    z2 = _add_player(w, "Zombie_A2", "Crypt", tags=["undead", "faction:lich_a"], traits={"slasher": True})

    assert not is_hostile_to(z1, z2, w)
    assert not is_hostile_to(z2, z1, w)


def test_different_faction_creatures_are_hostile():
    """lich_a and lich_b undead are hostile to each other."""
    w = _world()
    z_a = _add_player(w, "Zombie_A", "Crypt", tags=["undead", "faction:lich_a"], traits={"slasher": True})
    z_b = _add_player(w, "Zombie_B", "Crypt", tags=["undead", "faction:lich_b"], traits={"slasher": True})

    assert is_hostile_to(z_a, z_b, w)
    assert is_hostile_to(z_b, z_a, w)


def test_mansion_slasher_regression():
    """The mansion slasher targets living victims, but not other slashers."""
    w = _world()
    slasher = _add_player(w, "The Slasher", "Foyer", traits={"slasher": True})
    victim = _add_player(w, "Sammy", "Foyer")
    slasher_2 = _add_player(w, "Other Slasher", "Foyer", traits={"slasher": True})

    # Targets ordinary victim
    assert is_hostile_to(slasher, victim, w)
    # Ignores other unaligned slashers (mansion invariant)
    assert not is_hostile_to(slasher, slasher_2, w)


def test_hostile_trait_is_wired():
    """A creature with the hostile trait participates in hostility."""
    w = _world()
    orc = _add_player(w, "Orc Raider", "Camp", tags=["faction:iron_fang"], traits={"hostile": True})
    human = _add_player(w, "Villager", "Camp", tags=["faction:human"])
    orc_ally = _add_player(w, "Orc Peon", "Camp", tags=["faction:iron_fang"])

    assert is_hostile_to(orc, human, w)
    assert not is_hostile_to(orc, orc_ally, w)


def test_explicit_hunts_tags():
    """Creature declaring hunts:<group> only hunts matching targets."""
    w = _world()
    hunter = _add_player(w, "Mage Hunter", "Road", tags=["hunts:magic"])
    mage = _add_player(w, "Wizard", "Road", tags=["magic"])
    warrior = _add_player(w, "Fighter", "Road", tags=["warrior"])

    assert is_hostile_to(hunter, mage, w)
    assert not is_hostile_to(hunter, warrior, w)


def test_dead_targets_are_never_hostile():
    w = _world()
    slasher = _add_player(w, "Slasher", "Foyer", traits={"slasher": True})
    corpse = _add_player(w, "Victim", "Foyer")
    corpse.state = "dead"

    assert not is_hostile_to(slasher, corpse, w)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Mechanism tests: Group-aware fear
# ─────────────────────────────────────────────────────────────────────────────

def test_undead_do_not_fear_undead():
    """Undead creatures do not fear sources in their own group."""
    w = _world()
    z1 = _add_player(w, "Zombie_1", "Crypt", tags=["undead"], fear_tags=["undead", "holy"])
    z2 = _add_player(w, "Zombie_2", "Crypt", tags=["undead"])

    # z1 carries fear_tags: ["undead"], but because z1 itself is "undead", it is exempt
    source = fear_sources_for_character(w, z1, z2)
    assert source is None


def test_goblin_fears_non_hostile_zombie():
    """A goblin with fear_tag undead fears a zombie with no hostile traits."""
    w = _world()
    goblin = _add_player(w, "Grub", "Cave", tags=["goblin"], fear_tags=["undead"])
    # Passive docile zombie without hostile trait or slasher trait
    zombie = _add_player(w, "Docile Zombie", "Cave", tags=["undead"])

    # Zombie is not hostile to goblin
    assert not is_hostile_to(zombie, goblin, w)

    # But goblin still fears the zombie due to fear_tags
    source = fear_sources_for_character(w, goblin, zombie)
    assert source is not None
    assert source["name"] == "Docile Zombie"
    assert source["tags"] == ["undead"]


def test_faction_and_fear_are_independent():
    """Lich-A and Lich-B undead fight each other, but do not fear each other."""
    w = _world()
    z_a = _add_player(w, "Zombie_A", "Tomb", tags=["undead", "faction:lich_a"], traits={"slasher": True}, fear_tags=["undead"])
    z_b = _add_player(w, "Zombie_B", "Tomb", tags=["undead", "faction:lich_b"], traits={"slasher": True}, fear_tags=["undead"])

    # Hostility check: they are hostile to each other across factions
    assert is_hostile_to(z_a, z_b, w)
    assert is_hostile_to(z_b, z_a, w)

    # Fear check: neither fears the other because both share the undead group
    assert fear_sources_for_character(w, z_a, z_b) is None
    assert fear_sources_for_character(w, z_b, z_a) is None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Micro-scenario: slasher_hunt with faction target selection
# ─────────────────────────────────────────────────────────────────────────────

def test_micro_scenario_faction_hunt_and_fear():
    """End-to-end: Lich-A zombie ignores Lich-A ally and paths toward Lich-B enemy."""
    w = _world()
    # Create two connected areas
    w.movement.add_area(Area("Hall_A", "Hall A", []))
    w.movement.add_area(Area("Hall_B", "Hall B", []))
    w.movement.connect_areas("Hall_A", "Hall_B", "doorway_a", "doorway_b", state="open")

    z_a1 = _add_player(w, "Hunter_A1", "Hall_A", tags=["undead", "faction:lich_a"], traits={"slasher": True})
    z_a2 = _add_player(w, "Ally_A2", "Hall_A", tags=["undead", "faction:lich_a"], traits={"slasher": True})
    z_b1 = _add_player(w, "Enemy_B1", "Hall_B", tags=["undead", "faction:lich_b"], traits={"slasher": True})

    nearest = w.npc_behaviors._get_nearest_player_to("Hunter_A1")

    # Hunter_A1 ignores co-located Ally_A2 and targets Enemy_B1 in Hall_B!
    assert nearest == "Enemy_B1"