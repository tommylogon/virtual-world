"""Pregnancy, gestation, and birth tests (task-846).

Verifies conception gating by life-stage fertility and consent/willingness,
bounded gestation tracking across sim time, and live birth creating
a real character with birth_tick, graph node, and area placement.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from player import Player
from engine import character_appearance as ca
from engine import lifecycle as lc
from engine import pregnancy as preg


def _world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Camp Entrance", "A wooden palisade gate.", []))
    world.movement.add_area(Area("Mess Hall", "Long tables and benches.", []))
    return world


def _character(world, name, age=25, area="Camp Entrance"):
    player = Player(name)
    world.add_player(player)
    world.set_player_area(name, area)
    node = world.graph.get_node(world._player_node_id(name))
    ca.set_record(node, {"identity": {"age": age}})
    lc.ensure_birth_tick(player, world, node)
    player.life_stage = lc.life_stage(age)
    return player


def test_conception_requires_fertility_by_stage():
    world = _world()
    mother = _character(world, "Elena", age=25)
    father = _character(world, "Marcus", age=28)

    # Both adults: fertile
    fertile, reason = preg.is_fertile(mother, world)
    assert fertile is True, reason

    # Child (age 10) cannot conceive
    child = _character(world, "LittleTimmy", age=10)
    fertile, reason = preg.is_fertile(child, world)
    assert fertile is False
    assert "minor" in reason

    success, msg = preg.attempt_conception(child, father, world)
    assert success is False
    assert "minor" in msg

    # Adolescent (age 15) cannot conceive
    teen = _character(world, "Sarah", age=15)
    fertile, reason = preg.is_fertile(teen, world)
    assert fertile is False
    assert "minor" in reason

    success, msg = preg.attempt_conception(teen, father, world)
    assert success is False
    assert "minor" in msg

    # Elder (age 65) cannot conceive
    elder = _character(world, "GrandmaGreta", age=65)
    fertile, reason = preg.is_fertile(elder, world)
    assert fertile is False
    assert "elder" in reason

    success, msg = preg.attempt_conception(elder, father, world)
    assert success is False
    assert "elder" in msg

    # Sterile trait cannot conceive
    mother.traits["sterile"] = True
    fertile, reason = preg.is_fertile(mother, world)
    assert fertile is False
    assert "sterile" in reason


def test_conception_requires_willingness_and_consent():
    world = _world()
    mother = _character(world, "Kiala", age=24)
    father = _character(world, "Gromm", age=26)

    # Explicit unwilling flag
    mother.willing = False
    success, msg = preg.attempt_conception(mother, father, world)
    assert success is False
    assert "unwilling" in msg
    mother.willing = True

    # Partner unwilling
    father.willing = False
    success, msg = preg.attempt_conception(mother, father, world)
    assert success is False
    assert "unwilling" in msg
    father.willing = True

    # Boundary against pregnancy
    mother_node = world.graph.get_node(world._player_node_id("Kiala"))
    ca.set_record(mother_node, {
        "identity": {"age": 24},
        "personality": {"boundaries": ["pregnancy"]}
    })
    success, msg = preg.attempt_conception(mother, father, world)
    assert success is False
    assert "boundary" in msg

    # Clear boundary
    ca.set_record(mother_node, {
        "identity": {"age": 24},
        "personality": {"boundaries": []}
    })

    # Negative consent in relationship
    mother.relationships["Gromm"] = {"consent": -0.8}
    success, msg = preg.attempt_conception(mother, father, world)
    assert success is False
    assert "does not consent" in msg

    # Positive consent succeeds
    mother.relationships["Gromm"] = {"consent": 0.5}
    father.relationships["Kiala"] = {"consent": 0.7}
    success, msg = preg.attempt_conception(mother, father, world)
    assert success is True
    assert mother.pregnancy is not None
    assert mother.pregnancy["partner"] == "Gromm"


def test_gestation_progression_over_sim_ticks():
    world = _world()
    mother = _character(world, "Lyrie", age=22)
    father = _character(world, "Arix", age=24)

    # 100 ticks gestation
    success, _ = preg.attempt_conception(mother, father, world, gestation_ticks=100)
    assert success is True
    assert mother.pregnancy["stage"] == "first_trimester"

    # Tick forward 20 ticks: still first trimester
    world.time_ticks += 20
    stage, _ = preg.update_pregnancy(mother, world)
    assert stage == "first_trimester"

    # Tick forward to tick 40: second trimester
    world.time_ticks += 20
    stage, ev = preg.update_pregnancy(mother, world)
    assert stage == "second_trimester"
    assert ev is not None and "second_trimester" in ev

    # Tick forward to tick 75: third trimester
    world.time_ticks += 35
    stage, ev = preg.update_pregnancy(mother, world)
    assert stage == "third_trimester"
    assert ev is not None and "third_trimester" in ev

    # Tick forward to tick 100+: due
    world.time_ticks += 30
    stage, _ = preg.update_pregnancy(mother, world)
    assert stage == "due"


def test_live_birth_event_and_child_creation():
    world = _world()
    mother = _character(world, "Belne", age=23, area="Mess Hall")
    father = _character(world, "Viktor", age=25, area="Camp Entrance")

    success, _ = preg.attempt_conception(mother, father, world, gestation_ticks=50)
    assert success is True

    # Advance clock to due date
    world.time_ticks += 55
    events = lc.on_clock(world)

    # Delivery occurs
    assert any("gave birth" in e for e in events)
    assert mother.pregnancy is None

    # Child exists as a real character
    child_name = "Child of Belne"
    child = world.get_player(child_name)
    assert child is not None
    assert child.birth_tick == world.time_ticks
    assert child.life_stage == "child"
    assert child.current_area == "Mess Hall"

    # Child has a node in the graph
    child_node = world.graph.get_node(world._player_node_id(child_name))
    assert child_node is not None
    assert child_node.type == "character"

    # Relationships established
    assert child.relationships["Belne"]["role"] == "mother"
    assert mother.relationships[child_name]["role"] == "child"
    assert child.relationships["Viktor"]["role"] == "father"
    assert father.relationships[child_name]["role"] == "child"


def test_no_unbounded_per_character_store():
    world = _world()
    mother = _character(world, "Mikka", age=21)
    father = _character(world, "Tusker", age=23)

    preg.attempt_conception(mother, father, world, gestation_ticks=10)
    # Bounded dict only
    p = mother.pregnancy
    assert isinstance(p, dict)
    assert set(p.keys()) == {"partner", "conception_tick", "due_tick", "gestation_ticks", "stage"}

    # After delivery, cleared to None
    world.time_ticks += 15
    lc.on_clock(world)
    assert mother.pregnancy is None


def test_pregnancy_round_trips_through_serialization():
    world = _world()
    mother = _character(world, "Zikka", age=20)
    father = _character(world, "Gribba", age=22)

    preg.attempt_conception(mother, father, world, gestation_ticks=200)
    world.time_ticks += 80
    preg.update_pregnancy(mother, world)

    # Save to scenario dict
    data = world.to_scenario_dict()

    # Load into new world
    new_world = _world()
    new_world.load_from_dict(data)
    loaded_mother = new_world.get_player("Zikka")
    assert loaded_mother is not None
    assert loaded_mother.pregnancy is not None
    assert loaded_mother.pregnancy["partner"] == "Gribba"
    assert loaded_mother.pregnancy["stage"] == "second_trimester"
    assert loaded_mother.pregnancy["due_tick"] == 200


def test_minors_are_never_eligible_whatever_the_clock_says():
    world = _world()
    partner = _character(world, "Marcus", age=30)

    # Tagged teen, but the authored age (30) would make the clock say adult.
    teen = _character(world, "Arixlike", age=30)
    teen.tags = list(getattr(teen, "tags", []) or []) + ["teen"]
    fertile, reason = preg.is_fertile(teen, world)
    assert fertile is False
    assert "minor" in reason
    ok, msg = preg.attempt_conception(partner, teen, world)
    assert ok is False and "minor" in msg
    assert getattr(partner, "pregnancy", None) is None

    # Authored age 12 on a goblin (3x age rate would make it adult by the clock).
    young = _character(world, "YoungGoblin", age=12)
    node = world.graph.get_node(world._player_node_id("YoungGoblin"))
    ca.set_record(node, {"identity": {"age": 12, "species": "goblin"}})
    young.life_stage = "adult"  # a stale or inflated cached stage must not matter
    fertile, reason = preg.is_fertile(young, world)
    assert fertile is False
    assert "minor" in reason
    assert preg.minor_reason(young, node) is not None
