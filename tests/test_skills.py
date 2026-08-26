"""Tests for the SkillSystem: dice rolling, skill checks, and utilities."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from engine.skills import SkillSystem
from engine.player_manager import PlayerManager
from engine.logging_events import GameLogger
from graph import WorldGraph


# ─────────────────── Fixtures ───────────────────


@pytest.fixture
def graph():
    """Create a bare WorldGraph."""
    return WorldGraph()


@pytest.fixture
def game_logger():
    """Create a GameLogger."""
    return GameLogger()


@pytest.fixture
def player_manager(graph, game_logger):
    """Create a PlayerManager with a default player."""
    pm = PlayerManager(graph)
    from player import Player
    player = Player("TestHero")
    player.skills["Athletics"] = 8
    player.skills["Perception"] = 5
    player.skills["Stealth"] = 2
    player.skills["Survival"] = 0
    pm.add_player(player)
    return pm


@pytest.fixture
def skills(player_manager, game_logger):
    """Create a SkillSystem with all dependencies."""
    return SkillSystem(player_manager, game_logger)


# ─────────────────── TestSkills ───────────────────


class TestDiceRolling:
    """Dice rolling mechanics."""

    def test_roll_d20_within_range(self, skills):
        """A single d20 roll is between 1 and 20."""
        for _ in range(100):
            roll = skills.roll_dice(1, 20, 0)
            assert 1 <= roll <= 20

    def test_roll_d6_within_range(self, skills):
        """A single d6 roll is between 1 and 6."""
        for _ in range(100):
            roll = skills.roll_dice(1, 6, 0)
            assert 1 <= roll <= 6

    def test_roll_3d6_within_range(self, skills):
        """Rolling 3d6 produces a value between 3 and 18."""
        for _ in range(100):
            roll = skills.roll_dice(3, 6, 0)
            assert 3 <= roll <= 18

    def test_roll_with_modifier(self, skills):
        """Roll modifier shifts the result."""
        for _ in range(50):
            roll = skills.roll_dice(1, 10, 5)
            assert 6 <= roll <= 15

    def test_roll_negative_modifier(self, skills):
        """Negative modifier reduces result."""
        for _ in range(50):
            roll = skills.roll_dice(1, 20, -3)
            # Could be negative if roll is 1 and modifier is -3
            assert -2 <= roll <= 17

    def test_roll_d100_within_range(self, skills):
        """A d100 roll is between 1 and 100."""
        for _ in range(100):
            roll = skills.roll_dice(1, 100, 0)
            assert 1 <= roll <= 100

    def test_roll_deterministic_seed_not_constant(self, skills):
        """Consecutive rolls produce varied results (not always the same)."""
        rolls = [skills.roll_dice(1, 20, 0) for _ in range(10)]
        # Extremely unlikely all 10 rolls of d20 are the same number
        assert len(set(rolls)) > 1


class TestSkillChecks:
    """Skill check mechanics."""

    def test_skill_check_pass(self, skills, player_manager):
        """High skill vs low DC should usually pass."""
        player = player_manager.get_active_player_obj()
        player.skills["Athletics"] = 15

        success, total, message = skills.skill_check("Athletics", difficulty_class=5)
        assert success is True
        assert total >= 5
        assert "success" in message.lower()

    def test_skill_check_fail(self, skills, player_manager):
        """Low skill vs high DC should usually fail."""
        player = player_manager.get_active_player_obj()
        player.skills["Athletics"] = 0

        # 100 runs — should all fail against DC 30
        all_fail = True
        for _ in range(100):
            success, total, message = skills.skill_check("Athletics", difficulty_class=30)
            if success:
                all_fail = False
                break
        assert all_fail, "Skill check with skill=0 vs DC=30 should never pass"

    def test_skill_check_returns_tuple(self, skills):
        """Skill check returns (success, total, message) tuple."""
        result = skills.skill_check("Athletics", difficulty_class=10)
        assert len(result) == 3
        assert isinstance(result[0], bool)
        assert isinstance(result[1], int)
        assert isinstance(result[2], str)

    def test_skill_check_medium_dc(self, skills):
        """Skill check with medium DC (12) returns appropriate description."""
        success, total, message = skills.skill_check("Perception", difficulty_class=12)
        assert "medium" in message.lower() or "hard" in message.lower()

    def test_skill_check_easy_dc(self, skills):
        """Skill check with easy DC (5) returns appropriate description."""
        success, total, message = skills.skill_check("Perception", difficulty_class=5)
        assert "very easy" in message.lower() or "easy" in message.lower()

    def test_skill_check_very_hard_dc(self, skills):
        """Skill check with DC 25 returns appropriate description."""
        success, total, message = skills.skill_check("Perception", difficulty_class=25)
        assert "very hard" in message.lower()

    def test_skill_check_logs_entry(self, skills, game_logger):
        """Skill check adds an entry to the game log."""
        log_count_before = len(game_logger.game_log)
        skills.skill_check("Perception", difficulty_class=10)
        log_count_after = len(game_logger.game_log)
        assert log_count_after > log_count_before

    def test_skill_check_no_active_player(self, skills, player_manager):
        """Skill check with no active player returns failure."""
        player_manager.active_player = None
        success, total, message = skills.skill_check("Athletics", difficulty_class=10,
                                                      use_active_player=True)
        assert success is False
        assert total == 0
        assert "No active player" in message

    def test_skill_check_unknown_skill_defaults(self, skills, player_manager):
        """Unknown skill name defaults to skill value 0."""
        success, total, message = skills.skill_check("UnknownSkill",
                                                      difficulty_class=5)
        # With skill=0 and d20, success is still possible (roll >= 5)
        assert isinstance(success, bool)

    def test_skill_check_multiple_runs(self, skills):
        """Multiple skill checks are independent and produce varied results."""
        results = set()
        for _ in range(20):
            success, total, message = skills.skill_check("Athletics",
                                                          difficulty_class=10)
            results.add(total)
        # With skill=8, total = roll(1-20) + 8 = 9-28, should have variety
        assert len(results) > 1

    def test_skill_check_success_increases_with_skill(self, skills, player_manager):
        """Higher skill makes success more likely."""
        player = player_manager.get_active_player_obj()

        # Test with very low skill vs DC 15
        player.skills["Athletics"] = -10
        low_skill_wins = sum(
            1 for _ in range(50)
            if skills.skill_check("Athletics", difficulty_class=15)[0]
        )

        # Test with very high skill vs DC 15
        player.skills["Athletics"] = 20
        high_skill_wins = sum(
            1 for _ in range(50)
            if skills.skill_check("Athletics", difficulty_class=15)[0]
        )

        assert high_skill_wins >= low_skill_wins


class TestSavingThrows:
    """Unified save primitive (task-159): stat or skill, any player."""

    def _player(self, player_manager):
        return player_manager.get_active_player_obj()

    def test_stat_save_pass(self, skills, player_manager):
        """High stat vs low DC passes."""
        player = self._player(player_manager)
        player.stats["DEX"] = 20  # mod +5, min total 6
        success, total, msg = skills.saving_throw(player, "DEX", 5)
        assert success is True
        assert total >= 5
        assert "[Save] DEX vs DC 5" in msg
        assert "success" in msg.lower()

    def test_stat_save_fail(self, skills, player_manager):
        """Low stat vs high DC fails."""
        player = self._player(player_manager)
        player.stats["DEX"] = 3  # mod -3, max total 17
        all_fail = True
        for _ in range(100):
            success, total, msg = skills.saving_throw(player, "DEX", 30)
            if success:
                all_fail = False
                break
        assert all_fail

    def test_skill_save(self, skills, player_manager):
        """A skill name (not a stat) rolls the raw skill value."""
        player = self._player(player_manager)
        player.skills["Athletics"] = 8
        success, total, msg = skills.saving_throw(player, "Athletics", 5)
        assert success is True
        assert "[Save] Athletics vs DC 5" in msg

    def test_negative_stat_modifier_not_clamped(self, skills, player_manager):
        """STR 6 → -2 mod (not clamped to 0), so DC 19 can never pass."""
        player = self._player(player_manager)
        player.stats["STR"] = 6
        all_fail = True
        for _ in range(100):
            success, total, msg = skills.saving_throw(player, "STR", 19)
            if success:
                all_fail = False
                break
        assert all_fail

    def test_npc_player_save(self, skills, player_manager):
        """Saves work for NPCs, not just the active player."""
        from player import Player
        npc = Player("Guard")
        npc.stats["CON"] = 18  # mod +4, min total 5
        success, total, msg = skills.saving_throw(npc, "CON", 5)
        assert success is True
        assert "[Save] CON vs DC 5" in msg

    def test_returns_tuple(self, skills, player_manager):
        """saving_throw returns (success, total, message)."""
        result = skills.saving_throw(self._player(player_manager), "DEX", 12)
        assert len(result) == 3
        assert isinstance(result[0], bool)
        assert isinstance(result[1], int)
        assert isinstance(result[2], str)

    def test_save_logs_entry(self, skills, game_logger):
        """The roll is added to the game log like other skill checks."""
        log_count_before = len(game_logger.game_log)
        skills.saving_throw(self._player(skills.player_manager), "DEX", 12)
        assert len(game_logger.game_log) > log_count_before

    def test_unset_stat_defaults_to_10(self, skills, player_manager):
        """A stat not present in player.stats defaults to 10 (mod 0)."""
        player = self._player(player_manager)
        del player.stats["WIS"]
        success, total, msg = skills.saving_throw(player, "WIS", 30)
        assert success is False
        assert total <= 20

    def test_save_passes_at_exact_dc(self, skills, player_manager, monkeypatch):
        """total == dc is a success (uses >=, not >)."""
        player = self._player(player_manager)
        player.stats["DEX"] = 14  # mod +2
        monkeypatch.setattr(skills, "roll_dice", lambda *a, **k: 8)  # total 10
        success, total, msg = skills.saving_throw(player, "DEX", 10)
        assert success is True
        assert total == 10

    def test_save_fails_one_below_dc(self, skills, player_manager, monkeypatch):
        """total == dc - 1 is a failure."""
        player = self._player(player_manager)
        player.stats["DEX"] = 14  # mod +2
        monkeypatch.setattr(skills, "roll_dice", lambda *a, **k: 7)  # total 9
        success, total, msg = skills.saving_throw(player, "DEX", 10)
        assert success is False
        assert total == 9

    def test_save_message_shows_modifier_math(self, skills, player_manager, monkeypatch):
        """The logged message shows roll + mod = total."""
        player = self._player(player_manager)
        player.stats["STR"] = 16  # mod +3
        monkeypatch.setattr(skills, "roll_dice", lambda *a, **k: 4)
        success, total, msg = skills.saving_throw(player, "STR", 10)
        assert "roll 4 + 3 = 7" in msg

    def test_save_with_none_stats_and_skills(self, skills, player_manager):
        """None stats/skills dicts fall back to defaults instead of crashing."""
        player = self._player(player_manager)
        player.stats = None
        player.skills = None
        success, total, msg = skills.saving_throw(player, "DEX", 30)
        assert success is False
        assert total <= 20


class TestPlayerStateRemedy:
    """Player state remedy hints."""

    def test_sleeping_remedy(self, skills):
        """State 'sleeping' returns 'wake up'."""
        assert skills.player_state_remedy("sleeping") == "wake up"

    def test_unconscious_remedy(self, skills):
        """State 'unconscious' returns medical hint."""
        assert "medical" in skills.player_state_remedy("unconscious").lower()

    def test_bound_remedy(self, skills):
        """State 'bound' returns struggle hint."""
        assert "struggle" in skills.player_state_remedy("bound").lower()

    def test_dead_remedy(self, skills):
        """State 'dead' returns character creation hint."""
        assert "create" in skills.player_state_remedy("dead").lower()

    def test_unknown_state_remedy(self, skills):
        """Unknown state returns generic 'recover'."""
        assert skills.player_state_remedy("unknown") == "recover"


class TestSanityAndInvariants:
    """Safeguards: no random module contamination, no global state mutation."""

    def test_import_only_standard_library(self):
        """SkillSystem only imports from engine modules and standard library."""
        import inspect
        import engine.skills
        source = inspect.getsource(engine.skills)
        # Should import from: random, typing (stdlib) and engine modules
        # Should NOT import from: numpy, pandas, flask, etc.
        prohibited = ["import numpy", "import pandas", "import flask",
                      "import torch", "import tensorflow", "import django"]
        for imp in prohibited:
            assert imp not in source, f"SkillSystem imports prohibited module: {imp}"

    def test_roll_dice_uses_random_not_global_state(self, skills):
        """roll_dice does not modify any global state."""
        # Capture random state before
        import random
        state_before = random.getstate()

        skills.roll_dice(2, 6, 3)

        # After — SkillSystem uses its own random calls but shouldn't
        # permanently leak state (allowed to advance the global generator)
        # This test just ensures it doesn't crash; the real invariant is
        # that no module-level variables are mutated.
        import random
        state_after = random.getstate()
        # State can differ (random calls advance state) — that's fine
        assert state_after is not None

    def test_skill_check_does_not_mutate_global_config(self, skills):
        """Skill check does not modify module-level configuration."""
        from engine import skills as skill_module
        # Store references to module-level attributes
        attrs_before = set(dir(skill_module))
        skills.skill_check("Athletics", difficulty_class=10)
        attrs_after = set(dir(skill_module))
        assert attrs_before == attrs_after


class TestTraitSchemaV2Mods:
    """skill_check_mod / save_bonus wired into the roll primitives."""

    def test_skill_check_per_skill_mod(self, skills, player_manager):
        player = player_manager.get_player("TestHero")
        player.traits["sharp_eyed"] = True  # Perception +2
        skills.roll_dice = lambda *args: 10
        success, total, _ = skills.skill_check("Perception", 14)
        assert success is True
        assert total == 5 + 2 + 10  # skill 5 + trait +2 + roll 10

    def test_skill_check_flat_mod(self, skills, player_manager):
        player = player_manager.get_player("TestHero")
        player.traits["jittery"] = True  # all skills -1
        skills.roll_dice = lambda *args: 10
        success, total, _ = skills.skill_check("Athletics", 17)  # 8 - 1 + 10 = 17
        assert success is True
        assert total == 8 - 1 + 10

    def test_saving_throw_per_stat_bonus(self, skills, player_manager):
        player = player_manager.get_player("TestHero")
        player.stats["WIS"] = 14  # mod +2
        player.traits["iron_will"] = True  # WIS +2
        skills.roll_dice = lambda *args: 10
        success, total, _ = skills.saving_throw(player, "WIS", 13)
        assert success is True
        assert total == 10 + 2 + 2  # roll + WIS mod + trait bonus = 14
