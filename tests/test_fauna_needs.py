"""Fauna (tag ``animal``) do not run the human social/sanity economy (task-399).

Before this, a bear, boar, wolf, frog, worg and raven each drained Social to 0,
took the ``social_breakdown`` condition, and dragged the camp's Social average
down. They have hunger, thirst, energy and temperature; they do not get lonely.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.vitals import is_animal
from player import Player

AREA = "Blizzard Forest Clearing"


class _Stub:
    def __init__(self, tags):
        self.tags = list(tags)


def test_is_animal_reads_the_tag():
    assert is_animal(_Stub(["male", "animal", "bear"]))
    assert is_animal(_Stub(["animal"]))
    assert not is_animal(_Stub(["male", "adult", "goblin"]))
    assert not is_animal(_Stub([]))


def test_animal_does_not_drain_social_sanity_or_entertainment():
    from app import create_app

    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    w.active_player = None
    p = Player("Bruin")
    w.add_player(p)
    p.current_area = AREA
    w.set_player_area("Bruin", AREA)
    p.simulation_mode = "background"
    p.next_due_tick = 0
    p.tags = ["male", "animal", "bear"]
    for stat in ("Social", "Sanity", "Entertainment"):
        p.vitals[stat] = 30
    p.vitals["Hunger"] = 5
    p.vitals["Thirst"] = 5
    p.vitals["Energy"] = 90

    for _ in range(15):
        w.tick_turn()

    # The social economy: fauna do not drain Social/Entertainment, nor take the
    # social_breakdown condition. (Sanity has environmental drivers that are out
    # of scope; the tick guards it separately.)
    assert p.vitals["Social"] >= 30, "an animal's Social drained"
    assert p.vitals["Entertainment"] >= 30, "an animal's Entertainment drained"
    assert "social_breakdown" not in p.conditions
