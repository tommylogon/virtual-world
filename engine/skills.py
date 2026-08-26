"""Skill checks, dice rolling, and LLM call logging for the virtual world.

Provides a stateless skill-check service used by combat, triggers,
and narration.  All dependencies (player manager, logging) are
injected via the constructor.
"""

import random
from typing import Optional


class SkillSystem:
    """Performs D20 skill checks and dice rolls.

    Parameters
    ----------
    player_manager:
        Must provide ``get_active_player_obj()``, ``players``,
        and ``active_player``.
    logging_events:
        Must provide ``record_turn_event(...)``.
    """

    def __init__(self, player_manager, logging_events):
        self.player_manager = player_manager
        self.logging_events = logging_events

    # ─────────────────────────── Dice rolling ─────────────────────────

    def roll_dice(
        self, num_dice: int = 1, sides: int = 20, modifier: int = 0
    ) -> int:
        """Roll *num_dice* each with *sides* sides, sum them, and add *modifier*.

        >>> SkillSystem(None, None).roll_dice(1, 6, 0)  # 1d6 (random)
        4  # (example)
        """
        total = sum(random.randint(1, sides) for _ in range(num_dice))
        return total + modifier

    # ─────────────────────────── Skill checks ─────────────────────────

    def skill_check(
        self,
        skill_name: str,
        difficulty_class: int = 10,
        use_active_player: bool = True,
    ) -> tuple:
        """Perform a D20 skill check for the active player.

        Parameters
        ----------
        skill_name:
            The skill to test (e.g. ``"Perception"``, ``"Athletics"``).
        difficulty_class:
            The DC to beat.
        use_active_player:
            If True, uses the currently active player.  Otherwise a
            caller-supplied player would be needed (not yet supported).

        Returns
        -------
        tuple of ``(success: bool, total: int, message: str)``.
        """
        player = self.player_manager.get_active_player_obj() if use_active_player else None
        if not player:
            return (False, 0, "No active player")

        skill_value = player.skills.get(skill_name, 0)
        from engine.traits import TraitSystem
        mods = TraitSystem.get_skill_check_mods(player)
        bonus = mods.get(skill_name, 0) + mods.get("*", 0)
        roll = self.roll_dice(1, 20, 0)
        total = roll + skill_value + bonus
        success = total >= difficulty_class

        if difficulty_class <= 5:
            diff_desc = "very easy"
        elif difficulty_class <= 10:
            diff_desc = "easy"
        elif difficulty_class <= 15:
            diff_desc = "medium"
        elif difficulty_class <= 20:
            diff_desc = "hard"
        else:
            diff_desc = "very hard"

        result_label = "success" if success else "failure"
        message = (
            f"[Skill Check] {skill_name} vs DC {difficulty_class} ({diff_desc}): "
            f"roll={roll} + {skill_value} + {bonus} = {total} => {result_label}"
        )
        self.logging_events.add_log_entry(message)
        return (success, total, message)

    # ─────────────────────────── Saving throws ────────────────────────

    #: The six core ability scores. A check against one of these rolls the
    #: stat modifier; anything else is treated as a skill value.
    STAT_NAMES = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}

    def saving_throw(self, player, stat: str, dc: int = 12) -> tuple:
        """Roll d20 + modifier vs DC for an arbitrary player (active or NPC).

        *stat* is either an ability score (``"STR"``, ``"DEX"``, ``"CON"``,
        ``"INT"``, ``"WIS"``, ``"CHA"`` — rolled via the stat modifier
        ``(value - 10) // 2``) or a skill name (``"Athletics"``, ... — rolled
        via the raw skill value). This is the single unified save primitive
        (task-159): grab, traps, damage effects, and future mechanics all go
        through it.

        Conditions with ``auto_fail_saves`` for *stat* (paralysed/stunned/
        unconscious vs STR/DEX, restrained vs DEX, ...) auto-fail the save.

        Returns ``(success, total, message)``. The roll is logged to the
        event stream like other skill checks.
        """
        from engine.conditions import auto_fails_saves
        if auto_fails_saves(player, stat):
            message = (
                f"[Save] {stat} vs DC {dc}: AUTO-FAIL (a condition prevents it)"
            )
            self.logging_events.add_log_entry(message)
            return (False, 0, message)
        if stat in self.STAT_NAMES:
            stat_value = (player.stats or {}).get(stat, 10)
            mod = (stat_value - 10) // 2
        else:
            mod = (player.skills or {}).get(stat, 0)
        from engine.traits import TraitSystem
        flat_bonus, per_stat_bonus = TraitSystem.get_save_bonus(player)
        mod += flat_bonus + per_stat_bonus.get(stat, 0)
        roll = self.roll_dice(1, 20, 0)
        total = roll + mod
        success = total >= dc
        result_label = "success" if success else "failure"
        message = (
            f"[Save] {stat} vs DC {dc}: roll {roll} + {mod} = {total} => {result_label}"
        )
        self.logging_events.add_log_entry(message)
        return (success, total, message)

    # ─────────────────────── Player state remedy ──────────────────────

    @staticmethod
    def player_state_remedy(state: str) -> str:
        """Return a short hint on how to recover from *state*.

        >>> SkillSystem.player_state_remedy("sleeping")
        'wake up'
        """
        remedies = {
            "sleeping": "wake up",
            "unconscious": "receive medical attention",
            "bound": "struggle free",
            "exhausted": "rest and eat",
            "injured": "heal with medicine",
            "dead": "create a new character",
        }
        return remedies.get(state, "recover")

    # ────────────────────────── LLM call logging ──────────────────────

    def log_llm_call(
        self,
        label: str,
        prompt: str,
        response: Optional[str] = None,
        player_name: Optional[str] = None,
    ):
        """Log an LLM request/response to the turn event stream.

        Only writes when the ``llm_logging`` config flag is enabled.
        """
        return

        actor = player_name or self.player_manager.active_player or "__system__"
        message = f"[LLM {label}] Prompt: {prompt[:500]}"
        if response is not None:
            message += f"\n[Response] {response[:500]}"

        self.logging_events.record_turn_event(
            actor, "llm_log", message,
            tick=0,  # caller can patch tick if needed
        )
