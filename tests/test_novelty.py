"""Novelty recovery — Entertainment from fresh places, things and people (task-425).

Entertainment had no recurring source: an area paid +15 once ever, item discovery
paid +8 once ever, and nothing recreational existed, so it decayed to 0 within a
day and could never recover. Novelty is now a per-subject recovery curve read off
the observation memory, plus authored recreational fixtures.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine.novelty import (
    DEFAULT_RECOVERY_MINUTES,
    NOVELTY_MAX,
    freshness,
    grant,
    novelty_bonus,
    recovery_minutes,
)
from engine.runtime_config import DEFAULTS, SCHEMA


def seen(player, subject_id, tick):
    """Stamp a subject the way perception does."""
    player.record_observation(subject_id, f"You have seen {subject_id}.", tick,
                              kind="area", location="Here")


def test_never_seen_pays_full():
    p = Player("Cook")
    p.vitals = {"Entertainment": 0}
    assert freshness(p, "area_pantry", 500) == 1.0
    assert grant(p, "area_pantry", 500) == NOVELTY_MAX
    assert p.vitals["Entertainment"] == NOVELTY_MAX


def test_immediate_reentry_pays_nothing():
    """The whole point: the area you just left is not entertaining."""
    p = Player("Cook")
    p.vitals = {"Entertainment": 50}
    seen(p, "area_pantry", 100)

    assert freshness(p, "area_pantry", 100) == 0.0
    assert grant(p, "area_pantry", 100) == 0
    assert p.vitals["Entertainment"] == 50


def test_bouncing_between_two_areas_is_not_a_farm():
    """The window guard: a two-room bounce every 10 minutes pays nothing after
    the two first-ever sightings.

    (A linear ramp failed this — it trickled +1 a hop, 6/hour against
    Entertainment's 1.8/hour decay.)
    """
    p = Player("Cook")
    p.vitals = {"Entertainment": 0}
    gained = 0
    for hop in range(40):
        tick = hop * 10  # 400 minutes, one hop every 10
        subject = "area_a" if hop % 2 == 0 else "area_b"
        gained += grant(p, subject, tick)
        seen(p, subject, tick)

    assert gained == 2 * NOVELTY_MAX
    # A 10-minute gap is worth nothing at all.
    assert novelty_bonus(p, "area_a", 390) == 0
    assert freshness(p, "area_a", 390) < 0.01


def test_the_daily_budget_bounds_wide_roaming():
    """The budget guard: the window stops *bouncing*, but not *roaming*.

    With 31 areas a character revisits a given one only after about five hours,
    so every arrival is a fresh subject and the window pays on every hop — a fresh
    subject per action against 43/day of decay is unbounded. Measured with only
    the area subject paying and social switched off, a single day still pinned
    camp Entertainment at 81 average.
    """
    from engine.novelty import NOVELTY_DAILY_BUDGET, novelty_budget_remaining
    p = Player("Cook")
    p.vitals = {"Entertainment": 0}

    gained = 0
    for hop in range(40):
        tick = hop * 10
        subject = f"area_{hop}"
        gained += grant(p, subject, tick)
        seen(p, subject, tick)

    assert gained == NOVELTY_DAILY_BUDGET, "the day's novelty must be bounded"
    assert gained < 40 * NOVELTY_MAX
    assert novelty_budget_remaining(p, 400) == 0

    # A new in-game day restores the allowance.
    assert novelty_budget_remaining(p, 1440) == NOVELTY_DAILY_BUDGET
    assert grant(p, "area_fresh", 1440) == NOVELTY_MAX


def test_the_budget_is_reachable_at_any_tick_length():
    """A day is a day: the rollover uses game minutes, not ticks."""
    from engine.novelty import NOVELTY_DAILY_BUDGET, novelty_budget_remaining
    for minutes in (1, 15):
        p = Player("Cook")
        p.minutes_per_tick = minutes
        p.vitals = {"Entertainment": 0}
        grant(p, "area_a", 0)
        assert novelty_budget_remaining(p, 0) < NOVELTY_DAILY_BUDGET
        ticks_per_day = round(1440 / minutes)
        assert novelty_budget_remaining(p, ticks_per_day) == NOVELTY_DAILY_BUDGET


def test_a_stale_subject_pays_again_and_saturates():
    p = Player("Cook")
    p.vitals = {"Entertainment": 0}
    seen(p, "area_pantry", 0)

    # Half the window recovered, squared: a quarter of full novelty.
    half = grant(p, "area_pantry", DEFAULT_RECOVERY_MINUTES // 2)
    assert half == round(NOVELTY_MAX * 0.25)
    # At the window it is fully fresh again.
    assert grant(p, "area_pantry", DEFAULT_RECOVERY_MINUTES) == NOVELTY_MAX

    # Never *more* than full, however long the absence. Fresh character so the
    # day's budget is not what is limiting.
    q = Player("Cook2")
    q.vitals = {"Entertainment": 0}
    seen(q, "area_pantry", 0)
    assert novelty_bonus(q, "area_pantry", DEFAULT_RECOVERY_MINUTES * 10) == NOVELTY_MAX


def test_freshness_rises_monotonically_with_time_away():
    p = Player("Cook")
    seen(p, "area_pantry", 0)
    values = [freshness(p, "area_pantry", t)
              for t in (0, 30, 60, 90, 120, 240)]
    assert values == sorted(values)
    assert values[0] == 0.0 and values[-1] == 1.0


def test_homebody_is_never_entertained_by_a_new_place():
    p = Player("Homebody")
    p.vitals = {"Entertainment": 20}
    p.traits = {"homebody": True}
    assert novelty_bonus(p, "area_new", 0) == 0
    assert grant(p, "area_new", 0) == 0
    assert p.vitals["Entertainment"] == 20


def test_curious_gets_half_again():
    p = Player("Curious")
    p.vitals = {"Entertainment": 0}
    p.traits = {"curious": True}
    assert novelty_bonus(p, "area_new", 0) == int(NOVELTY_MAX * 1.5)


def test_wanderlust_reenchants_twice_as_fast():
    plain = Player("Plain")
    wanderer = Player("Wanderer")
    wanderer.traits = {"wanderlust": True}
    for p in (plain, wanderer):
        seen(p, "area_pantry", 0)

    tick = DEFAULT_RECOVERY_MINUTES // 2
    assert novelty_bonus(plain, "area_pantry", tick) == round(NOVELTY_MAX * 0.25)
    # Half the window in, a wanderlust character is already fully refreshed.
    assert novelty_bonus(wanderer, "area_pantry", tick) == NOVELTY_MAX


def test_no_entertainment_vital_means_no_grant():
    p = Player("Stoic")
    p.vitals = {"HP": 100}
    assert grant(p, "area_new", 0) == 0
    assert "Entertainment" not in p.vitals


def test_the_recovery_window_is_configurable():
    assert DEFAULTS["entertainment.novelty_recovery_minutes"] == DEFAULT_RECOVERY_MINUTES
    assert SCHEMA["entertainment.novelty_recovery_minutes"]["section"] == "entertainment"
    assert recovery_minutes() == float(DEFAULT_RECOVERY_MINUTES)


def test_a_bad_window_value_falls_back_instead_of_dividing_by_zero(monkeypatch):
    import engine.novelty as novelty_module
    monkeypatch.setattr(novelty_module.config, "get", lambda key, default=None: 0)
    assert novelty_module.recovery_minutes() > 0
    p = Player("Cook")
    seen(p, "area_pantry", 0)
    assert 0.0 <= freshness(p, "area_pantry", 10) <= 1.0


def test_the_recovery_window_is_the_same_game_time_at_any_tick_length():
    """The window is authored in game minutes but measured against tick deltas.

    Getting that conversion wrong is not subtle: dividing a 2-hour window by
    ticks at 15 min/tick makes it 30 hours, which silently stopped short-tick
    camps from re-earning novelty — it showed up as a 59-vs-89 Entertainment
    split between the 15 and 1 min/tick soaks.
    """
    for minutes in (1, 5, 15):
        p = Player("Cook")
        p.minutes_per_tick = minutes
        seen(p, "area_pantry", 0)

        half_window_ticks = round(DEFAULT_RECOVERY_MINUTES / 2 / minutes)
        full_window_ticks = round(DEFAULT_RECOVERY_MINUTES / minutes)

        # Half the window is a quarter of full novelty, whatever the tick.
        assert novelty_bonus(p, "area_pantry", half_window_ticks) == round(NOVELTY_MAX * 0.25), minutes
        # A full window is fully fresh again.
        assert novelty_bonus(p, "area_pantry", full_window_ticks) == NOVELTY_MAX, minutes


def test_the_tick_loop_keeps_a_characters_clock_in_step():
    """`minutes_per_tick` must follow the world, or the window is measured in
    the wrong unit after the tick length changes."""
    from app import create_app
    world = create_app({"TESTING": True}).world
    world.time_per_tick_minutes = 15
    name = world.active_player
    world.tick_turn()
    assert world.player_manager.get_player(name).minutes_per_tick == 15
