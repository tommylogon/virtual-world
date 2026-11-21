"""Tests for bug-595: disposition-driven physical combat bystander responses."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from player import Player
from virtual_world_engine import VirtualWorld


def _add_actor(world, name, area, *, simple_npc=False, traits=None, relationships=None):
    p = Player(name=name)
    p.current_area = area
    p.simple_npc = simple_npc
    if traits:
        p.traits = traits
    if relationships:
        p.relationships = relationships
    world.player_manager.add_player(p)
    return p


def _make_two_room_world():
    world = VirtualWorld()
    world.movement.add_area(Area("tavern", "A bustling tavern.", []))
    world.movement.add_area(Area("street", "A quiet street outside.", []))
    world.movement.connect_areas("tavern", "street", "south", "north")
    return world


def test_combat_bystanders_multiple_physical_responses():
    world = _make_two_room_world()
    area = "tavern"

    attacker = _add_actor(world, "Raider", area)
    victim = _add_actor(world, "Merchant", area)

    coward = _add_actor(world, "TimidBystander", area, simple_npc=True, traits={"cowardly": {"level": 1}})
    ally = _add_actor(
        world,
        "GuardAlly",
        area,
        simple_npc=True,
        traits={"protective": {"level": 1}},
        relationships={"Merchant": {"closeness": 65}},
    )
    witness = _add_actor(world, "NeutralWitness", area, simple_npc=True)

    # Make perception deterministic so all 3 co-located bystanders witness the fight
    world.npc_behaviors.check_perception = lambda npc, dc: True
    lines = world.npc_behaviors.process_npcs_on_combat({"combat_actors": [attacker.name, victim.name]})

    # All 3 bystanders should react (no max_reactions=1 cap)
    assert len(lines) >= 3
    # Coward fled to another area
    assert coward.current_area == "street"
    # Ally went alert and targeted the attacker
    assert ally.npc_state == "alert"
    assert getattr(ally, "pack_target", None) == attacker.name
    # Neutral witness went alert
    assert witness.npc_state == "alert"


def test_cornered_fearful_bystander_hides():
    world = VirtualWorld()
    world.movement.add_area(Area("cellar_trap", "A dead-end cellar.", []))

    attacker = _add_actor(world, "Thug", "cellar_trap")
    victim = _add_actor(world, "Target", "cellar_trap")
    cornered = _add_actor(world, "CorneredCivilian", "cellar_trap", simple_npc=True, traits={"fearful": {"level": 1}})

    world.npc_behaviors.check_perception = lambda npc, dc: True
    lines = world.npc_behaviors.process_npcs_on_combat({"combat_actors": [attacker.name, victim.name]})
    assert len(lines) == 1
    assert cornered.hidden is True
    assert cornered.npc_state == "hiding"
