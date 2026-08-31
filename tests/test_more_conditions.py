"""Task-190 conditions: wet, injured, bleeding, hypothermia, suffocating, petrified.

Covers catalog shapes, periodic drains (summed across instances), blocking
gates (can_act + movement), ends_on resolution, wet→insulation math, and
perception lines.
"""

import pytest

from graph import Edge, Node, EDGE_EQUIPPED, EDGE_CARRYING
from engine.node_ids import NodeIDHelper
from engine.conditions import effective_speed_mult, get_condition_mods
from engine.equipment_bonuses import aggregate_bonuses, effective_temperature
from virtual_world_engine import VirtualWorld


@pytest.fixture
def world():
    w = VirtualWorld()
    w.graph.add_node(Node(id=NodeIDHelper.area_node_id("Alpha"), type="area", name="Alpha", properties={}))
    w.set_player_area(next(iter(w.player_manager.players)), "Alpha")
    return w


def _p(world):
    name = next(iter(world.player_manager.players))
    return world.player_manager.players[name]


def _apply(world, cid, **kwargs):
    name = next(iter(world.player_manager.players))
    return world.conditions.apply_condition(name, cid, **kwargs)


def test_catalog_entries_present():
    from player import CONDITION_DEFINITIONS
    for cid in ("wet", "injured", "bleeding", "hypothermia", "suffocating", "petrified"):
        assert cid in CONDITION_DEFINITIONS
        d = CONDITION_DEFINITIONS[cid]
        for field in ("blocks_actions", "blocks_movement", "blocks_speech",
                      "attack_mod", "defense_mod", "speed_mult", "periodic",
                      "ends_on", "known", "symptoms", "stack"):
            assert field in d, f"{cid} missing {field}"


def test_bleeding_drains_hp_scaled(world):
    p = _p(world)
    p.vitals["HP"] = 100
    _apply(world, "bleeding", level=2)
    world.conditions.process_tick()
    assert p.vitals["HP"] == 98
    # two bleeding instances (stacked) drain twice
    _apply(world, "bleeding", level=1)
    world.conditions.process_tick()
    assert p.vitals["HP"] == 95  # 98 - 2 - 1


def test_injured_levels_modify_speed_and_hp(world):
    p = _p(world)
    p.vitals["HP"] = 50
    _apply(world, "injured", level=3)
    assert effective_speed_mult("injured", p.conditions["injured"]) == 0.5
    world.conditions.process_tick()
    assert p.vitals["HP"] == 47  # level 3 → -3 HP/tick (catalog)


def test_injured_ends_on_fix(world):
    p = _p(world)
    _apply(world, "injured", level=2)
    assert p.has_condition("injured")
    removed = world.conditions.end_conditions(next(iter(world.player_manager.players)), "fix")
    assert any(cid == "injured" for cid, _src in removed)
    assert not p.has_condition("injured")


def test_hypothermia_drains_energy(world):
    p = _p(world)
    p.vitals["Energy"] = 50
    _apply(world, "hypothermia", level=2)
    world.conditions.process_tick()
    assert p.vitals["Energy"] == 48


def test_suffocating_blocks_actions_and_movement(world):
    name = next(iter(world.player_manager.players))
    _apply(world, "suffocating", duration=4)
    assert not world.conditions.can_act(name)
    from player import BLOCKING_CONDITIONS
    assert "suffocating" in BLOCKING_CONDITIONS
    with pytest.raises(ValueError, match="suffocating"):
        world.move_to_area("north")
    # still perceived as a symptom (unknown → symptom line)
    from engine.conditions import perceived_conditions
    lines = perceived_conditions(_p(world))
    assert any("burning" in line.lower() or "air" in line.lower() for line in lines)


def test_petrified_blocks_and_tough(world):
    name = next(iter(world.player_manager.players))
    _apply(world, "petrified")
    assert not world.conditions.can_act(name)
    mods = get_condition_mods(_p(world))
    assert mods["defense_mod"] == 5
    with pytest.raises(ValueError, match="petrified"):
        world.move_to_area("north")


def test_wet_reduces_insulation(world):
    name = next(iter(world.player_manager.players))
    p = _p(world)
    pname = world.player_manager.get_player_node_id(name)
    coat = Node(id="item_coat", type="item", name="Winter Coat",
                properties={"tags": ["clothing"], "insulation": 10, "equip_slots": ["torso"]})
    world.graph.add_node(coat)
    world.graph.add_edge(Edge(source=coat.id, target=pname, type=EDGE_EQUIPPED))
    dry = aggregate_bonuses(p, world.graph)["insulation"]
    assert dry == 10
    _apply(world, "wet", level=1)
    wet = aggregate_bonuses(p, world.graph)["insulation"]
    assert wet == 6  # 60% kept at level 1
    assert effective_temperature(-10, aggregate_bonuses(p, world.graph)) > -10


def test_symptoms_staging_for_hypothermia(world):
    p = _p(world)
    _apply(world, "hypothermia", level=2, symptoms=None)
    from engine.conditions import symptom_for
    inst = p.conditions["hypothermia"][0]
    assert "shaking" in symptom_for("hypothermia", inst)
    inst["level"] = 3
    assert "sleepy" in symptom_for("hypothermia", inst)
    inst["level"] = 1
    assert "shuddering" in symptom_for("hypothermia", inst).lower()
