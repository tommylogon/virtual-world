"""Search tables and two-step notice/search (task-478)."""

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


def _area(w, name, tags):
    from area import Area
    w.movement.add_area(Area(name, "Test ground.", []))
    w.graph.get_node(w.area_node_id(name)).properties["tags"] = list(tags)
    return name


def _searcher(name="Searcher"):
    p = Player(name)
    return p


# ─────────────────────────────── tables ───────────────────────────────────

class TestTables:
    def test_new_skills_have_tables_and_display_names(self):
        for key in ("nature", "investigation", "arcana", "medicine"):
            assert key in foraging.SKILL_TABLES
            assert foraging.SKILL_TABLES[key]
            assert foraging.SKILL_DISPLAY[key] == key.title()

    def test_area_bonuses_cover_the_new_skills(self):
        forest = foraging.AREA_SKILL_BONUS["forest"]
        assert forest["nature"] >= 1 and forest["medicine"] >= 1
        ruin = foraging.AREA_SKILL_BONUS["ruin"]
        assert ruin["investigation"] >= 1 and ruin["arcana"] >= 1
        assert foraging.AREA_SKILL_BONUS["temple"]["arcana"] >= 1

    def test_best_skill_for_a_plant_is_nature(self):
        p = _searcher()
        p.skills.update({"Nature": 3, "Medicine": 0, "Survival": 0})
        assert foraging.best_skill_for(None, p, ["plant"]) == "nature"

    def test_existing_area_gate_is_unchanged(self):
        # No new area tags were introduced, so the "can this area yield" set is
        # the same tags it always was.
        assert "forest" in foraging.AREA_SKILL_BONUS
        assert "cave" not in foraging.AREA_SKILL_BONUS


# ─────────────────────────── notice (step 1) ──────────────────────────────

class TestNotice:
    def test_notice_marks_the_area_on_success(self):
        w = _world()
        area = _area(w, "Old Ruin", ["ruin"])
        w.skill_check = lambda *a, **k: (True, 20, "")
        assert foraging.notice(w, _searcher(), area) is True
        node = w.graph.get_node(w.area_node_id(area))
        assert node.properties[foraging.NOTICE_PROPERTY] is True

    def test_notice_fails_without_a_successful_check(self):
        w = _world()
        area = _area(w, "Old Ruin", ["ruin"])
        w.skill_check = lambda *a, **k: (False, 2, "")
        assert foraging.notice(w, _searcher(), area) is False
        node = w.graph.get_node(w.area_node_id(area))
        assert not node.properties.get(foraging.NOTICE_PROPERTY)

    def test_already_noticed_needs_no_new_check(self):
        w = _world()
        area = _area(w, "Old Ruin", ["ruin"])
        node = w.graph.get_node(w.area_node_id(area))
        node.properties[foraging.NOTICE_PROPERTY] = True
        w.skill_check = lambda *a, **k: (False, 2, "")   # would fail if rolled
        assert foraging.notice(w, _searcher(), area) is True


# ──────────────────────── notice-then-search (step 2) ─────────────────────

class TestNoticeThenSearch:
    def test_hidden_search_needs_a_notice(self):
        w = _world()
        area = _area(w, "Old Ruin", ["ruin"])
        w.skill_check = lambda *a, **k: (True, 25, "")
        # require_notice without a notice finds nothing even on a great roll.
        assert foraging.find_or_spawn(w, _searcher(), area, skill="investigation",
                                      rng=random.Random(1),
                                      require_notice=True) is None

    def test_a_failed_notice_means_no_search(self):
        w = _world()
        area = _area(w, "Old Ruin", ["ruin"])
        w.skill_check = lambda *a, **k: (False, 2, "")
        assert foraging.search_hidden(w, _searcher(), area) is None

    def test_notice_then_search_finds(self):
        w = _world()
        area = _area(w, "Old Ruin", ["ruin"])
        w.skill_check = lambda *a, **k: (True, 25, "")
        find = foraging.search_hidden(w, _searcher(), area,
                                      rng=random.Random(1))
        assert find is not None
        # It really landed in the area, not in the void.
        assert w.graph.get_node(find.id) is not None

    def test_plain_search_is_not_gated(self):
        w = _world()
        area = _area(w, "Forest", ["forest"])
        w.skill_check = lambda *a, **k: (True, 25, "")
        find = foraging.find_or_spawn(w, _searcher(), area, skill="survival",
                                      rng=random.Random(1))
        assert find is not None
