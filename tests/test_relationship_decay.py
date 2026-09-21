"""Relationship drift (player.decay_relationships + the per-day tick hook).

Closeness used to only ever move on an event: `last_interaction_tick` was
written in five places and read in none, so a pair that never met again kept its
value forever. Decay eases closeness toward 0 for bonds nobody maintains.

It has to be safe on authored data, so: the step never crosses zero, shared
history (`interaction_count`, which also drives `derive.familiarity`) damps the
rate, and an authored `label` is a declaration rather than a measurement and is
never touched.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from player import Player

AREA = "Blizzard Forest Clearing"


def _rel(closeness, count=0, label=""):
    return {"closeness": closeness, "last_interaction_tick": 0,
            "interaction_count": count, "label": label}


# ── arithmetic ───────────────────────────────────────────────────────────


def test_closeness_drifts_toward_zero():
    p = Player("A")
    p.relationships["B"] = _rel(20)
    p.decay_relationships(2, 0.5)          # 2 days at 0.5/day
    assert p.relationships["B"]["closeness"] == 19


def test_low_rates_accumulate_instead_of_rounding_away():
    """0.5/day must not round to nothing every day."""
    p = Player("A")
    p.relationships["B"] = _rel(20)
    for _ in range(4):
        p.decay_relationships(1, 0.5)      # 4 separate days
    assert p.relationships["B"]["closeness"] == 18


def test_negative_closeness_drifts_up_but_not_past_zero():
    p = Player("A")
    p.relationships["B"] = _rel(-20)
    p.decay_relationships(2, 0.5)
    assert p.relationships["B"]["closeness"] == -19


def test_decay_never_crosses_or_overshoots_zero():
    for start in (1, -1, 5, 100, -100):
        p = Player("A")
        p.relationships["B"] = _rel(start)
        p.decay_relationships(1000, 0.5)
        assert p.relationships["B"]["closeness"] == 0, start


def test_a_disabled_rate_changes_nothing():
    p = Player("A")
    p.relationships["B"] = _rel(30)
    assert p.decay_relationships(30, 0) == 0
    assert p.decay_relationships(0, 0.5) == 0
    assert p.relationships["B"]["closeness"] == 30


# ── protection of authored data ──────────────────────────────────────────


def test_shared_history_slows_the_drift():
    p = Player("A")
    p.relationships["Stranger"] = _rel(50, count=0)
    p.relationships["Old friend"] = _rel(50, count=6)
    p.decay_relationships(20, 0.5)
    stranger = p.relationships["Stranger"]["closeness"]
    familiar = p.relationships["Old friend"]["closeness"]
    assert familiar > stranger


def test_an_authored_label_is_never_touched():
    p = Player("A")
    p.relationships["B"] = _rel(40, label="my brother")
    p.decay_relationships(10, 0.5)
    assert p.relationships["B"]["label"] == "my brother"
    assert p.relationships["B"]["closeness"] == 35


def test_interaction_count_is_not_consumed():
    """It is a lifetime measure (familiarity), not a resource."""
    p = Player("A")
    p.relationships["B"] = _rel(40, count=3)
    p.decay_relationships(10, 0.5)
    assert p.relationships["B"]["interaction_count"] == 3


# ── the tick hook ────────────────────────────────────────────────────────


def _survive(world, player):
    """Keep the probe alive: a lone character outdoors freezes/starves in
    under a day, which would end the run before the day boundary arrives."""
    player.vitals.update({"Hunger": 20, "Thirst": 20, "Energy": 90,
                          "HP": 100, "Temperature": 37})
    player.conditions.pop("unconscious", None)
    if player.state == "dead":
        player.state = "awake"


def _run_days(minutes_per_tick, days):
    world = create_app({"TESTING": True}).world
    world.time_per_tick_minutes = minutes_per_tick
    p = Player("Hook")
    world.add_player(p)
    p.relationships["F"] = _rel(20)
    world.set_player_area("Hook", AREA)
    ticks = int(round(days * 1440 / minutes_per_tick))
    for _ in range(ticks + 2):
        world.tick_turn()
        _survive(world, p)
    return world.player_manager.players["Hook"].relationships["F"]["closeness"]


def test_the_hook_drifts_once_per_game_day():
    assert _run_days(5, 2) == 19      # 2 days x 0.5 = 1 point


def test_drift_is_independent_of_the_tick_length():
    """The hook keys off game days, not ticks, so a 15-minute world and a
    1-minute one must drift identically over the same game time."""
    slow = _run_days(1, 3)
    fast = _run_days(15, 3)
    assert slow == fast
