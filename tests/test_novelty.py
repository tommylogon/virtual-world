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


def test_bouncing_between_two_areas_earns_far_less_than_a_fresh_route():
    """The farm guard, as task-425 states it: repeatedly entering the same area
    must produce far less Entertainment than a fresh route over the same time.

    A linear ramp failed this — a two-room bounce every 10 minutes trickled +1 a
    hop, 6/hour against Entertainment's 1.8/hour decay.
    """
    bouncer = Player("Bouncer")
    wanderer = Player("Wanderer")
    bouncer.vitals = {"Entertainment": 0}
    wanderer.vitals = {"Entertainment": 0}

    bounce_gained = 0
    fresh_gained = 0
    for hop in range(40):
        tick = hop * 10  # 400 minutes, one hop every 10
        subject = "area_a" if hop % 2 == 0 else "area_b"
        bounce_gained += grant(bouncer, subject, tick)
        seen(bouncer, subject, tick)

        fresh = f"area_{hop}"
        fresh_gained += grant(wanderer, fresh, tick)
        seen(wanderer, fresh, tick)

    assert bounce_gained < fresh_gained / 5
    # A 10-minute gap is worth nothing at all: area_a was last seen at 380 on the
    # final hop, so a 390 check is the bounce case exactly.
    assert novelty_bonus(bouncer, "area_a", 390) == 0
    assert freshness(bouncer, "area_a", 390) < 0.01


def test_a_stale_subject_pays_again_and_saturates():
    p = Player("Cook")
    p.vitals = {"Entertainment": 0}
    seen(p, "area_pantry", 0)

    # Half the window recovered, squared: a quarter of full novelty.
    half = grant(p, "area_pantry", DEFAULT_RECOVERY_MINUTES // 2)
    assert half == round(NOVELTY_MAX * 0.25)

    # At the window it is fully fresh again — and no fresher.
    assert grant(p, "area_pantry", DEFAULT_RECOVERY_MINUTES) == NOVELTY_MAX
    assert novelty_bonus(p, "area_pantry", DEFAULT_RECOVERY_MINUTES * 10) == NOVELTY_MAX


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
