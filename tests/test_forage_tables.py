"""Forage table JSON surface, per-area overrides, findable hints (task-483)."""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine import foraging


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _area(w, name, tags=(), forage_tables=None):
    from area import Area
    w.movement.add_area(Area(name, "Test ground.", []))
    node = w.graph.get_node(w.area_node_id(name))
    node.properties["tags"] = list(tags)
    if forage_tables is not None:
        node.properties[foraging.AREA_TABLES_PROPERTY] = forage_tables
    return name


def _searcher(name="Searcher"):
    return Player(name)


# ───────────────────────────── JSON surface ───────────────────────────────

class TestDataSurface:
    def test_shipped_file_is_authoritative(self):
        with open(foraging.FORAGE_DATA_PATH, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        assert set(data["skill_tables"]) == set(foraging.SKILL_TABLES)
        assert data["area_skill_bonus"]["forest"] == \
            foraging.AREA_SKILL_BONUS["forest"]

    def test_all_eight_skills_are_shipped(self):
        for key in ("survival", "perception", "history", "religion",
                    "nature", "investigation", "arcana", "medicine"):
            assert key in foraging.SKILL_TABLES
            assert key in foraging.SKILL_DISPLAY

    def test_missing_file_falls_back_to_builtins(self):
        assert foraging._load_forage_data("Z:/definitely/not/here.json") == {}
        assert foraging._DEFAULT_SKILL_TABLES
        assert foraging._DEFAULT_AREA_SKILL_BONUS


# ─────────────────────────── per-area override ────────────────────────────

class TestPerAreaOverride:
    def test_override_makes_an_untagged_area_searchable(self):
        w = _world()
        area = _area(w, "Hidden Alcove", forage_tables={
            "survival": [{"tags": ["food"], "weight": 5}]})
        w.skill_check = lambda *a, **k: (True, 25, "")
        find = foraging.find_or_spawn(w, _searcher(), area, skill="survival",
                                      rng=random.Random(1))
        assert find is not None

    def test_untagged_area_without_override_stays_barren(self):
        w = _world()
        area = _area(w, "Bare Room")
        w.skill_check = lambda *a, **k: (True, 25, "")
        assert foraging.find_or_spawn(w, _searcher(), area, skill="survival",
                                      rng=random.Random(1)) is None


# ────────────────────────── findable-here hints ───────────────────────────

class TestFindableHere:
    def test_forest_offers_its_skills(self):
        w = _world()
        area = _area(w, "Forest", ["forest"])
        keys = {h["key"] for h in foraging.findable_here(w, area)}
        assert {"survival", "nature", "medicine"} <= keys

    def test_override_skill_is_reported(self):
        w = _world()
        area = _area(w, "Wizard's Nook", forage_tables={
            "arcana": [{"tags": ["relic"], "weight": 2}]})
        keys = {h["key"] for h in foraging.findable_here(w, area)}
        assert "arcana" in keys

    def test_bare_area_has_no_hints(self):
        w = _world()
        area = _area(w, "Bare Room")
        assert foraging.findable_here(w, area) == []
        assert "worth searching" in foraging.findable_hint(w, area)

    def test_hint_names_the_skill(self):
        w = _world()
        area = _area(w, "Temple", ["temple"])
        assert "Religion" in foraging.findable_hint(w, area)
