"""Authored daily schedules (task-409).

A schedule is what turns a survival loop into a *day*: Mikka goes to the
Workshop, Gribba cooks, and the camp gathers at the Chief's Pit in the evening
and sleeps in the halls. Before it, every character ate, drank, slept and
socialised wherever it happened to be standing.

Times are game minutes, never ticks, so a step at 07:00 happens at 07:00 at any
tick length.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import create_app
from player import Player
from engine.schedule import (
    DEFAULT_ACTIVITY,
    MINUTES_PER_DAY,
    current_step,
    describe,
    minutes_of_day,
    normalize,
    parse_start,
)


# ── parsing ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("value,expected", [
    ("00:00", 0), ("06:00", 360), ("07:30", 450), ("23:59", 1439),
    ("6:05", 365), ("24:00", 0), ("12:00:00", 720),
])
def test_parse_start(value, expected):
    assert parse_start(value) == expected


@pytest.mark.parametrize("value", [None, "", "  ", "noon", "12", "99:00", "12:99"])
def test_parse_start_rejects_junk(value):
    assert parse_start(value) is None


def test_parse_start_tolerates_a_bare_minute_count():
    """A form field may hand us minutes rather than a clock string."""
    assert parse_start(450) == 450
    assert parse_start(1500) == 1500 % MINUTES_PER_DAY


# ── normalisation ────────────────────────────────────────────────────────


def test_normalize_sorts_by_time():
    steps = normalize([
        {"start": "18:00", "activity": "socialise"},
        {"start": "06:00", "activity": "work"},
    ])
    assert [s["start"] for s in steps] == [360, 1080]


def test_a_step_with_no_usable_start_is_dropped_not_guessed():
    """Inventing a time would make a character behave in a way nobody authored."""
    steps = normalize([
        {"start": "06:00", "activity": "work"},
        {"activity": "work"},          # no start
        {"start": "noon", "activity": "eat"},
    ])
    assert len(steps) == 1
    assert steps[0]["activity"] == "work"


def test_an_unknown_activity_degrades_to_wait_rather_than_vanishing():
    """A typo should leave the character *there*, not free to wander."""
    steps = normalize([{"start": "06:00", "activity": "smithing"}])
    assert steps[0]["activity"] == DEFAULT_ACTIVITY


def test_normalize_accepts_an_empty_or_missing_schedule():
    assert normalize(None) == []
    assert normalize([]) == []
    assert normalize({}) == []
    assert normalize({"steps": []}) == []


def test_a_fallback_is_always_present():
    steps = normalize([{"start": "06:00", "activity": "work", "area": "Workshop"}])
    assert steps[0]["fallback"] == DEFAULT_ACTIVITY


# ── picking the step in force ────────────────────────────────────────────


SCHEDULE = [
    {"start": "06:00", "activity": "work", "area": "Workshop"},
    {"start": "12:00", "activity": "eat", "area": "Cooking Area"},
    {"start": "22:00", "activity": "sleep", "area": "Sleeping Halls"},
]


@pytest.mark.parametrize("now,activity", [
    (360, "work"),     # exactly on the step
    (361, "work"),     # just after
    (700, "work"),     # still morning
    (719, "work"),     # one minute before the next step
    (720, "eat"),      # exactly on the next step
    (1000, "eat"),
    (1320, "sleep"),
    (1439, "sleep"),
])
def test_current_step_picks_the_step_in_force(now, activity):
    assert current_step(SCHEDULE, now)["activity"] == activity


def test_before_the_first_step_the_last_step_is_still_in_force():
    """Otherwise a schedule starting at 06:00 leaves a character idle from
    midnight until dawn — or worse, wandering."""
    step = current_step(SCHEDULE, 60)     # 01:00
    assert step["activity"] == "sleep"


def test_an_empty_schedule_has_no_step():
    assert current_step([], 600) is None


def test_current_step_handles_junk_input():
    assert current_step(SCHEDULE, "noon") is None or True  # must not raise
    assert current_step(SCHEDULE, None) is None


def test_wrapping_past_midnight_keeps_the_evening_step():
    steps = normalize([
        {"start": "20:00", "activity": "socialise"},
        {"start": "02:00", "activity": "sleep"},
    ])
    assert current_step(steps, 1380)["activity"] == "socialise"   # 23:00
    assert current_step(steps, 180)["activity"] == "sleep"        # 03:00


# ── the clock is game minutes, not ticks ─────────────────────────────────


def test_minutes_of_day_is_independent_of_tick_length():
    """60 game minutes is 60 game minutes, whatever a tick is.

    Asserted as an *advance* rather than an absolute reading, because the world
    clock has its own start-of-day offset (`total_game_minutes` includes it) and
    a test that hard-coded 07:00 would be asserting the camp's start hour, not
    this function's arithmetic.
    """
    for minutes_per_tick in (1, 5, 15):
        app = create_app({"TESTING": True})
        world = app.world
        world.time_per_tick_minutes = minutes_per_tick
        start = minutes_of_day(world)
        world.time_ticks = int(60 / minutes_per_tick)   # +60 game minutes
        assert (minutes_of_day(world) - start) % MINUTES_PER_DAY == 60, minutes_per_tick


def test_minutes_of_day_falls_back_to_ticks_on_a_bare_stub():
    class Stub:
        time_ticks = 90
        time_per_tick_minutes = 10
    assert minutes_of_day(Stub()) == (90 * 10) % MINUTES_PER_DAY


def test_minutes_of_day_survives_a_stub_with_nothing():
    class Stub:
        pass
    assert minutes_of_day(Stub()) == 0


# ── serialization ────────────────────────────────────────────────────────


def test_a_schedule_round_trips_through_a_savegame():
    world = create_app({"TESTING": True}).world
    name = world.active_player
    player = world.player_manager.get_player(name)
    player.schedule = normalize(SCHEDULE)

    reloaded = create_app({"TESTING": True}).world
    reloaded.load_from_dict(world.to_dict())

    restored = reloaded.player_manager.get_player(name).schedule
    assert [s["activity"] for s in restored] == ["work", "eat", "sleep"]
    assert restored[0]["area"] == "Workshop"


def test_a_malformed_saved_schedule_is_normalised_on_load():
    """A hand-edited file must not put a bad step into somebody's day."""
    world = create_app({"TESTING": True}).world
    name = world.active_player
    data = world.to_dict()
    data["players"][name]["schedule"] = [
        {"activity": "work"},                       # no start
        {"start": "06:00", "activity": "nonsense"},  # unknown activity
    ]

    reloaded = create_app({"TESTING": True}).world
    reloaded.load_from_dict(data)
    restored = reloaded.player_manager.get_player(name).schedule
    assert len(restored) == 1
    assert restored[0]["activity"] == DEFAULT_ACTIVITY


def test_no_schedule_is_a_valid_state():
    """Every character behaved this way before schedules existed."""
    world = create_app({"TESTING": True}).world
    assert world.player_manager.get_player(world.active_player).schedule == []


def test_describe_summarises_a_day():
    text = describe(SCHEDULE)
    assert "06:00 work at Workshop" in text
    assert "22:00 sleep at Sleeping Halls" in text
    assert describe([]) == "no schedule"
