"""Skill growth, proficiency and setting packs (task-480)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine import checks, skill_progress
from engine.skills import SkillSystem


class _Logger:
    def __init__(self):
        self.entries = []

    def add_log_entry(self, text):
        self.entries.append(text)


class _PM:
    def __init__(self, player):
        self.players = {player.name: player}
        self.active_player = player.name

    def get_active_player_obj(self):
        return self.players[self.active_player]


class _World:
    def __init__(self, growth=False, threshold=5):
        self.skill_growth = growth
        self.skill_growth_threshold = threshold


def _player(name="Tester"):
    return Player(name)


# ─────────────────────────────── packs ────────────────────────────────────

class TestPacks:
    def test_shipped_packs_validate(self):
        assert skill_progress.validate() == []

    def test_apply_pack_raises_only(self):
        p = _player()
        assert p.skills["Nature"] == 0 and p.skills["Animal Handling"] == 0
        granted = skill_progress.apply_pack(p, "eldenford_human")
        assert granted == {"Nature": 1, "Animal Handling": 1}

        # Idempotent, and never lowers an already-higher skill.
        p.skills["Nature"] = 4
        granted2 = skill_progress.apply_pack(p, "eldenford_human")
        assert granted2 == {} and p.skills["Nature"] == 4

    def test_apply_pack_can_lower_when_asked(self):
        p = _player()
        p.skills["Nature"] = 4
        skill_progress.apply_pack(p, "eldenford_human", allow_lower=True)
        assert p.skills["Nature"] == 1

    def test_apply_unknown_pack_is_a_noop(self):
        p = _player()
        assert skill_progress.apply_pack(p, "no_such_pack") == {}

    def test_validate_flags_bad_packs(self):
        problems = skill_progress.validate({"packs": {
            "bad": {"name": "Bad", "skills": {"Nonsense": 2, "Nature": 0}}}})
        assert any("unknown skill" in p for p in problems)
        assert any("positive" in p for p in problems)


# ──────────────────────────── proficiency ─────────────────────────────────

class TestProficiency:
    def test_default_is_zero_and_inert(self):
        p = _player()
        assert skill_progress.proficiency_bonus(p) == 0
        sources = {m.source for m in checks.skill_modifiers(p, "Survival")[1]}
        assert "proficiency" not in sources

    def test_proficiency_is_a_separate_modifier(self):
        p = _player()
        p.proficiency = 3
        mods = checks.skill_modifiers(p, "Survival")[1]
        assert any(m.source == "proficiency" and m.value == 3 for m in mods)

    def test_proficiency_flows_through_resolve(self):
        p = _player()
        p.skills["Survival"] = 0
        p.proficiency = 3
        res = checks.resolve(p, kind="Survival", dc=10, roll_fn=lambda: 7)
        assert res.total == 10 and res.success


# ─────────────────────── use-based advancement ────────────────────────────

class TestGrowth:
    def test_a_skill_rises_after_the_threshold_of_successes(self):
        p = _player()
        p.skills["Survival"] = 0
        raised = [skill_progress.record_use(p, "Survival", threshold=3)
                  for _ in range(3)]
        assert raised == [False, False, True]
        assert p.skills["Survival"] == 1
        assert skill_progress.skill_progress(p)["Survival"] == 0

    def test_failure_does_not_teach(self):
        p = _player()
        p.skills["Survival"] = 0
        for _ in range(10):
            assert skill_progress.record_use(p, "Survival", success=False) is False
        assert p.skills["Survival"] == 0

    def test_growth_is_capped(self):
        p = _player()
        p.skills["Survival"] = skill_progress.MAX_SKILL
        for _ in range(20):
            assert skill_progress.record_use(p, "Survival", threshold=1) is False
        assert p.skills["Survival"] == skill_progress.MAX_SKILL

    def test_growth_is_opt_in(self):
        p = _player()
        p.skills["Perception"] = 0
        pm = _PM(p)
        logger = _Logger()

        off = SkillSystem(pm, logger, game_state=_World(growth=False))
        off.roll_dice = lambda *a, **k: 20
        for _ in range(6):
            off.skill_check("Perception", 5)
        assert p.skills["Perception"] == 0, "grew with growth disabled"

        on = SkillSystem(pm, logger, game_state=_World(growth=True, threshold=3))
        on.roll_dice = lambda *a, **k: 20
        for _ in range(3):
            on.skill_check("Perception", 5)
        assert p.skills["Perception"] == 1, "did not grow with growth enabled"
        assert any("improved" in e for e in logger.entries)

    def test_growth_needs_a_world(self):
        p = _player()
        p.skills["Perception"] = 0
        sys_ = SkillSystem(_PM(p), _Logger())   # no game_state
        sys_.roll_dice = lambda *a, **k: 20
        for _ in range(6):
            sys_.skill_check("Perception", 5)
        assert p.skills["Perception"] == 0


# ─────────────────────────── serialization ────────────────────────────────

class TestSerialization:
    def test_progress_and_proficiency_serialize(self):
        p = _player()
        p.proficiency = 2
        p.skills["Survival"] = 0
        skill_progress.record_use(p, "Survival", threshold=5)
        data = p.to_dict()
        assert data["proficiency"] == 2
        assert data["skill_progress"]["Survival"] == 1


# ────────────────────── mutable abilities in play ─────────────────────────

class _GS:
    def __init__(self, player):
        self.player = player
        self.players = {player.name: player}


class TestMutableAbilities:
    def test_adjust_stat_trains_and_clamps(self):
        from engine.effect_handlers import vitals
        p = _player()
        p.stats["STR"] = 10
        gs = _GS(p)
        vitals.handle_adjust_stat(None, {"stat": "STR", "amount": 3}, {}, game_state=gs)
        assert p.stats["STR"] == 13
        vitals.handle_adjust_stat(None, {"stat": "STR", "amount": 100}, {}, game_state=gs)
        assert p.stats["STR"] == 30
        vitals.handle_adjust_stat(None, {"stat": "STR", "amount": -100}, {}, game_state=gs)
        assert p.stats["STR"] == 1

    def test_adjust_stat_reuses_existing_key_case(self):
        from engine.effect_handlers import vitals
        p = _player()
        p.stats = {"str": 10}
        gs = _GS(p)
        vitals.handle_adjust_stat(None, {"stat": "STR", "amount": 2}, {}, game_state=gs)
        assert p.stats["str"] == 12

    def test_unknown_stat_is_ignored(self):
        from engine.effect_handlers import vitals
        p = _player()
        gs = _GS(p)
        assert vitals.handle_adjust_stat(
            None, {"stat": "LUCK", "amount": 5}, {}, game_state=gs) == []
