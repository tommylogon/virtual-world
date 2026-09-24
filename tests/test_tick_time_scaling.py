"""Vital decay must scale with the tick's game-time length.

Every rate in ``vital_rates`` is per in-game minute, but a tick is
``world.time_per_tick_minutes`` of game time — 1 by default, settable per
scenario and live from Engine Config. If decay is applied per tick without
scaling, a 15-minute world drains needs 15x too slowly and the clock and the
meters disagree with no error.

The load-bearing property is that **equal game time produces equal outcomes**,
whatever the tick length. These tests assert that, plus the individual pieces
that make it true.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from player import Player
from vital_rates import change, tick_minutes

AREA = "Blizzard Forest Clearing"


def _world(minutes_per_tick=1):
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    world.time_per_tick_minutes = minutes_per_tick
    return world


def _place(world, name):
    p = world.player_manager.players.get(name) or Player(name)
    if name not in world.player_manager.players:
        world.add_player(p)
    world.set_player_area(name, AREA)
    return p


def _empty_area(world, keep):
    """Send everyone else away so Social/environment effects are comparable."""
    for other in world.player_manager.players.values():
        if other is not keep and other.current_area == AREA:
            world.set_player_area(other.name, "Kitchen")


# ── the invariant ────────────────────────────────────────────────────────


def _energy_lost(minutes_per_tick, total_minutes, name):
    world = _world(minutes_per_tick=minutes_per_tick)
    p = _place(world, name)
    p.vitals["Energy"] = 100
    _empty_area(world, p)
    for _ in range(int(round(total_minutes / minutes_per_tick))):
        world.tick_turn()
    return 100 - p.vitals["Energy"]


def test_equal_game_time_gives_equal_decay():
    """120 in-game minutes is 120 minutes of decay, whether that is 120
    one-minute ticks or 24 five-minute ticks."""
    one_min = _energy_lost(1, 120, "Scaled A")
    five_min = _energy_lost(5, 120, "Scaled B")
    assert one_min > 0
    assert one_min == five_min, (one_min, five_min)


def test_scaling_holds_at_a_coarser_step():
    """15 minutes per tick is an unusual setting, not a special case."""
    one_min = _energy_lost(1, 180, "Scaled C")
    fifteen_min = _energy_lost(15, 180, "Scaled D")
    assert one_min == fifteen_min, (one_min, fifteen_min)


def test_unscaled_decay_would_have_been_wrong():
    """Guards the actual regression: 24 five-minute ticks must NOT behave like
    24 one-minute ticks (which is what the old per-tick code did)."""
    scaled = _energy_lost(5, 120, "Scaled E")
    unscaled_equivalent = _energy_lost(1, 24, "Scaled F")
    assert scaled > unscaled_equivalent * 3


# ── the pieces ───────────────────────────────────────────────────────────


def test_change_scales_with_minutes():
    # 0.25 is exact in binary, so the integer accumulator carries no float
    # noise and the assertion can be exact.
    p = Player("Unit")
    p.vitals["Energy"] = 100
    for _ in range(20):
        change(p, "Energy", -0.25, minutes=5)
    assert 100 - p.vitals["Energy"] == 25  # 0.25 x 5 x 20

    q = Player("Unit2")
    q.vitals["Energy"] = 100
    for _ in range(20):
        change(q, "Energy", -0.25, minutes=1)
    assert 100 - q.vitals["Energy"] == 5


def test_change_defaults_to_one_minute():
    """Existing callers that pass no `minutes` keep the per-minute behaviour."""
    p = Player("Default")
    p.vitals["Energy"] = 100
    for _ in range(10):
        change(p, "Energy", -1.0)
    assert 100 - p.vitals["Energy"] == 10


def test_tick_minutes_tolerates_junk():
    class W:
        def __init__(self, v):
            self.time_per_tick_minutes = v

    assert tick_minutes(W(15)) == 15
    assert tick_minutes(W(2.5)) == 2.5
    assert tick_minutes(W(-4)) == 4          # sign is a config typo, not intent
    assert tick_minutes(W(0)) == 1           # zero would freeze the sim
    assert tick_minutes(W(None)) == 1
    assert tick_minutes(W("nonsense")) == 1
    assert tick_minutes(W("12")) == 12


def test_condition_durations_are_game_minutes():
    """A 10-minute condition lasts 10 game minutes at any tick length.

    Durations used to count down one per tick, so a 5-minute unconsciousness
    lasted 75 minutes in a 15-minute world.
    """
    def ticks_until_expired(minutes_per_tick):
        world = _world(minutes_per_tick=minutes_per_tick)
        p = _place(world, "Conditioned")
        # `wet` is a plain timed condition; arousal-state ids are stripped every
        # tick while mature_content is off (player.py sync_vitals_with_tags).
        p.add_condition("wet", duration=10)
        assert "wet" in p.conditions, "fixture failed to apply the condition"
        for tick in range(1, 200):
            world.tick_turn()
            if "wet" not in p.conditions:
                return tick
        return None

    assert ticks_until_expired(1) == 10
    assert ticks_until_expired(5) == 2    # 10 minutes / 5 per tick
    assert ticks_until_expired(10) == 1


def test_starvation_grace_is_counted_in_minutes():
    """The grace is a wall-clock reprieve: 5-minute ticks must consume it 5x
    faster, or a 1-hour thirst grace becomes 15 hours."""
    world = _world(minutes_per_tick=5)
    p = _place(world, "Parched")
    p.vitals["Thirst"] = 100
    _empty_area(world, p)
    for _ in range(3):
        world.tick_turn()
    assert getattr(p, "_drive_maxed_thirst", 0) == pytest.approx(15)


def test_starvation_damage_is_per_minute():
    """Past the grace, a 5-minute tick deals 5 minutes of HP loss."""
    world = _world(minutes_per_tick=5)
    p = _place(world, "Starving")
    p.vitals["Thirst"] = 100
    p.vitals["HP"] = 100
    # Skip the 60-minute grace, then take one 5-minute tick of damage.
    p._drive_maxed_thirst = 60
    _empty_area(world, p)
    world.tick_turn()
    # 0.50 HP/min x 5 min = 2.5 -> rounded down to 2 by the int() on HP.
    assert p.vitals["HP"] == 98


# ── world advance soaks everyone (task-436 root cause) ───────────────────
#
# `process_due` gives a *focused* character `minutes_in_turn - 1` minutes of
# action time — zero at a 1-minute tick. `advance_world` has no attended actor,
# so unless it offloads everyone a fine-grained world advance decays every drive
# without ever serving it: the whole camp hits Energy 0, Thirst 78, Bladder 100
# after a day while a 15-minute world looks healthy. These tests pin the fix.

CAMP = Path(__file__).parent.parent / "data" / "scenarios" / "kraktooth_goblin_camp.json"
SOAK_VITALS = ("Energy", "Hunger", "Thirst", "Bladder", "Hygiene",
               "Entertainment", "Social", "Sanity", "HP")


def _camp_soak(minutes_per_tick, total_minutes):
    import json
    from engine import timeskip

    world = _world(minutes_per_tick=minutes_per_tick)
    with open(CAMP, encoding="utf-8-sig") as fh:
        world.load_from_dict(json.load(fh))
    world.time_per_tick_minutes = minutes_per_tick
    before = {p.name: p.simulation_mode for p in world.player_manager.players.values()}

    timeskip.advance_world(world, total_minutes)

    players = list(world.player_manager.players.values())
    after = {p.name: p.simulation_mode for p in players}
    mean = {v: sum(p.vitals.get(v, 0) for p in players) / len(players)
            for v in SOAK_VITALS}
    return mean, before, after


def test_world_advance_restores_simulation_modes():
    """A world advance soaks everyone for the span only."""
    _, before, after = _camp_soak(15, 60)
    assert before == after
    assert set(after.values()) == {"active"}


def test_two_day_world_advance_is_tick_length_independent():
    """Two in-game days give comparable outcomes at T=1 and T=15.

    Before the fix the T=1 camp ended at Energy 0 / Hunger 56 / Thirst 78 /
    Bladder 100 while T=15 sat near Energy 50 / Hunger 31 / Thirst 34 / Bladder 81.
    """
    one, _, _ = _camp_soak(1, 2 * 24 * 60)
    fifteen, _, _ = _camp_soak(15, 2 * 24 * 60)

    for vital in SOAK_VITALS:
        assert abs(one[vital] - fifteen[vital]) <= 15, (
            vital, one[vital], fifteen[vital])

    # The 1-minute world is hydrated, not merely alive.
    assert one["Energy"] > 40
    assert one["Hunger"] < 40
    assert one["Thirst"] < 50
    assert one["Bladder"] < 90
