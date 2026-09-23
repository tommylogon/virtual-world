"""Sanity has sources, and the conditions no longer lock it at 0 (task-432).

Sanity had five drains and **no source**. A week emptied an authored 65-90
(baseline alone is 7.2/day), so every one of the 23 characters ended a soak
hallucinating — and because `hallucinating` itself drained Sanity at -2/min
(400x the baseline, -2880/day) a character who reached it could never climb back
out however well they lived.

The fix is in three parts: the conditions stop draining the meter that causes
them, sleep/rest/meditation become real sources, and company steadies the mind as
the mirror of the existing isolation penalty.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import create_app
from player import Player
from engine.activities import ACTIVITY_REGEN
from engine.background_simulation import SANITY_REST_MINUTES
from engine.conditions import condition_definition, effective_periodic_for
from vital_rates import (
    BASELINE_DECAY,
    SANITY_COMPANY_GAIN,
    SANITY_COMPANY_MIN_SOCIAL,
)

AREA = "Verdant Hollow"


def _world(minutes_per_tick=1):
    world = create_app({"TESTING": True}).world
    world.time_per_tick_minutes = minutes_per_tick
    world.movement.add_area(__import__("area").Area(AREA, "A hollow.", []))
    return world


# ── the self-lock is gone ────────────────────────────────────────────────


@pytest.mark.parametrize("condition", ["hallucinating", "social_breakdown"])
def test_a_breakdown_condition_does_not_drain_sanity(condition):
    """It used to drain the meter that caused it, which made it permanent."""
    periodic = condition_definition(condition).get("periodic") or {}
    assert "Sanity" not in periodic, (
        f"{condition} drains Sanity again — a condition that suppresses what "
        f"causes it can only maintain itself"
    )


def test_the_conditions_still_cost_something():
    """Removing the drain must not make them free: the behavioural penalty is
    the cost."""
    for condition in ("hallucinating", "social_breakdown"):
        spec = condition_definition(condition)
        assert spec.get("attack_mod", 0) < 0 or spec.get("auto_fail_checks")
        assert spec.get("ends_on"), "a condition with no way out is a trap"


def test_effective_periodic_reports_no_sanity_for_those_conditions():
    for condition in ("hallucinating", "social_breakdown"):
        periodic = effective_periodic_for(condition, {})
        assert periodic.get("Sanity", 0) == 0, condition


def test_sanity_never_drains_hp():
    """Deliberate: low Sanity makes a character dangerous, not dead."""
    for condition in ("hallucinating", "social_breakdown"):
        assert "HP" not in (condition_definition(condition).get("periodic") or {})


# ── the sources ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("activity", ["sleeping", "resting", "meditating"])
def test_restorative_activities_restore_sanity(activity):
    assert ACTIVITY_REGEN[activity].get("Sanity", 0) > 0, activity


def test_sleep_is_the_strongest_source():
    """A night is the main way a character recovers its mind — by *total*, not by
    rate: resting is a more concentrated but much shorter block."""
    per_night = ACTIVITY_REGEN["sleeping"]["Sanity"] * 60 * 8      # 8 hours
    per_rest = ACTIVITY_REGEN["resting"]["Sanity"] * SANITY_REST_MINUTES
    assert per_night > per_rest
    # A night must also exceed the passive daily drain, or nobody recovers.
    assert per_night > BASELINE_DECAY["Sanity"] * 1440


def test_the_sleep_rate_does_not_peg_the_whole_camp():
    """The first attempt at 0.10/min restored so much that every character sat
    at 100 within a week, which makes the meter inert."""
    per_night = ACTIVITY_REGEN["sleeping"]["Sanity"] * 60 * 8
    assert per_night < 30, "sleep alone should not be a full refill"


def test_company_steadies_the_mind_mirroring_the_isolation_penalty():
    assert SANITY_COMPANY_GAIN > 0
    assert 0 < SANITY_COMPANY_MIN_SOCIAL <= 100


def test_company_gain_is_smaller_than_the_passive_drain():
    """It is a steadying influence, not a source on its own — otherwise merely
    standing in a crowd would be enough and rest would not matter."""
    assert SANITY_COMPANY_GAIN < BASELINE_DECAY["Sanity"]


# ── the background rest step ─────────────────────────────────────────────


def test_a_low_sanity_character_rests():
    from engine.background_simulation import BackgroundSimulation, SANITY_THRESHOLD
    world = _world(minutes_per_tick=15)
    p = Player("Wretch")
    world.add_player(p)
    world.set_player_area("Wretch", AREA)
    p.current_area = AREA
    p.simulation_mode = "background"
    p.vitals.update({"Sanity": SANITY_THRESHOLD - 1, "Hunger": 0, "Thirst": 0,
                     "Energy": 100, "Bladder": 0, "Hygiene": 100,
                     "Entertainment": 100})
    sim = BackgroundSimulation(world)

    sim._act("Wretch", p)

    assert p.activity and p.activity["type"] == "resting"
    # Bounded, because `_act` skips anyone mid-activity and a sprawling rest
    # would stop them eating.
    assert p.activity["duration_ticks"] == 4  # 60 minutes at 15 min/tick


def test_the_rest_duration_is_expressed_in_game_minutes():
    from engine.background_simulation import BackgroundSimulation, SANITY_REST_MINUTES
    for minutes in (1, 15):
        world = _world(minutes_per_tick=minutes)
        p = Player("Wretch")
        world.add_player(p)
        world.set_player_area("Wretch", AREA)
        p.current_area = AREA
        p.vitals.update({"Sanity": 10, "Energy": 100})
        sim = BackgroundSimulation(world)
        sim._recuperate(p)
        expected = max(1, round(SANITY_REST_MINUTES / minutes))
        assert p.activity["duration_ticks"] == expected, minutes


def test_a_healthy_character_does_not_rest():
    from engine.background_simulation import BackgroundSimulation
    world = _world()
    p = Player("Wretch")
    world.add_player(p)
    world.set_player_area("Wretch", AREA)
    p.current_area = AREA
    p.vitals.update({"Sanity": 90, "Hunger": 0, "Thirst": 0, "Energy": 100,
                     "Bladder": 0, "Hygiene": 100, "Entertainment": 100})
    sim = BackgroundSimulation(world)
    sim._act("Wretch", p)
    assert p.activity is None


def test_recuperate_will_not_interrupt_an_existing_activity():
    from engine.background_simulation import BackgroundSimulation
    world = _world()
    p = Player("Wretch")
    world.add_player(p)
    world.set_player_area("Wretch", AREA)
    p.current_area = AREA
    p.vitals["Sanity"] = 10
    p.activity = {"type": "sleeping", "started_at_tick": 0}
    sim = BackgroundSimulation(world)
    assert sim._recuperate(p) is False
    assert p.activity["type"] == "sleeping"
