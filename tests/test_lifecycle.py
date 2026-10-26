"""Aging and lifecycle (task-735): birth ticks, stages, old-age death.

The clock is sim ticks (world.time_ticks), not wall time.
Pregnancy and birth ride a follow-up card - this file covers the
clock, the stages, and death.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from player import Player

from engine import lifecycle as lc


YEAR_TICKS = 518400 // 5  # default calendar, 5 min per tick


def _year_ticks(world):
    """Ticks per game-year for THIS world (bare test worlds tick 1 min)."""
    per_tick = float(getattr(world, "time_per_tick_minutes", 5) or 5)
    return int(lc.minutes_per_year(world) / per_tick)


def _world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Kitchen", "A test kitchen.", []))
    return world


def _character(world, name="Arix"):
    player = Player(name)
    world.add_player(player)
    world.set_player_area(name, "Kitchen")
    return player


def _node(world, name="Arix"):
    return world.graph.get_node(world._player_node_id(name))


def test_authored_age_resolves_a_birth_tick_once():
    world = _world()
    _character(world)
    node = _node(world)
    from engine import character_appearance as ca
    ca.set_record(node, {"identity": {"age": 30}})
    player = world.player_manager.get_player("Arix")
    assert player.birth_tick is None
    assert lc.age_years(player, world, node) == 30
    assert player.birth_tick is not None
    # Resolving again does not move the tick.
    before = player.birth_tick
    assert lc.age_years(player, world, node) == 30
    assert player.birth_tick == before


def test_ageless_character_stays_ageless():
    world = _world()
    _character(world)
    player = world.player_manager.get_player("Arix")
    assert lc.age_years(player, world, _node(world)) is None
    assert lc.life_stage(None) is None
    assert lc.on_clock(world) == []


def test_life_stage_thresholds():
    assert lc.life_stage(5) == "child"
    assert lc.life_stage(12.9) == "child"
    assert lc.life_stage(13) == "adolescent"
    assert lc.life_stage(17.9) == "adolescent"
    assert lc.life_stage(18) == "adult"
    assert lc.life_stage(59.9) == "adult"
    assert lc.life_stage(60) == "elder"
    assert lc.life_stage(200) == "elder"


def test_stage_transition_emits_an_event():
    world = _world()
    _character(world)
    node = _node(world)
    from engine import character_appearance as ca
    ca.set_record(node, {"identity": {"age": 12}})
    player = world.player_manager.get_player("Arix")
    assert lc.age_years(player, world, node) == 12
    events = lc.on_clock(world)
    assert player.life_stage == "child"
    # Cross into adolescence: 5 game-years of ticks.
    world.time_ticks += 5 * _year_ticks(world)
    events = lc.on_clock(world)
    assert player.life_stage == "adolescent"
    assert any("adolescent" in e for e in events)


def test_mortality_never_before_lifespan():
    world = _world()
    _character(world)
    player = world.player_manager.get_player("Arix")
    assert lc.mortality_roll(player, 79.9, 80, rng=lambda: 0.0) is False


def test_old_age_can_kill_and_is_yearly():
    world = _world()
    _character(world)
    node = _node(world)
    from engine import character_appearance as ca
    ca.set_record(node, {"identity": {"age": 90}})
    player = world.player_manager.get_player("Arix")
    assert lc.age_years(player, world, node) == 90
    # rng 1.0 never kills, but the year is still recorded (once/year).
    lc.on_clock(world, rng=lambda: 1.0)
    assert player.state != "dead"
    first_year = player.last_mortality_year
    assert first_year is not None
    lc.on_clock(world, rng=lambda: 0.0)
    assert player.state != "dead"  # same year: no second roll
    assert player.last_mortality_year == first_year
    # Next year, rng 0.0 kills.
    world.time_ticks += _year_ticks(world) + 1
    events = lc.on_clock(world, rng=lambda: 0.0)
    assert player.state == "dead"
    assert any("old age" in e for e in events)


def test_advance_age_moves_the_clock_too():
    world = _world()
    _character(world)
    node = _node(world)
    from engine import character_appearance as ca
    ca.set_record(node, {"identity": {"age": 30}})
    player = world.player_manager.get_player("Arix")
    assert lc.age_years(player, world, node) == 30
    world.effects.execute("advance_age", {"years": 5, "target": "Arix"},
                          {"actor": "Arix"}, game_state=world)
    assert ca.identity(node)["age"] == 35
    assert lc.age_years(player, world, node) == 35


def test_lifecycle_fields_round_trip_saves():
    world = _world()
    _character(world)
    player = world.player_manager.get_player("Arix")
    player.birth_tick = 1000
    player.life_stage = "adult"
    player.last_mortality_year = 3
    data = world.to_dict()
    players = {p["name"]: p for p in data["players"]} \
        if isinstance(data.get("players"), list) \
        else data.get("players", {})
    assert players["Arix"]["birth_tick"] == 1000
    assert players["Arix"]["life_stage"] == "adult"


def test_clock_advance_ages_the_cast():
    """The tick path runs lifecycle: bulk jumps land on the true stage."""
    world = _world()
    _character(world)
    node = _node(world)
    from engine import character_appearance as ca
    ca.set_record(node, {"identity": {"age": 12}})
    player = world.player_manager.get_player("Arix")
    assert lc.age_years(player, world, node) == 12
    world.tick_manager.advance_clock(6 * _year_ticks(world))
    assert player.life_stage == "adult"
    assert lc.age_years(player, world, node) == 18


def test_birthday_dd_mm_yyyy_resolves_birth_tick_and_recalculates_on_force():
    world = _world()
    _character(world)
    node = _node(world)
    from engine import character_appearance as ca
    ca.set_record(node, {"identity": {"birthday": "14.03.1998", "age": 28}})
    player = world.player_manager.get_player("Arix")
    bt = lc.ensure_birth_tick(player, world, node)
    assert bt is not None
    assert bt < 0
    st = lc.status(player, world, node)
    assert st["birthday"] == "14.03.1998"
    assert st["birth_tick"] == bt
    # On Jan 1 (day 1, month 1), a March 14 birthday is ~0.2 years away from turning 28
    assert 27.5 <= st["age"] <= 28.0

    # Updating age/birthday and calling ensure_birth_tick(..., force=True) moves birth_tick
    ca.set_record(node, {"identity": {"birthday": "01.01.1990", "age": 36}})
    bt_updated = lc.ensure_birth_tick(player, world, node, force=True)
    assert bt_updated < bt
    assert lc.age_years(player, world, node) == 36

