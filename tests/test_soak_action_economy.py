"""The soak spends the action economy (task-352 slice 5).

The background/soak flow (`BackgroundSimulation.process_due`) fills a minute
timeframe, but the composition of that turn is bounded by the SAME per-turn
budget an attended character gets (`engine/action_tiers.DEFAULT_BUDGET`). Travel
is a move: the turn's first hop is the major, a later one the minor.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player  # noqa: E402

AREA = "Blizzard Forest Clearing"


def _world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _bg_player(world, name="BudgetGoblin", area=AREA, **vitals):
    p = Player(name)
    world.add_player(p)
    p.current_area = area
    world.set_player_area(name, area)
    p.simulation_mode = "background"
    p.next_due_tick = 0
    for k, v in vitals.items():
        p.vitals[k] = v
    return p


def test_background_task_tiers():
    from engine.background_simulation import BackgroundSimulation as BGS
    tier = BGS._task_tier
    assert tier("travel", 0) == "major", "the first hop of a turn is the go"
    assert tier("travel", 1) == "minor", "a later hop is the second go"
    assert tier("eat", 0) == "major"
    assert tier("drink", 0) == "major"
    assert tier("forage", 0) == "major"
    assert tier("wash", 0) == "minor"
    assert tier("sleep", 0) == "activity"
    assert tier("recuperate", 0) == "activity"
    # An unclassified task is budgeted, never silently free.
    assert tier("some_new_task", 0) == "major"


def test_a_soak_turn_is_bounded_by_the_action_budget():
    """A background character cannot out-action the budget, however long the turn.

    Feed the loop an endless stream of one-minute travel steps: without the
    economy a 15-minute turn is fifteen steps. With it, travel is the turn's
    major hop and then its minor — two — and the third step is unaffordable.
    """
    from engine.background_simulation import BackgroundSimulation
    from engine import action_tiers as at

    w = _world()
    w.time_per_tick_minutes = 15
    p = _bg_player(w, Thirst=50, Hunger=50, Energy=90)
    bgs = BackgroundSimulation(w)

    steps = []

    def endless_travel(name, player, served=None, remaining=None):
        if name != p.name or not remaining or remaining < 1:
            return None
        steps.append(round(remaining, 2))
        return (1.0, "travel")

    bgs._act = endless_travel
    bgs.process_due()

    budget = at.DEFAULT_BUDGET
    # Two moves were paid (major + minor); the third call is refused and breaks
    # the loop. Without the cap this would be `minutes_in_turn` (15) steps.
    assert p.turn_slots.get("major", 0) == 0, p.turn_slots
    assert p.turn_slots.get("minor", 0) == 0, p.turn_slots
    assert len(steps) < w.time_per_tick_minutes, f"took {len(steps)} steps at T=15"
    assert len(steps) == 3, f"took {len(steps)} steps (two paid, one refused)"
    # The free and activity slots are untouched by a move.
    assert p.turn_slots.get("free", 0) == budget["free"]
    assert p.turn_slots.get("activity", 0) == budget["activity"]


def test_a_quiet_soak_character_still_spends_nothing():
    """The budget is a ceiling, not a quota: nothing due means nothing spent."""
    from engine.background_simulation import BackgroundSimulation
    from engine import action_tiers as at

    w = _world()
    w.time_per_tick_minutes = 15
    p = _bg_player(w, Thirst=5, Hunger=5, Energy=95)
    bgs = BackgroundSimulation(w)
    bgs.process_due()
    assert p.turn_slots == at.DEFAULT_BUDGET, p.turn_slots
