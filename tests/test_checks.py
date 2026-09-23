"""Central dice and check system (task-472)."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine import checks


def _player(**stats):
    p = Player("Tester")
    p.stats.update(stats)
    return p


# ───────────────────────────── dice ───────────────────────────────────────

class TestDice:
    def test_parse_expression(self):
        assert checks.parse_dice("2d6+3") == (2, 6, 3)
        assert checks.parse_dice("d20") == (1, 20, 0)
        assert checks.parse_dice("1d8-1") == (1, 8, -1)

    def test_flat_number_is_a_constant(self):
        assert checks.parse_dice("4") == (0, 0, 4)
        assert checks.roll("4") == 4

    def test_roll_matches_dice_primitive(self):
        assert checks.roll("2d6+1", rng=random.Random(5)) == \
            checks.roll_dice(2, 6, 1, rng=random.Random(5))

    def test_roll_range(self):
        rng = random.Random(1)
        assert 3 <= checks.roll("3d6", rng=rng) <= 18

    def test_bad_expression_raises(self):
        try:
            checks.parse_dice("banana")
        except ValueError:
            return
        raise AssertionError("expected ValueError")


# ───────────────────────────── abilities ──────────────────────────────────

class TestAbilities:
    def test_ability_mod_bands(self):
        assert checks.ability_mod(10) == 0
        assert checks.ability_mod(20) == 5
        assert checks.ability_mod(8) == -1
        assert checks.ability_mod(1) == -5
        assert checks.ability_mod(None) == 0

    def test_skill_ability_map(self):
        assert checks.SKILL_ABILITY["Survival"] == "WIS"
        assert checks.SKILL_ABILITY["Sleight of Hand"] == "DEX"
        assert checks.SKILL_ABILITY["History"] == "INT"

    def test_dc_bands_keep_legacy_wording(self):
        assert checks.dc_band(5) == "very easy"
        assert checks.dc_band(10) == "easy"
        assert checks.dc_band(12) == "medium"
        assert checks.dc_band(20) == "hard"
        assert checks.dc_band(25) == "very hard"


# ─────────────────────── advantage / disadvantage ─────────────────────────

class TestAdvantage:
    def test_normal_roll_uses_one_die(self):
        roll = checks.roll_d20(roll_fn=lambda: 11)
        assert roll.mode == "normal" and roll.kept == 11 and roll.faces == [11]

    def test_advantage_keeps_the_high_die(self):
        faces = iter([4, 17])
        roll = checks.roll_d20(advantage=True, roll_fn=lambda: next(faces))
        assert roll.kept == 17 and roll.mode == "advantage"

    def test_disadvantage_keeps_the_low_die(self):
        faces = iter([4, 17])
        roll = checks.roll_d20(disadvantage=True, roll_fn=lambda: next(faces))
        assert roll.kept == 4 and roll.mode == "disadvantage"

    def test_advantage_and_disadvantage_cancel(self):
        roll = checks.roll_d20(advantage=True, disadvantage=True,
                               roll_fn=lambda: 12)
        assert roll.mode == "normal" and roll.faces == [12]


# ───────────────────────────── resolve ────────────────────────────────────

class TestResolve:
    def test_skill_check_adds_ability_and_skill(self):
        p = _player(WIS=14)          # +2
        p.skills["Perception"] = 3
        res = checks.resolve(p, kind="Perception", dc=15, roll_fn=lambda: 10)
        assert res.total == 15 and res.success
        by_source = {m.source: m.value for m in res.modifiers}
        assert by_source["WIS mod"] == 2 and by_source["Perception"] == 3

    def test_degrees_of_success(self):
        assert checks.resolve(_player(), kind="Athletics", dc=10,
                              roll_fn=lambda: 10).tier == "success"
        assert checks.resolve(_player(), kind="Athletics", dc=10,
                              roll_fn=lambda: 15).tier == "strong_success"
        assert checks.resolve(_player(), kind="Athletics", dc=10,
                              roll_fn=lambda: 20).tier == "crit_success"
        assert checks.resolve(_player(), kind="Athletics", dc=10,
                              roll_fn=lambda: 1).tier == "crit_fail"

    def test_ability_check_uses_the_stat_modifier(self):
        res = checks.resolve(_player(DEX=20), kind="DEX", dc=10,
                             roll_fn=lambda: 5)
        assert res.total == 10 and res.success

    def test_explicit_modifiers_are_added(self):
        p = _player()
        p.skills["Athletics"] = 0
        res = checks.resolve(p, kind="Athletics", dc=10,
                             roll_fn=lambda: 5,
                             extra_mods=[("cover", 2), checks.Modifier("bless", 3)])
        assert res.total == 10

    def test_condition_disadvantage_applies(self):
        p = _player()
        p.conditions["restrained"] = [{}]     # attacks at disadvantage
        res = checks.resolve(p, kind="attack", dc=5, roll_fn=lambda: 15)
        assert res.mode == "disadvantage"

    def test_condition_auto_fail(self, monkeypatch):
        p = _player()
        p.conditions["test_fail"] = [{}]
        monkeypatch.setattr(checks, "_condition_definitions",
                            lambda: {"test_fail": {"auto_fail_checks": ["dexterity"]}})
        res = checks.resolve(p, kind="Stealth", dc=5, roll_fn=lambda: 20)
        assert res.auto_fail and res.success is False and res.tier == "auto_fail"

    def test_condition_advantage_applies(self, monkeypatch):
        p = _player()
        p.conditions["focused"] = [{}]
        monkeypatch.setattr(checks, "_condition_definitions",
                            lambda: {"focused": {"check_advantage": ["perception"]}})
        res = checks.resolve(p, kind="Perception", dc=5, roll_fn=lambda: 15)
        assert res.mode == "advantage"

    def test_logs_a_breakdown(self):
        class _Logger:
            def __init__(self):
                self.entries = []

            def add_log_entry(self, text):
                self.entries.append(text)

        logger = _Logger()
        checks.resolve(_player(WIS=14), kind="Perception", dc=10,
                       roll_fn=lambda: 6, logger=logger)
        assert logger.entries and "[Check] Perception vs DC 10 (easy)" in logger.entries[0]
        assert "WIS mod" not in logger.entries[0]  # breakdown shows values, not sources


class TestOpposed:
    def test_higher_total_wins(self):
        a = _player(STR=18)
        d = _player(STR=6)
        a.skills["Athletics"] = 5
        d.skills["Athletics"] = 0
        win = iter([15])
        lose = iter([3])
        res_a, res_d, attacker_wins = checks.opposed(
            a, d, kind="Athletics", roll_fn=lambda: next(win),
            defender_roll_fn=lambda: next(lose))
        assert attacker_wins and res_a.success and not res_d.success

    def test_ties_go_to_the_defender(self):
        a = _player()
        d = _player()
        res_a, res_d, attacker_wins = checks.opposed(
            a, d, kind="Athletics", roll_fn=lambda: 10,
            defender_roll_fn=lambda: 10)
        assert not attacker_wins
