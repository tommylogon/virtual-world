"""Tests for reproductive cycle, periods, and estrus (task-928).

Verifies:
- Species patterns (none, cycle, heat)
- Phase progression on clock ticks
- Condition application (menstruating, ovulating, in_heat) and clearing
- Fertility window integration with engine/pregnancy.is_fertile
- Pregnancy suspension and postpartum resumption
- Willingness and consent boundaries are never bypassed
- Scenario verification against kraktooth_goblin_camp.json and Millwood.json
"""

import json
from pathlib import Path
import pytest

from area import Area
from player import Player
from engine import character_appearance as ca
from engine import lifecycle as lc
from engine import pregnancy as preg
from engine import reproductive_cycle
from virtual_world_engine import VirtualWorld


def _world():
    world = VirtualWorld()
    world.mature_content = True
    world.movement.add_area(Area("Camp Entrance", "A wooden palisade gate.", []))
    world.movement.add_area(Area("Mess Hall", "Long tables and benches.", []))
    return world


def _character(world, name, age=25, species="human", sex="female", area="Camp Entrance"):
    player = Player(name)
    player.gender = sex
    world.add_player(player)
    world.set_player_area(name, area)
    node = world.graph.get_node(world._player_node_id(name))
    node.properties["species"] = species
    node.properties["sex"] = sex
    node.properties["tags"] = [sex, "adult", species]
    ca.set_record(node, {"identity": {"age": age}})
    lc.ensure_birth_tick(player, world, node)
    player.life_stage = lc.life_stage(age)
    return player, node


def test_species_pattern_resolution():
    """Verify species declare correct cycle patterns."""
    assert reproductive_cycle.pattern_for_species("human") == "cycle"
    assert reproductive_cycle.pattern_for_species("elf") == "cycle"
    assert reproductive_cycle.pattern_for_species("dwarf") == "cycle"

    assert reproductive_cycle.pattern_for_species("goblin") == "heat"
    assert reproductive_cycle.pattern_for_species("animal") == "heat"
    assert reproductive_cycle.pattern_for_species("frog") == "heat"
    assert reproductive_cycle.pattern_for_species("wolf") == "heat"

    assert reproductive_cycle.pattern_for_species("undead") == "none"
    assert reproductive_cycle.pattern_for_species("zombie") == "none"
    assert reproductive_cycle.pattern_for_species("ghost") == "none"
    assert reproductive_cycle.pattern_for_species("construct") == "none"


def test_eligibility_and_minor_exclusion():
    """Minors, males, and infertile characters are excluded from reproductive cycles."""
    world = _world()
    carrier, c_node = _character(world, "Carrier", age=25, species="human", sex="female")
    sire, s_node = _character(world, "Sire", age=28, species="human", sex="male")

    # Adult female human is eligible
    eligible, pattern = reproductive_cycle.is_eligible_for_cycle(carrier, world, c_node)
    assert eligible is True
    assert pattern == "cycle"

    # Male is not eligible
    eligible, _ = reproductive_cycle.is_eligible_for_cycle(sire, world, s_node)
    assert eligible is False

    # Minor is excluded
    c_node.properties["tags"] = ["female", "teen", "student"]
    eligible, _ = reproductive_cycle.is_eligible_for_cycle(carrier, world, c_node)
    assert eligible is False

    # Infertile tag is excluded
    c_node.properties["tags"] = ["female", "adult", "infertile"]
    eligible, _ = reproductive_cycle.is_eligible_for_cycle(carrier, world, c_node)
    assert eligible is False


