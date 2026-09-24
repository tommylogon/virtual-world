"""Role-based skill profiles (task-476)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine import checks, roles


def _player(name="Tester", **stats):
    p = Player(name)
    p.stats.update(stats)
    p.skills.update({"Survival": 0, "Perception": 0, "Nature": 0,
                     "Investigation": 0, "Insight": 0, "Intimidation": 0})
    return p


# ───────────────────────────── data ───────────────────────────────────────

class TestData:
    def test_shipped_table_is_clean(self):
        assert roles.validate() == []

    def test_expected_roles_exist(self):
        table = roles.roles()
        for role_id in ("hunter", "trapper", "guard", "thief", "healer",
                        "scholar", "cook", "farmer"):
            assert role_id in table, role_id

    def test_add_a_role_is_data_only(self):
        data = {"roles": {"diver": {"name": "Diver",
                                    "skills": {"Athletics": 2}}}}
        assert roles.validate(data) == []

    def test_validate_flags_unknown_skill(self):
        data = {"roles": {"bad": {"name": "Bad",
                                  "skills": {"Basket Weaving": 2}}}}
        assert any("unknown skill" in p for p in roles.validate(data))

    def test_validate_flags_missing_name_and_empty_skills(self):
        problems = roles.validate({"roles": {"bad": {"skills": {}}}})
        assert any("missing name" in p for p in problems)
        assert any("no skill biases" in p for p in problems)

    def test_validate_flags_prefixed_id(self):
        data = {"roles": {"role:diver": {"name": "Diver",
                                         "skills": {"Athletics": 1}}}}
        assert any("prefix" in p for p in roles.validate(data))

    def test_validate_flags_zero_bias(self):
        data = {"roles": {"bad": {"name": "Bad", "skills": {"Athletics": 0}}}}
        assert any("zero" in p for p in roles.validate(data))


# ───────────────────────────── resolution ─────────────────────────────────

class TestResolution:
    def test_bare_tag_is_inert(self):
        p = _player()
        p.tags = ["cook", "farmer"]          # incidental, not roles
        assert roles.character_roles(p) == []
        assert roles.skill_mods(p) == {}

    def test_role_prefix_resolves(self):
        p = _player()
        p.tags = ["goblin", "role:trapper"]
        assert roles.character_roles(p) == ["trapper"]

    def test_prefix_is_case_insensitive(self):
        p = _player()
        p.tags = ["ROLE:Hunter"]
        assert roles.character_roles(p) == ["hunter"]

    def test_unknown_role_tag_ignored(self):
        p = _player()
        p.tags = ["role:astronaut"]
        assert roles.character_roles(p) == []
        assert roles.skill_mods(p) == {}

    def test_mods_are_additive_across_roles(self):
        p = _player()
        p.tags = ["role:guard", "role:cook"]
        mods = roles.skill_mods(p)
        assert mods["Insight"] == 2          # 1 (guard) + 1 (cook)
        assert mods["Perception"] == 2


# ────────────────────────────── pipeline ──────────────────────────────────

class TestPipeline:
    def test_role_mod_is_in_the_breakdown(self):
        p = _player()
        p.tags = ["role:guard"]
        _ability, mods = checks.skill_modifiers(p, "Perception")
        by_source = {m.source: m.value for m in mods}
        assert by_source.get("role") == 2
        # No guard bias on a skill the role does not name.
        assert "role" not in {m.source for m in
                              checks.skill_modifiers(p, "Stealth")[1]}

    def test_trapper_out_forages_a_roleless_child(self):
        trapper = _player("Trapper")
        trapper.tags = ["role:trapper"]
        child = _player("Child")
        # Same roll, same stats, same trained value: only the role differs.
        a = checks.resolve(trapper, kind="Survival", dc=11, roll_fn=lambda: 10)
        b = checks.resolve(child, kind="Survival", dc=11, roll_fn=lambda: 10)
        assert a.total == b.total + 2
        assert a.success and not b.success

    def test_guard_beats_a_cook_on_perception(self):
        guard = _player("Guard")
        guard.tags = ["role:guard"]
        cook = _player("Cook")
        cook.tags = ["role:cook"]
        a = checks.resolve(guard, kind="Perception", dc=11, roll_fn=lambda: 10)
        b = checks.resolve(cook, kind="Perception", dc=11, roll_fn=lambda: 10)
        assert a.success and not b.success
