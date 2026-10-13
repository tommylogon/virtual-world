"""MOSIAC context assembly (task-812).

The six letters of a character's decision context, read from real state: goals and
obligations and the schedule (the character's own mind) plus vitals and the clock
(the moment). Nothing is invented to fill a blank.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine import mosiac


class _Clock:
    """A minimal world: just enough clock for the schedule step."""
    time_ticks = 0

    def __init__(self, minutes):
        self._minutes = minutes

    def total_game_minutes(self):
        return self._minutes


def _clock_at(hh, mm=0):
    return _Clock(hh * 60 + mm)


def test_attention_flags_a_drive_and_a_depleted_meter_but_not_a_healthy_one():
    p = Player("Pip")
    p.vitals["Hunger"] = 80      # drive: high is the concern, salient
    p.vitals["Energy"] = 10      # depleting: low is the concern, salient
    p.vitals["Social"] = 90      # healthy

    needs = [n["need"] for n in mosiac.attention_of(p)]
    assert "hunger" in needs
    assert "energy" in needs
    assert "social" not in needs


def test_attention_is_empty_when_nothing_is_pressing():
    """A calm moment is a real answer, not a blank to fill."""
    assert mosiac.attention_of(Player("Calm")) == []


def test_assemble_reads_every_letter_from_real_state():
    p = Player("Pip")
    p.goals = [{"id": "become_chief", "what": "Become chief", "status": "active",
                "motivation": "I want respect", "intention": "so they stop pushing me"}]
    p.obligations = [{"id": "fetch_water", "charge": "Fetch water", "status": "accepted"},
                     {"id": "sing", "charge": "Sing", "status": "refused"}]
    p.schedule = [{"start": "08:00", "activity": "work", "area": "Forge"}]

    ctx = mosiac.assemble(_clock_at(8), p)

    assert ctx["character"] == "Pip"
    assert ctx["M"] == "I want respect"
    assert ctx["I"] == "so they stop pushing me"
    assert [o["id"] for o in ctx["O"]] == ["fetch_water"], "an answered obligation is not open"
    assert ctx["S"]["step"]["activity"] == "work"
    assert ctx["S"]["now"] == 480
    assert "free" in ctx["C"] and ctx["C"]["free"], "the always-available commands are offered"


def test_motivation_and_intention_fall_back_to_the_moment():
    p = Player("Pip")
    p.vitals["Thirst"] = 95
    p.schedule = [{"start": "06:00", "activity": "patrol", "area": "Gate"}]

    ctx = mosiac.assemble(_clock_at(12), p)

    assert ctx["M"] == "the need to satisfy thirst"      # no goal -> the top need
    assert ctx["I"] == "the schedule says patrol at Gate"  # no goal -> the schedule


def test_choices_drop_a_spent_tier():
    """A major slot already spent removes the major verbs from the set."""
    p = Player("Pip")
    p.turn_slots = {"major": 0, "minor": 1, "free": 3, "activity": 1}

    choices = mosiac.choices(p)

    assert "major" not in choices, "a spent major budget offers no major verbs"
    assert choices.get("free")