def test_human_cycle_phases_and_conditions():
    """Human cycle moves through menstruating, follicular, ovulating, and luteal phases."""
    world = _world()
    carrier, c_node = _character(world, "Carrier", age=25, species="human", sex="female")

    # Initial update at tick 0 sets day 1 (menstruating)
    reproductive_cycle.update_cycle(carrier, world, c_node, reset_day_one=True)
    rc = carrier.reproductive_cycle
    assert rc is not None
    assert rc["pattern"] == "cycle"
    assert rc["phase"] == "menstruating"
    assert rc["day"] == 1
    assert "menstruating" in (carrier.conditions or {})
    fertile, _ = preg.is_fertile(carrier, world, c_node)
    assert fertile is False

    # Advance to ovulation window (day 14)
    ticks_per_day = reproductive_cycle.ticks_per_day(world)
    world.time_ticks = ticks_per_day * 13 + 10  # Day 14
    reproductive_cycle.update_cycle(carrier, world, c_node)
    rc = carrier.reproductive_cycle
    assert rc["day"] == 14
    assert rc["phase"] == "ovulating"
    assert "ovulating" in (carrier.conditions or {})
    assert "menstruating" not in (carrier.conditions or {})
    fertile, _ = preg.is_fertile(carrier, world, c_node)
    assert fertile is True

    # Advance to luteal phase (day 20)
    world.time_ticks = ticks_per_day * 19 + 10
    reproductive_cycle.update_cycle(carrier, world, c_node)
    rc = carrier.reproductive_cycle
    assert rc["day"] == 20
    assert rc["phase"] == "luteal"
    assert "ovulating" not in (carrier.conditions or {})
    fertile, _ = preg.is_fertile(carrier, world, c_node)
    assert fertile is False


def test_goblin_heat_phases_and_conditions():
    """Goblin cycles through anestrus, proestrus, in_heat, and metestrus."""
    world = _world()
    carrier, c_node = _character(world, "GobCarrier", age=20, species="goblin", sex="female")

    reproductive_cycle.update_cycle(carrier, world, c_node, reset_day_one=True)
    rc = carrier.reproductive_cycle
    assert rc["pattern"] == "heat"
    assert rc["phase"] == "anestrus"
    assert "in_heat" not in (carrier.conditions or {})
    fertile, _ = preg.is_fertile(carrier, world, c_node)
    assert fertile is False

    # Estrus window (days 12..14 in a 15-day cycle)
    ticks_per_day = reproductive_cycle.ticks_per_day(world)
    world.time_ticks = ticks_per_day * 12 + 10  # Day 13
    reproductive_cycle.update_cycle(carrier, world, c_node)
    rc = carrier.reproductive_cycle
    assert rc["day"] == 13
    assert rc["phase"] == "in_heat"
    assert "in_heat" in (carrier.conditions or {})
    fertile, _ = preg.is_fertile(carrier, world, c_node)
    assert fertile is True


def test_pregnancy_suspension_and_birth_resumption():
    """Pregnancy suspends cycle and clears conditions; birth resumes cycle at day 1."""
    world = _world()
    carrier, c_node = _character(world, "Carrier", age=25, species="human", sex="female")
    sire, s_node = _character(world, "Sire", age=28, species="human", sex="male")

    # Start at day 1, then advance to ovulation window (day 14)
    ticks_per_day = reproductive_cycle.ticks_per_day(world)
    world.time_ticks = 0
    reproductive_cycle.update_cycle(carrier, world, c_node, reset_day_one=True)
    world.time_ticks = ticks_per_day * 13 + 10
    reproductive_cycle.update_cycle(carrier, world, c_node)
    assert carrier.reproductive_cycle["phase"] == "ovulating"
    assert "ovulating" in carrier.conditions

    # Conceive
    success, reason = preg.attempt_conception(carrier, sire, world, bypass_willingness=True)
    assert success is True, reason
    assert carrier.reproductive_cycle["phase"] == "pregnant"
    assert "ovulating" not in (carrier.conditions or {})
    assert "menstruating" not in (carrier.conditions or {})

    # Deliver birth
    carrier.pregnancy["status"] = "term"
    child, birth_msg = preg.deliver_birth(carrier, world)
    assert child is not None, birth_msg
    assert carrier.reproductive_cycle["phase"] != "pregnant"
    assert carrier.reproductive_cycle["day"] == 1


def test_consent_and_willingness_boundaries_preserved():
    """Even during peak estrus (in_heat), pregnancy respects consent and boundaries."""
    world = _world()
    carrier, c_node = _character(world, "GobCarrier", age=20, species="goblin", sex="female")
    sire, s_node = _character(world, "GobSire", age=22, species="goblin", sex="male")

    ticks_per_day = reproductive_cycle.ticks_per_day(world)
    world.time_ticks = 0
    reproductive_cycle.update_cycle(carrier, world, c_node, reset_day_one=True)
    world.time_ticks = ticks_per_day * 12 + 10
    reproductive_cycle.update_cycle(carrier, world, c_node)
    assert "in_heat" in carrier.conditions

    # 1. Boundary check: character has boundary against pregnancy
    carrier.boundaries = ["pregnancy"]
    success, reason = preg.attempt_conception(carrier, sire, world, bypass_willingness=False)
    assert success is False
    assert "boundary" in reason.lower()

    # 2. Explicit unwilling check
    carrier.boundaries = []
    carrier.willing = False
    success, reason = preg.attempt_conception(carrier, sire, world, bypass_willingness=False)
    assert success is False
    assert "unwilling" in reason.lower()


