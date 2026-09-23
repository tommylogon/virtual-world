"""Skill-driven search finds (task-471).

A search's yield depends on the skill used and the area: Survival finds plants
and game, History old things, Religion relics; a forest favours Survival and a
ruin favours History/Religion, and an area with no such tag yields nothing.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from player import Player
from engine import foraging
from engine.background_simulation import BackgroundSimulation, TASK_MINUTES

FORAGE_TAGS = {"herb", "medicinal", "berry", "fruit", "food", "root",
               "grub", "bait", "bug"}


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _area(w, name, tags):
    w.movement.add_area(Area(name, "test area", []))
    node = w.graph.get_node(w.area_node_id(name))
    node.properties["tags"] = list(tags)
    return name


def _searcher(w, area, **skills):
    p = Player("Vekka")
    w.add_player(p)
    p.current_area = area
    w.set_player_area("Vekka", area)
    p.skills.update(skills)
    p.vitals.update({"Hunger": 0, "Thirst": 0, "Energy": 100, "Bladder": 0})
    return p


def test_survival_search_in_a_forest_finds_a_forage_item():
    w = _world()
    area = _area(w, "Test Woods", ["forest"])
    p = _searcher(w, area, Survival=10)
    w.skill_check = lambda *a, **k: (True, 20, "")
    node = foraging.find_or_spawn(w, p, area, skill="survival",
                                  rng=random.Random(1))
    assert node is not None
    tags = {str(t).lower() for t in (node.properties.get("tags") or [])}
    assert tags & FORAGE_TAGS
    assert any(e.source == node.id and e.target == w.area_node_id(area)
               for e in w.graph.edges), "the find was not placed in the area"


def test_an_untagged_interior_yields_nothing():
    w = _world()
    area = _area(w, "Test Hall", [])
    p = _searcher(w, area, Survival=10)
    w.skill_check = lambda *a, **k: (True, 20, "")
    assert foraging.find_or_spawn(w, p, area, skill="survival") is None


def test_a_failed_check_finds_nothing():
    w = _world()
    area = _area(w, "Test Woods", ["forest"])
    p = _searcher(w, area, Survival=10)
    w.skill_check = lambda *a, **k: (False, 0, "")
    assert foraging.find_or_spawn(w, p, area, skill="survival") is None


def test_the_area_cap_stops_a_loot_pinata():
    w = _world()
    area = _area(w, "Test Woods", ["forest"])
    p = _searcher(w, area, Survival=10)
    w.skill_check = lambda *a, **k: (True, 20, "")
    rng = random.Random(2)
    found = [foraging.find_or_spawn(w, p, area, skill="survival", rng=rng)
             for _ in range(foraging.MAX_FINDS_PER_AREA_PER_DAY + 2)]
    assert sum(1 for n in found if n is not None) == \
        foraging.MAX_FINDS_PER_AREA_PER_DAY


def test_religion_search_in_a_ruin_finds_a_relic():
    w = _world()
    area = _area(w, "Test Ruin", ["ruin"])
    p = _searcher(w, area, Religion=10)
    w.skill_check = lambda *a, **k: (True, 20, "")
    node = foraging.find_or_spawn(w, p, area, skill="religion",
                                  rng=random.Random(3))
    assert node is not None
    tags = {str(t).lower() for t in (node.properties.get("tags") or [])}
    assert tags & {"relic", "religious", "idol"}


def test_soak_forages_when_the_area_has_no_food():
    w = _world()
    area = _area(w, "Test Woods", ["forest"])
    p = _searcher(w, area, Survival=10)
    p.simulation_mode = "background"
    p.vitals["Hunger"] = 80
    w.skill_check = lambda *a, **k: (True, 20, "")
    used = BackgroundSimulation(w).take_action(p, served=set(), remaining=10.0)
    assert used == TASK_MINUTES["eat"], (
        f"did not eat the find: used={used} hunger={p.vitals['Hunger']} "
        f"activity={getattr(p, 'activity', None)} "
        f"log={list(w.game_logger.game_log)[-3:]}")
    assert p.vitals["Hunger"] == 80 - 45