def test_serialization_round_trip():
    """Player serialization preserves reproductive_cycle dict."""
    world = _world()
    p = Player("Tester")
    p.reproductive_cycle = {
        "pattern": "cycle",
        "species": "human",
        "phase": "ovulating",
        "day": 14,
        "length_days": 28,
        "fertile_window": [12, 16],
        "next_phase_tick": 2000,
        "anchor_tick": 0,
        "suspended": False,
    }

    serialized = world.serializer._serialize_player("Tester", p)
    assert "reproductive_cycle" in serialized
    assert serialized["reproductive_cycle"]["phase"] == "ovulating"

    restored = world.serializer._deserialize_player("Tester", serialized)
    assert restored.reproductive_cycle is not None
    assert restored.reproductive_cycle["day"] == 14
    assert restored.reproductive_cycle["phase"] == "ovulating"
    assert restored.reproductive_cycle["phase"] == "ovulating"


def test_kraktooth_and_millwood_content_verification():
    """Authored scenarios exercise cycle, heat, none, and minor exclusions."""
    # 1. Millwood: all 6 teens must be excluded
    with open("data/scenarios/Millwood.json", "r", encoding="utf-8") as f:
        millwood_data = json.load(f)
    mw_nodes = millwood_data.get("graph", {}).get("nodes", {})
    if isinstance(mw_nodes, dict):
        mw_node_list = list(mw_nodes.values())
    else:
        mw_node_list = mw_nodes

    minor_count = 0
    for n in mw_node_list:
        if n.get("type") == "character":
            p = Player(n.get("name"))
            p.gender = n.get("properties", {}).get("gender", "neutral")
            is_minor = bool(preg.minor_reason(p, n))
            if is_minor:
                minor_count += 1
    assert minor_count == 6

    # 2. Kraktooth: check adult goblin heat, adult human cycle, minor goblin exclusion, and zombie none
    with open("data/scenarios/kraktooth_goblin_camp.json", "r", encoding="utf-8") as f:
        krak_data = json.load(f)

    world = VirtualWorld()
    world.load_from_dict(krak_data)

    # Arix (12yo goblin teen) must be excluded
    arix_p = world.players.get("Arix")
    arix_node = world.graph.get_node(world._player_node_id("Arix"))
    assert preg.minor_reason(arix_p, arix_node) is not None
    eligible, _ = reproductive_cycle.is_eligible_for_cycle(arix_p, world, arix_node)
    assert eligible is False

    # Belne (18yo adult goblin female) has heat pattern
    belne_p = world.players.get("Belne")
    belne_node = world.graph.get_node(world._player_node_id("Belne"))
    eligible, pattern = reproductive_cycle.is_eligible_for_cycle(belne_p, world, belne_node)
    assert eligible is True
    assert pattern == "heat"
    assert reproductive_cycle.pattern_for_species(reproductive_cycle.resolve_species(belne_p, belne_node)) == "heat"

    # Leslie (adult human female) has cycle pattern
    leslie_p = world.players.get("Leslie")
    leslie_node = world.graph.get_node(world._player_node_id("Leslie"))
    eligible, pattern = reproductive_cycle.is_eligible_for_cycle(leslie_p, world, leslie_node)
    assert eligible is True
    assert pattern == "cycle"
    assert reproductive_cycle.pattern_for_species(reproductive_cycle.resolve_species(leslie_p, leslie_node)) == "cycle"

    # Zombie has none pattern
    zombie_p = world.players.get("zombie")
    zombie_node = world.graph.get_node(world._player_node_id("zombie"))
    if zombie_p and zombie_node:
        assert reproductive_cycle.pattern_for_species(reproductive_cycle.resolve_species(zombie_p, zombie_node)) == "none"
