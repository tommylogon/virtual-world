"""Combat system for the virtual world engine.

Handles player-vs-player attacks, weapon discovery, and combat resolution.

@module combat
@contributes attack and grapple resolution, hit dice and restraint
@docs docs/virtualWorld/Rules Engine/Combat System.md
"""

import random
import logging
from typing import Optional, List
from graph import Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_CONNECTION
from engine.vitals import ceiling

logger = logging.getLogger(__name__)

#: Ticks during which a recent attacker counts as provoking self-defense.
RECENT_ATTACK_WINDOW_TICKS = 5


WEAPON_KEYWORDS = [
    "cleaver", "knife", "letter_opener", "hatchet", "axe", "blade",
    "sword", "dagger", "machete", "club", "hammer", "spear", "shiv",
    "chainsaw", "crowbar",
]

# Skill name → relevant stat for damage modifier
SKILL_DAMAGE_STAT = {
    "Athletics": "STR",
    "Acrobatics": "DEX",
    "Stealth": "DEX",
    "Perception": "WIS",
    "Investigation": "INT",
    "Survival": "WIS",
    "Persuasion": "CHA",
    "Performance": "CHA",
    "Medicine": "WIS",
    "Arcana": "INT",
    "Intimidation": "CHA",
    "Lockpicking": "DEX",
}

#: Attack penalty while grappled/restrained (can't fight at full strength).
GRAPPLE_ATTACK_PENALTY = 4
#: Attack bonus when your target is grappled by YOU (they can't dodge).
GRAPPLE_ATTACK_BONUS = 4


class CombatSystem:
    """Handles combat resolution, weapon discovery, and related actions."""

    def __init__(self, graph, skills, ghost_system, npc_behaviors):
        self.graph = graph
        self.skills = skills
        self.ghost_system = ghost_system
        self.npc_behaviors = npc_behaviors

    def _game_state(self):
        """The world behind the ``skills`` handle, when there is one.

        The constructor parameter is a mixed bag: production passes the
        ``VirtualWorld`` itself, while ``tests/test_combat.py`` hands over a
        ``SkillSystem`` that has been monkey-patched with just the handful of
        methods the attack maths calls. So the world is not always reachable
        through ``self.skills`` directly - walk to it when it is there rather
        than assuming either shape, which is what let the death branch below
        raise ``AttributeError`` on a perfectly ordinary test.
        """
        handle = self.skills
        world = getattr(handle, "world", None)
        return world if world is not None and hasattr(world, "players") else handle

    def _can_frightened_self_defend(self, attacker, target) -> bool:
        """True when *attacker* is cornered, grappling, or retaliating against *target*."""
        if attacker.has_condition("grappled") or attacker.has_condition("restrained"):
            return True
        # Actively grappling or grappled by target
        try:
            from engine.character_spatial import _pm_get_player_node_id
            attacker_node = _pm_get_player_node_id(self.skills, attacker.name)
            target_node = _pm_get_player_node_id(self.skills, target.name)
            if attacker_node and target_node:
                for e in self.graph.get_edges_by_type("grappled"):
                    if (e.source == attacker_node and e.target == target_node) or (
                        e.source == target_node and e.target == attacker_node
                    ):
                        return True
        except Exception:
            pass
        # Recently attacked by target
        recent = getattr(attacker, "recent_attackers", None) or {}
        if target.name in recent:
            current_tick = getattr(self.skills, "time_ticks", 0) or 0
            if current_tick - recent[target.name] <= RECENT_ATTACK_WINDOW_TICKS:
                return True
        # Cornered: no unblocked/unlocked exits out of current area
        area_name = getattr(attacker, "current_area", None)
        if area_name and hasattr(self.skills, "_area_node_id"):
            try:
                from engine.conditions import frightened_block
                area_id = self.skills._area_node_id(area_name)
                if area_id:
                    edges = self.graph.get_edges_for_source(area_id, EDGE_CONNECTION)
                    if not edges:
                        return True
                    has_escape = False
                    for edge in edges:
                        way_node = self.graph.get_node(edge.target)
                        if way_node is None:
                            continue
                        if way_node.properties.get("locked"):
                            continue
                        if frightened_block(attacker, "way", source_id=way_node.id, source_name=way_node.name):
                            continue
                        has_escape = True
                        break
                    if not has_escape:
                        return True
            except Exception:
                pass
        return False

    def _emit_combat_fear_hooks(self, attacker_name: str, target_name: str, target, area_name: Optional[str]) -> None:
        """Emit pre-damage combat_threat (target) and witness_combat (bystanders)."""
        gs = self._game_state()
        emit = getattr(gs, "_emit_save_on", None)
        if not callable(emit):
            return
        ctx = {"source": attacker_name, "source_type": "character"}
        try:
            if not target.has_condition("frightened"):
                for line in emit(target_name, "combat_threat", ctx):
                    self.skills.add_log_entry(line)
        except Exception as e:
            logger.warning("[combat] combat_threat %s: %s", target_name, e)
        if not area_name:
            return
        players = getattr(self.skills, "players", None) or {}
        for bname, bplayer in list(players.items()):
            if bname in (attacker_name, target_name):
                continue
            if getattr(bplayer, "state", None) == "dead":
                continue
            if getattr(bplayer, "current_area", None) != area_name:
                continue
            if bplayer.has_condition("frightened"):
                continue
            try:
                for line in emit(bname, "witness_combat", ctx):
                    self.skills.add_log_entry(line)
            except Exception as e:
                logger.warning("[combat] witness_combat %s: %s", bname, e)

    def _wake_on_damage(self, target_name, source=None, source_type=None):
        """Damage interrupts activities (wakes sleepers). Returns wake message."""
        try:
            return self.skills.activities.wake_on_damage(
                target_name, source=source, source_type=source_type
            )
        except Exception:
            return None

    def _armor_wear_text(self, target):
        """Natural-language armor-wear note for a hit (task-161) - never raw
        use counts. Empty string when no tracked armor is equipped."""
        try:
            equipment = self.skills.equipment
            if equipment is None:
                return ""
            wear_msgs = equipment.decrement_armor_uses_on_hit(target)
            if wear_msgs:
                return "\n" + "\n".join(wear_msgs)
        except Exception:
            pass
        return ""

    def _wound_sentence(self, damage: int, damage_type: str, region: str) -> str:
        """Narrative-only wound description - NO hit points, no totals.

        The engine still tracks HP internally; characters live in injuries and
        conditions. Region + severity + damage type drive the prose: a slashing
        hit opens a cut that BLEEDS, a bludgeon swells, and so on. Thresholds
        mirror the condition logic (slashing/piercing bleed at >= 8).
        """
        region = (region or "torso").lower()
        dt = (damage_type or "").lower()
        if dt == "slashing":
            if damage >= 13:
                return f"a deep gash tears open in the {region}, blood seeping steadily."
            if damage >= 8:
                return f"a nasty cut opens in the {region}, blood beading and running."
            return f"a shallow cut opens in the {region}; it barely breaks the skin."
        if dt == "piercing":
            if damage >= 13:
                return f"a deep puncture sinks into the {region}, dark blood welling up."
            return f"a sharp puncture bites into the {region}" + ("; blood wells up." if damage >= 8 else "; a thin trickle of blood.")
        if dt == "bludgeoning":
            if damage >= 13:
                return f"a crushing impact slams into the {region}, the flesh swelling at once."
            return f"a heavy blow slams into the {region}" + (" - the area swells immediately." if damage >= 8 else " - a stinging bruise.")
        if damage >= 8:
            return f"a heavy hit lands in the {region}, knocking the wind out of them."
        return f"a glancing hit lands in the {region}."

    def _dr_mode(self) -> str:
        """The configured damage-reduction mode (task-607).

        Read at call time so switching it mid-session re-resolves the next armed
        hit with no restart. An unknown value degrades to ``flat`` -- the mode
        that preserves historical behaviour -- rather than inventing a fourth.
        """
        from engine.runtime_config import config
        mode = str(config.get("combat.damage_reduction_mode", "flat") or "flat").lower()
        return mode if mode in ("flat", "dice", "percentage") else "flat"

    def _damage_reduction_value(self, target_player) -> tuple:
        """``(flat, dice)`` for the target's worn DR expression.

        ``flat`` is the summed numeric value; ``dice`` is the best ``(count,
        sides)`` or ``None``. Shared by every mode so there is one read of the
        equipment state.
        """
        from engine.equipment_bonuses import aggregate_bonuses
        bonuses = aggregate_bonuses(target_player, self.graph)
        flat = int(bonuses.get("damage_reduction") or 0)
        dice = bonuses.get("damage_reduction_dice")
        return flat, dice if dice and dice[0] > 0 else None

    def _get_target_evasion(self, target_player) -> int:
        """Signed attack-side modifier (task-604). Positive = harder to hit."""
        from engine.equipment_bonuses import aggregate_bonuses
        bonuses = aggregate_bonuses(target_player, self.graph)
        return int(bonuses.get("evasion") or 0)

    def _adjust_damage_dice(self, count: int, target_player) -> tuple:
        """``dice`` mode (task-607): strip DR dice from an incoming damage roll.

        The DR value is read as a *number of damage dice removed* -- `2` removes
        two dice, a `d6` removes 1-6 -- leaving at least one die so a hit never
        vanishes entirely. This runs before the roll, which is what makes armour
        lose dice rather than points; every other mode is a no-op here.

        Returns ``(adjusted_count, stripped)`` so the caller can name the mode in
        the log (review fix, finding 3).
        """
        if self._dr_mode() != "dice":
            return count, 0
        flat, dice = self._damage_reduction_value(target_player)
        remove = flat + (self.skills.roll_dice(dice[0], dice[1], 0) if dice else 0)
        adjusted = max(1, count - remove)
        return adjusted, count - adjusted

    def _apply_damage_reduction(self, damage: int, target_player) -> tuple:
        """Reduce `damage` by the target's worn armour.

        Returns ``(damage, amount, mode, label)`` where ``label`` is a short
        mode-tagged fragment for the combat log (``−2 flat`` / ``−40%``), so a
        soak log distinguishes which mode produced the number.

        task-607: `defense`/`damage_reduction` is a damage *expression* read by
        the same parser the weapon-damage field uses, so a suit can carry `20`
        (flat, and what every existing item carries -- unchanged behaviour) or
        `d8`. The mode (engine config ``combat.damage_reduction_mode``) decides
        what that value does:

        * ``flat`` (default) -- subtract the value; a dice expression is rolled
          per hit, never summed at aggregation.
        * ``percentage`` -- the value is a percent of the incoming blow, so the
          same number blunts a knife and a cannon alike.
        * ``dice`` -- handled before the roll by :meth:`_adjust_damage_dice`; a
          no-op here so the two implementations never both fire.

        The floor is 1 in flat and percentage mode: a landed hit always bruises,
        which is deliberate and unchanged from before task-607. In dice mode the
        floor lives in the dice count (at least one die is always rolled).
        """
        mode = self._dr_mode()
        if mode == "dice":
            return damage, 0, mode, ""
        flat, dice = self._damage_reduction_value(target_player)
        rolled = self.skills.roll_dice(dice[0], dice[1], 0) if dice else 0
        if mode == "percentage":
            pct = max(0, min(100, flat + rolled))
            if pct <= 0:
                return damage, 0, mode, ""
            reduced = max(1, damage - int(round(damage * pct / 100.0)))
            return reduced, damage - reduced, mode, f"−{pct}%"
        total = flat + rolled
        if total <= 0:
            return damage, 0, mode, ""
        return max(1, damage - total), total, mode, f"−{total} flat"

    def player_attack(self, attacker_name: str, target_name: str, weapon_node=None,
                      where=None) -> str:
        """Generic player-vs-player attack. Works for any character.
        Uses attacker's STR for attack roll, target's DEX for defense.
        If weapon_node is provided, uses its damage stat and optional dice/skill/type.
        ``where`` is an optional body-part region id (see engine/body_parts.py):
        on a hit, damage also applies a region-scoped ``injured`` condition
        (and possibly ``bleeding``) if the region is exposed and damage crosses
        the injury threshold (task-253)."""
        from engine.equipment_bonuses import parse_damage, resisted_damage
        from engine.body_parts import (
            resolve_region, injury_region, is_exposed, region_injury_level,
            INJURY_DAMAGE_THRESHOLD, BLEEDING_DAMAGE_THRESHOLD,
        )

        attacker = self.skills.get_player(attacker_name)
        target = self.skills.get_player(target_name)

        if not attacker or not target:
            return ""

        from engine.triggers.behaviors import is_character_hidden, reveal_if_hidden
        gs_for_stealth = self._game_state()

        # Violent action breaks the attacker's own concealment and records feedback.
        reveal_note = reveal_if_hidden(
            gs_for_stealth, attacker_name, reason=f"attacking {target_name}", player=attacker, graph=self.graph
        )
        if reveal_note:
            self.skills.add_log_entry(f"[STEALTH] {reveal_note}")

        # task-309 / task-958: you can only strike what you can see. An unseen
        # target - mundane hidden (player.hidden, state in ('hidden', 'stealthed'),
        # or 'hidden' graph edges), or an unmanifested ghost - can't be aimed at.
        target_visible = True
        try:
            if hasattr(self.skills, "player_manager") and self.skills.player_manager is not None:
                target_visible = self.skills.player_manager.is_visible(target.name)
            elif hasattr(self.skills, "is_visible"):
                target_visible = self.skills.is_visible(target.name)
        except Exception:
            pass
        if not target_visible or is_character_hidden(gs_for_stealth, target.name, graph=self.graph, player=target):
            return (f"{attacker_name} swings at {target_name} - and the blow passes "
                    f"straight through empty air. {target_name} is not there to hit.")

        # Resolve an AIMED body region up front (invalid/unknown → no region).
        # Un-aimed attacks stay None here; the location is rolled on a HIT so
        # misses don't consume a hit-location roll (task-253).
        region = resolve_region(where) if where else None
        region_exposed = is_exposed(target, region, self.graph) if region else False

        from engine.character_spatial import approach_character
        approach_character(self.graph, self.skills, target_name, actor_name=attacker_name)

        # Charmed: the charmed character can't attack their charmer (source-driven)
        for inst in attacker.conditions.get("charmed", []):
            if inst.get("source") == target_name:
                self.skills.add_log_entry(
                    f"[COMBAT] {attacker_name} can't bring themselves to hurt {target_name} (charmed)."
                )
                return f"{attacker_name} hesitates - they can't bring themselves to hurt {target_name}."

        # Frightened (character source): can't attack the character they fear,
        # unless cornered, grappling/grappled by them, or recently attacked by them.
        if attacker.has_condition("frightened"):
            from engine.conditions import frightened_block
            self_defense = self._can_frightened_self_defend(attacker, target)
            block = frightened_block(
                attacker, "character", source_name=target_name, self_defense=self_defense
            )
            if block:
                self.skills.add_log_entry(f"[COMBAT] {attacker_name} is too afraid to attack {target_name}.")
                return f"{attacker_name} trembles - {block}"
            if self_defense and frightened_block(attacker, "character", source_name=target_name):
                self.skills.add_log_entry(
                    f"[COMBAT] {attacker_name} fights back in desperation against {target_name} (frightened)."
                )

        # Record recent attack on target so a frightened defender can retaliate.
        current_tick = getattr(self.skills, "time_ticks", 0) or 0
        recent = getattr(target, "recent_attackers", None)
        if not isinstance(recent, dict):
            recent = {}
            target.recent_attackers = recent
        recent[attacker_name] = current_tick

        # Pre-damage threat and witness fear hooks (e.g. cowardly trait).
        self._emit_combat_fear_hooks(attacker_name, target_name, target, getattr(target, "current_area", None))

        # Decrease target's relationship toward the attacker - catches the "psychotic friend" betrayal case.
        # Through the one write path (task-420) so the cause is recorded: a
        # beating and a shared meal both move the same scalar, and only the
        # trace can tell them apart afterwards.
        try:
            from engine.relationships import apply_relationship_delta
            apply_relationship_delta(
                target, attacker_name, -30, "combat",
                tick=getattr(self.skills, 'time_ticks', 0),
                area_id=getattr(target, "current_area", "") or "",
            )
        except Exception as e:
            logger.warning("[combat] relationship delta %s: %s", attacker_name, e)

        area_name = target.current_area

        # Grapple modifiers (task-4): a held attacker fights at a penalty; a
        # target held by the attacker is easier to hit. "Held by the attacker"
        # = a grappled edge from attacker → target.
        attack_mod = 0
        if attacker.has_condition("grappled") or attacker.has_condition("restrained"):
            attack_mod -= GRAPPLE_ATTACK_PENALTY
        held_by_attacker = False
        if target.has_condition("grappled"):
            from engine.character_spatial import _pm_get_player_node_id
            attacker_node = _pm_get_player_node_id(self.skills, attacker_name)
            target_node = _pm_get_player_node_id(self.skills, target_name)
            held_by_attacker = any(
                e.source == attacker_node and e.target == target_node
                for e in self.graph.get_edges_by_type("grappled")
            )
        if held_by_attacker:
            attack_mod += GRAPPLE_ATTACK_BONUS

        # Condition catalog mods (Phase 1 + follow-up): each condition's
        # attack_mod applies to the bearer's rolls; `defense_mod` is the
        # TARGET's defense, subtracted here - a negative defense (helpless
        # conditions) hands the attacker +X.
        from engine.conditions import get_condition_mods
        attacker_mods = get_condition_mods(attacker)
        target_mods = get_condition_mods(target)
        attack_mod += attacker_mods["attack_mod"] - target_mods["defense_mod"]

        # Auto-select the attacker's best weapon when none was named. "attack X"
        # used to resolve BARE-HANDED even when a butcher carried a cleaver -
        # the weapon just sat unseen in inventory.
        if weapon_node is None:
            weapon_node = self._best_weapon_node(attacker_name)

        # task-518: a ranged weapon needs ammunition. Spend it when the shot is
        # attempted -- a miss still costs the arrow -- and fail cleanly before
        # any roll when the quiver is empty, so no damage is dealt.
        if weapon_node is not None and self._is_ranged_weapon(weapon_node):
            ammo = self._carried_ammo_node(attacker_name)
            if ammo is None:
                ranged_name = weapon_node.properties.get("name") or weapon_node.name
                return (f"{attacker_name} raises the {ranged_name} and reaches for "
                        f"an arrow, but has none. The shot is not taken.")
            self._spend_ammo(ammo)

        # task-477: resolve attack and defense rolls through central checks.resolve()
        from engine import checks
        roll_fn = (lambda: self.skills.roll_dice(1, 20, 0)) if hasattr(self, "skills") and hasattr(self.skills, "roll_dice") else None

        target_evasion = self._get_target_evasion(target)
        atk_extra = [checks.Modifier("attack_mod", attack_mod)] if attack_mod else []
        def_extra = [checks.Modifier("evasion", target_evasion)] if target_evasion else []

        attack_check = checks.resolve(attacker, kind="attack", ability="STR", extra_mods=atk_extra, roll_fn=roll_fn)
        defense_check = checks.resolve(target, kind="defense", ability="DEX", extra_mods=def_extra, roll_fn=roll_fn)

        attack_roll = attack_check.total
        defense_total = defense_check.total
        attack_raw = attack_check.kept
        defense_raw = defense_check.kept
        str_mod_display = next((m.value for m in attack_check.modifiers if m.source == "STR mod"),
                               next((m.value for m in attack_check.modifiers if "STR" in m.source), 0))
        defense_stat_mod = next((m.value for m in defense_check.modifiers if m.source == "DEX mod"),
                                next((m.value for m in defense_check.modifiers if "DEX" in m.source), 0))
        evasion_display = f" + {target_evasion} evasion" if target_evasion else ""

        crit_branch = ""
        if attack_check.tier == "crit_success":
            crit_branch = " (CRIT)"
        elif attack_check.tier == "crit_fail":
            crit_branch = " (CRIT FAIL)"
        elif attack_check.auto_fail:
            crit_branch = " (AUTO-FAIL)"

        atk_mode_note = ""
        if attack_check.mode == "advantage":
            import re
            m_adv = re.search(r"\[advantage[^\]]*\]", attack_check.message)
            atk_mode_note = f" {m_adv.group(0)}" if m_adv else " [advantage]"
        elif attack_check.mode == "disadvantage":
            import re
            m_dis = re.search(r"\[disadvantage[^\]]*\]", attack_check.message)
            atk_mode_note = f" {m_dis.group(0)}" if m_dis else " [disadvantage]"

        def_mode_note = ""
        if defense_check.mode == "advantage":
            import re
            m_adv = re.search(r"\[advantage[^\]]*\]", defense_check.message)
            def_mode_note = f" {m_adv.group(0)}" if m_adv else " [advantage]"
        elif defense_check.mode == "disadvantage":
            import re
            m_dis = re.search(r"\[disadvantage[^\]]*\]", defense_check.message)
            def_mode_note = f" {m_dis.group(0)}" if m_dis else " [disadvantage]"

        atk_breakdown = f"d20({attack_raw}){atk_mode_note} + {str_mod_display} STR + {attack_mod} mod = {attack_roll} (degree: {attack_check.tier}){crit_branch}"
        def_breakdown = f"d20({defense_raw}){def_mode_note} + {defense_stat_mod} DEX = {defense_total}{evasion_display}"

        self.npc_behaviors.process_npcs_on_combat(
            {"combat_actors": [attacker_name, target_name]}
        )

        if attack_check.auto_fail:
            is_hit = False
        elif attack_check.tier == "crit_success":
            is_hit = True
        else:
            is_hit = (attack_roll >= defense_total)

        if is_hit:
            hp_before = target.vitals.get("HP", 0)
# task-538: the target's own ceiling, not a literal. A `or 100`
            # fallback here also swallowed an authored `Max_HP` of 0.
            hp_max = ceiling(target.vitals, "HP")
            # task-607: populated by whichever DR mode fired, for the armor note.
            dr_label = ""

            if weapon_node:
                weapon_props = weapon_node.properties
                weapon_name = weapon_props.get("name", weapon_node.name)

                damage_skill = weapon_props.get("damage_skill", "")
                damage_type = weapon_props.get("damage_type", "")
                damage_stat = SKILL_DAMAGE_STAT.get(damage_skill, "STR")
                stat_value = attacker.stats.get(damage_stat, 10)
                stat_mod = max(0, (stat_value - 10) // 2)

                attack_bonus = attacker.stats.get("attack_bonus", 0) or 0

                parsed = parse_damage(weapon_props.get("damage", 5))
                if parsed[0] > 0:
                    count, sides, flat = parsed
                    # task-607 dice mode: strip DR dice before the roll.
                    rolled_count, dice_stripped = self._adjust_damage_dice(count, target)
                    dmg_mod = stat_mod + flat + (attack_bonus if self.skills.is_slasher(attacker_name) else 0)
                    damage = self.skills.roll_dice(rolled_count, sides, dmg_mod)
                    damage_raw = damage - dmg_mod
                    dmg_desc = f"{rolled_count}d{sides} ({damage_raw}) + {stat_mod} stat + {flat} flat"
                    if dice_stripped:
                        dmg_desc += f" [{dice_stripped} dice stripped]"
                    if self.skills.is_slasher(attacker_name):
                        dmg_desc += f" + {attack_bonus} attack_bonus"
                    damage, _dr, _mode, dr_label = self._apply_damage_reduction(damage, target)
                    if dice_stripped:
                        dr_label = f"−{dice_stripped} dice"
                    dmg_desc += f" = {damage} total, {dr_label} armor" if dr_label else f" = {damage} total, −0 armor"
                else:
                    base_damage = parsed[2] or 5
                    rolled_count, dice_stripped = self._adjust_damage_dice(1, target)
                    dmg_mod = stat_mod + (attack_bonus if self.skills.is_slasher(attacker_name) else 0)
                    damage = self.skills.roll_dice(rolled_count, base_damage, dmg_mod)
                    damage_raw = damage - dmg_mod
                    dmg_desc = f"{rolled_count}d{base_damage} ({damage_raw}) + {stat_mod} stat"
                    if dice_stripped:
                        dmg_desc += f" [{dice_stripped} dice stripped]"
                    if self.skills.is_slasher(attacker_name):
                        dmg_desc += f" + {attack_bonus} attack_bonus"
                    damage, _dr, _mode, dr_label = self._apply_damage_reduction(damage, target)
                    if dice_stripped:
                        dr_label = f"−{dice_stripped} dice"
                    dmg_desc += f" = {damage} total, {dr_label} armor" if dr_label else f" = {damage} total, −0 armor"

                if damage_type:
                    resisted = resisted_damage(damage, damage_type,
                                               {"resistances": self._get_target_resistances(target)})
                    resisted_by = damage - resisted
                    damage = resisted
                    if resisted_by > 0:
                        dmg_desc += f", {resisted_by} resisted ({damage_type})"
                else:
                    resisted_by = 0

                # task-490: an undead identity is its own defence profile.
                # Resistance *halves* and immunity *negates*, which the item
                # aggregate above (a flat subtraction) cannot express, so this is
                # a separate step rather than more entries in that dict. A
                # magical weapon still gets through the weapon-resistance half
                # - that is the 5e rule and the reason a ghost is a problem.
                undead_note = ""
                if damage > 0:
                    from engine import undead as undead_mod
                    profile = undead_mod.resistance_for_weapon(target, weapon_props)
                    mundane_hit = undead_mod.is_nonmagical_weapon(weapon_props)
                    outcome = undead_mod.apply_damage_resistance(
                        damage, damage_type, profile, mundane_hit)
                    if outcome["immune"] or outcome["resisted"]:
                        blocked = damage - outcome["damage"]
                        dmg_desc += f", {blocked} {damage_type} {'immune' if outcome['immune'] else 'resisted'}"
                        undead_note = undead_mod.hit_line(
                            damage, damage_type, profile, target_name, mundane_hit)
                        damage = outcome["damage"]

                uses = weapon_props.get("uses", -1)
                if uses > 0:
                    weapon_props["uses"] = uses - 1
                    from engine.items.carry_weight import reconcile_item_weight
                    reconcile_item_weight(weapon_node)
                target.vitals["HP"] = max(0, target.vitals["HP"] - damage)
                wake_msg = self._wake_on_damage(
                    target_name, source=attacker_name, source_type="character"
                )

                injury_note = ""
                if damage > 0:
                    # task-490: an immune blow did not land, so nothing is cut and
                    # no region is injured. Wounding a ghost for touching it
                    # would be the engine disagreeing with itself in two places.
                    hit_region, hit_region_exposed = self._resolve_hit_region(
                        target, region, region_exposed
                    )
                    injury_target = injury_region(hit_region)
                    from engine.body_parts import BODY_REGIONS
                    region_meta = BODY_REGIONS.get(hit_region, {})
                    region_phrase = region_meta.get("name") if hit_region else ""
                    if hit_region and hit_region_exposed:
                        injury_note = self._apply_region_injury(
                            target, hit_region, injury_target, damage, attacker_name, damage_type
                        )
                else:
                    region_phrase = ""

                # Narrative-first result - NO hit-point numbers. Characters live
                # in wounds and conditions; HP stays engine-internal.
                wound = self._wound_sentence(damage, damage_type, region_phrase)
                armor_note = " Armor blunted the blow." if dr_label else ""
                resist_note = f" ({resisted_by} resisted)" if resisted_by > 0 else ""
                if undead_note:
                    # Nothing solid was struck, so no wound sentence and no
                    # region injury - the blow did not land.
                    wound = undead_note
                self.skills.add_log_entry(
                    f"[COMBAT] {attacker_name} attacks {target_name} with {weapon_name}! "
                    f"Attack {atk_breakdown} vs {def_breakdown}: HIT - {wound}"
                    f" [{dmg_desc}]"
                )
                self.skills.record_turn_event(
                    attacker_name, "combat",
                    f"cuts {target_name} in the {(region_phrase or 'body').lower()} with {weapon_name}",
                    area_name=area_name
                )
                hit_msg = (
                    f"{attacker_name} attacks {target_name} with {weapon_name}!\n"
                    f"  Attack: {atk_breakdown} vs {def_breakdown} → HIT\n"
                    f"  Result: {wound}{armor_note}{resist_note}"
                )
                if wake_msg:
                    hit_msg += f" {wake_msg}"
                if injury_note:
                    hit_msg += f" {target_name} - {injury_note}."
                hit_msg += self._armor_wear_text(target)

                # Stun on hit - driven by weapon stun_chance (0-100) and stun_duration.
                # `stunned` stacks as "refresh": a fresh stun extends the countdown.
                stun_chance = int(weapon_props.get("stun_chance", 0) or 0)
                if stun_chance > 0 and random.randint(1, 100) <= stun_chance:
                    stun_duration = int(weapon_props.get("stun_duration", 2) or 2)
                    target.add_condition("stunned", duration=stun_duration)
                    self.skills.add_log_entry(
                        f"[COMBAT] {attacker_name}'s hit with {weapon_name} stuns {target_name}!"
                    )
                    hit_msg += f" {target_name} is stunned!"
            else:
                str_bonus = max(0, (attacker.stats.get("STR", 10) - 10) // 2)
                _fists_dice, dice_stripped = self._adjust_damage_dice(1, target)
                damage = self.skills.roll_dice(_fists_dice, 4, str_bonus)
                damage_raw = damage - str_bonus
                damage, _dr, _mode, dr_label = self._apply_damage_reduction(damage, target)
                if dice_stripped:
                    dr_label = f"−{dice_stripped} dice"
                dmg_desc = f"{_fists_dice}d4 ({damage_raw}) + {str_bonus} STR"
                if dice_stripped:
                    dmg_desc += f" [{dice_stripped} dice stripped]"
                dmg_desc += f" = {damage} total, {dr_label} armor" if dr_label else f" = {damage} total, −0 armor"
                target.vitals["HP"] = max(0, target.vitals["HP"] - damage)
                wake_msg = self._wake_on_damage(
                    target_name, source=attacker_name, source_type="character"
                )
                injury_note = ""
                hit_region, hit_region_exposed = self._resolve_hit_region(
                    target, region, region_exposed
                )
                injury_target = injury_region(hit_region)
                from engine.body_parts import BODY_REGIONS
                region_meta = BODY_REGIONS.get(hit_region, {})
                region_phrase = region_meta.get("name") if hit_region else ""
                if hit_region and hit_region_exposed:
                    injury_note = self._apply_region_injury(
                        target, hit_region, injury_target, damage, attacker_name, ""
                    )
                wound = self._wound_sentence(damage, "", region_phrase)
                armor_note = " Armor blunted the blow." if dr_label else ""
                self.skills.add_log_entry(
                    f"[COMBAT] {attacker_name} attacks {target_name} with bare hands! "
                    f"Attack {atk_breakdown} vs {def_breakdown}: HIT - {wound}"
                    f" [{dmg_desc}]"
                )
                self.skills.record_turn_event(
                    attacker_name, "combat",
                    f"punches {target_name} in the {(region_phrase or 'body').lower()}",
                    area_name=area_name
                )
                hit_msg = (
                    f"{attacker_name} attacks {target_name} with bare hands!\n"
                    f"  Attack: {atk_breakdown} vs {def_breakdown} → HIT\n"
                    f"  Result: {wound}{armor_note}"
                )
                if wake_msg:
                    hit_msg += f" {wake_msg}"
                if injury_note:
                    hit_msg += f" {target_name} - {injury_note}."
                hit_msg += self._armor_wear_text(target)

            if target.vitals["HP"] <= 0:
                # task-538: one death path. `kill_player` also zeroes HP, drops
                # held items and writes the lived-log record, so a body killed
                # by a sword is indistinguishable from one the cold took. The
                # guard is for the isolated harness, which passes a partial
                # `skills` double with no world behind it - there the original
                # inline handling stands in.
                cause = f"slain by {attacker_name}"
                game_state = self._game_state()
                kill = getattr(game_state, "kill_player", None)
                if callable(kill):
                    kill(target_name, cause, announce=False)
                else:
                    target.state = "dead"
                    self.ghost_system.spawn_body_item(target_name, cause)
                    try:
                        self.skills.item_actions.drop_held_items(
                            self.skills, target_name)
                    except Exception:
                        pass
                self.skills.add_log_entry(f"[{target_name}] has been killed by {attacker_name}!")
                return f"{hit_msg} {target_name} collapses - dead."
            return hit_msg
        else:
            used_weapon = (weapon_node.properties.get('name') or weapon_node.name) if weapon_node else "bare hands"
            self.skills.add_log_entry(
                f"[COMBAT] {attacker_name} attacks {target_name} with {used_weapon}! "
                f"Attack {atk_breakdown} vs {def_breakdown}: MISSED"
            )
            self.skills.record_turn_event(
                attacker_name, "combat",
                f"attacks {target_name} with {used_weapon} and misses" if weapon_node else f"attacks {target_name} bare-handed and misses",
                area_name=area_name
            )
            if weapon_node:
                weapon_name = weapon_node.properties.get('name') or weapon_node.name
                return (
                    f"{attacker_name} swings the {weapon_name} at {target_name} but misses!\n"
                    f"  Attack: {atk_breakdown} vs {def_breakdown} → MISS"
                )
            return (
                f"{attacker_name} lunges at {target_name} with bare hands but misses!\n"
                f"  Attack: {atk_breakdown} vs {def_breakdown} → MISS"
            )

    def _get_target_resistances(self, target_player):
        from engine.equipment_bonuses import aggregate_bonuses
        bonuses = aggregate_bonuses(target_player, self.graph)
        return bonuses.get("resistances", {})

    def _resolve_hit_region(self, target, aimed_region, region_exposed):
        """Resolve the region that actually gets hit.

        Aimed attacks use the pre-resolved region; un-aimed attacks roll a d20
        hit-location on the hit. Returns ``(region, region_exposed)``.
        """
        from engine.body_parts import roll_hit_location, is_exposed, resolve_region
        if aimed_region:
            return aimed_region, region_exposed
        region = roll_hit_location()
        return region, is_exposed(target, region, self.graph)

    def _apply_region_injury(self, target, region, injury_target, damage, attacker_name, damage_type=""):
        """Apply region-scoped injured/bleeding condition instances (task-253).

        Only fires when the region is exposed (not covered by high-coverage
        clothing) and damage crosses the injury threshold. Each body part holds
        its own condition instances via the ``body_part`` override - so a gash
        on the arm and a bruise on the leg are mechanically distinct and heal
        independently (``ends_on: fix`` ends only the matching instances).
        Slashing/piercing wounds bleed at a lower threshold (they cut blood
        vessels - the condition matches the prose in _wound_sentence).
        Returns a human-readable injury note ("" when nothing applies).
        """
        if not region or not injury_target:
            return ""
        from engine.body_parts import (
            region_injury_level, BLEEDING_DAMAGE_THRESHOLD, BODY_REGIONS,
        )
        level = region_injury_level(damage)
        if level <= 0:
            return ""
        region_meta = BODY_REGIONS.get(region, {})
        region_name = region_meta.get("name", region.replace("_", " "))
        notes = []
        target.add_condition(
            "injured", source=attacker_name, level=level,
            overrides={"body_part": injury_target},
        )
        notes.append(f"{region_name} injured (level {level})")
        bleed_threshold = BLEEDING_DAMAGE_THRESHOLD
        if str(damage_type or "").lower() in ("slashing", "piercing"):
            bleed_threshold = min(bleed_threshold, 8)
        if damage >= bleed_threshold:
            target.add_condition(
                "bleeding", source=attacker_name, level=level,
                overrides={"body_part": injury_target},
            )
            notes.append(f"{region_name} is bleeding")
        return "; ".join(notes)

    def _is_ranged_weapon(self, node) -> bool:
        """A ranged weapon declares the ``ranged`` tag (or is a ``bow``)."""
        if node is None or node.type != "item":
            return False
        tags = (node.properties or {}).get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        lowered = {str(t).lower() for t in tags}
        return "ranged" in lowered or "bow" in lowered

    def _carried_ammo_node(self, attacker_name: str) -> Optional[Node]:
        """The first carried/equipped ``ammo`` item, or None (task-518)."""
        from engine.character_spatial import _pm_get_player_node_id
        player_node_id = _pm_get_player_node_id(self.skills, attacker_name)
        if not player_node_id:
            return None
        for edge in (self.graph.get_edges_for_target(player_node_id, EDGE_CARRYING)
                     + self.graph.get_edges_for_target(player_node_id, EDGE_EQUIPPED)):
            node = self.graph.get_node(edge.source)
            if not node or node.type != "item":
                continue
            tags = (node.properties or {}).get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            if any(str(t).lower() == "ammo" for t in tags):
                return node
        return None

    def _spend_ammo(self, ammo_node, count: int = 1) -> None:
        """Decrement one shot from an ammo item; remove it when spent (task-518).

        ``uses`` is the generic charge counter, so a bundle of 20 arrows decrements
        and a single discrete arrow (uses 1) is destroyed. ``uses <= 0`` is
        treated as an inexhaustible supply and left alone.
        """
        props = ammo_node.properties or {}
        try:
            uses = int(props.get("uses", 1))
        except (TypeError, ValueError):
            uses = 1
        if uses <= 0:
            return
        uses -= max(1, int(count or 1))
        props["uses"] = max(0, uses)
        from engine.items.carry_weight import reconcile_item_weight
        reconcile_item_weight(ammo_node)
        if props["uses"] <= 0:
            # Review fix (finding 5): empty through the shared teardown so an
            # authored `on_depleted` / persistent empty state (an empty quiver)
            # is honoured rather than silently stripping the node.
            item_actions = getattr(self.skills, "item_actions", None)
            if item_actions is not None and hasattr(item_actions, "_finish_depleted"):
                item_actions._finish_depleted(ammo_node, "")
            else:
                for edge in list(self.graph.edges):
                    if edge.source == ammo_node.id or edge.target == ammo_node.id:
                        self.graph.edges.remove(edge)
                self.graph.remove_node(ammo_node.id)

    def _find_weapon_in_inventory(self, player_name: str, weapon_name: str) -> Optional[Node]:
        """Find a weapon item node in a player's inventory by name."""
        from engine.character_spatial import _pm_get_player_node_id
        player_node_id = _pm_get_player_node_id(self.skills, player_name)
        weapon_lower = weapon_name.lower()
        for edge in self.graph.get_edges_for_target(player_node_id, EDGE_CARRYING):
            node = self.graph.get_node(edge.source)
            if node and node.type == "item":
                item_props = node.properties or {}
                if node.name.lower() == weapon_lower or weapon_lower in item_props.get("name", "").lower():
                    return node
        return None

    def _best_weapon_node(self, attacker_name: str) -> Optional[Node]:
        """Auto-select the strongest weapon the attacker carries or equips.

        ``attack X`` with no explicit ``with <weapon>`` used to resolve bare
        handed even when the attacker held a weapon - the butcher's cleaver did
        fists while the cleaver sat ignored in inventory. Candidates are item
        nodes with a ``damage`` property or a ``weapon`` tag; highest flat/dice
        damage wins.
        """
        from engine.equipment_bonuses import parse_damage as _parse
        from engine.character_spatial import _pm_get_player_node_id
        player_node_id = _pm_get_player_node_id(self.skills, attacker_name)
        if not player_node_id:
            return None
        best: Optional[Node] = None
        best_score = -1
        seen = set()
        # Carried/equipped edges are item → player (same direction as EDGE_IN),
        # so match edges whose TARGET is the player and take the source item.
        for edge in (self.graph.get_edges_for_target(player_node_id, EDGE_CARRYING)
                     + self.graph.get_edges_for_target(player_node_id, EDGE_EQUIPPED)):
            node = self.graph.get_node(edge.source)
            if not node or node.type != "item" or node.id in seen:
                continue
            seen.add(node.id)
            props = node.properties or {}
            tags = props.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            # task-518: an `ammo` item is a shaft, not a club. A broadhead arrow
            # carries `damage: 0` + `weapon` and used to be auto-selected,
            # rolling `1d0` and "swinging" an arrow.
            if any(t.lower() == "ammo" for t in tags):
                continue
            dmg = props.get("damage", 0) or 0
            if not dmg and "weapon" not in tags:
                continue
            try:
                _count, _sides, flat = _parse(dmg)
                if _count > 0 and _sides > 0:
                    score = _count * (_sides + 1) / 2 + float(flat)  # expected damage
                else:
                    score = float(flat)
            except Exception:
                score = 0
            if score > best_score:
                best = node
                best_score = score
        return best

    # ─────────────────────────── Disarm ───────────────────────────

    def _find_held_hand_items(self, target_name: str, target) -> list:
        """Return list of ``(slot, Node)`` visibly held in target's hands."""
        from engine.character_spatial import _pm_get_player_node_id
        from engine.equipment import is_intrinsic_ability

        target_id = _pm_get_player_node_id(self.skills, target_name)
        found = []
        seen_ids = set()

        # Prefer hand_right then hand_left from graph EDGE_EQUIPPED
        by_slot = {"hand_right": [], "hand_left": []}
        for edge in self.graph.get_edges_for_target(target_id, EDGE_EQUIPPED):
            slot = (edge.properties or {}).get("slot")
            if slot in by_slot:
                by_slot[slot].append(edge.source)

        # Also include player.equipped stacks in case graph edges omit slot
        equipped = getattr(target, "equipped", None) or {}
        for slot in ("hand_right", "hand_left"):
            for raw_id in list(equipped.get(slot) or []) + by_slot[slot]:
                if not raw_id:
                    continue
                real_id = str(raw_id).replace("__multi_slot_", "") if str(raw_id).startswith("__multi_slot_") else raw_id
                if real_id in seen_ids:
                    continue
                node = self.graph.get_node(real_id)
                if not node or node.type != "item":
                    continue
                props = node.properties or {}
                if props.get("concealed") or is_intrinsic_ability(node):
                    continue
                seen_ids.add(real_id)
                found.append((slot, node))
        return found

    def _free_hand_slot(self, player_name: str, player) -> Optional[str]:
        """Return an available hand slot (``hand_right`` or ``hand_left``), or None."""
        from engine.character_spatial import _pm_get_player_node_id

        disabled = set()
        try:
            from engine.traits import TraitSystem
            disabled = set(TraitSystem.get_disabled_slots(player) or ())
        except Exception:
            pass

        player_id = _pm_get_player_node_id(self.skills, player_name)
        equipped = getattr(player, "equipped", None) or {}
        graph_hand_slots = set()
        for edge in self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED):
            slot = (edge.properties or {}).get("slot")
            if slot in ("hand_right", "hand_left"):
                graph_hand_slots.add(slot)

        for slot in ("hand_right", "hand_left"):
            if slot in disabled:
                continue
            if not (equipped.get(slot) or []) and slot not in graph_hand_slots:
                return slot
        return None

    def _area_node_id(self, area_name: Optional[str]) -> Optional[str]:
        """Resolve graph node id for an area name."""
        if not area_name:
            return None
        candidate = f"area_{area_name.lower().replace(' ', '_')}"
        node = self.graph.get_node(candidate)
        if node:
            return node.id
        for node in self.graph.nodes.values():
            if node.type == "area" and node.name == area_name:
                return node.id
        return None

    def player_disarm(self, attacker_name: str, target_name: str,
                      item_name: Optional[str] = None, catch: bool = False) -> str:
        """Non-lethal contested disarm to wrest a visibly held item from target.

        Resolves an opposed Athletics/STR/DEX check against the target's grip
        (honoring weapon size, two-handed grip, prone/frightened modifiers, and
        ``approach_character``). On success, moves the item off the target's
        hand slot onto the disarmer (when ``catch=True`` and a hand is free) or
        drops it to the area floor, firing ``on_unequip`` triggers without
        dealing HP damage. Records a structured ``'disarm'`` turn_event.
        """
        from engine.checks import resolve as check_resolve

        attacker = self.skills.get_player(attacker_name)
        target = self.skills.get_player(target_name)
        if not attacker or not target:
            return ""
        if attacker_name == target_name:
            return f"{attacker_name} cannot disarm themselves."

        from engine.triggers.behaviors import is_character_hidden, reveal_if_hidden
        gs_for_stealth = self._game_state()
        reveal_note = reveal_if_hidden(
            gs_for_stealth, attacker_name, reason=f"disarming {target_name}", player=attacker, graph=self.graph
        )
        if reveal_note:
            self.skills.add_log_entry(f"[STEALTH] {reveal_note}")

        target_visible = True
        try:
            if hasattr(self.skills, "player_manager") and self.skills.player_manager is not None:
                target_visible = self.skills.player_manager.is_visible(target.name)
            elif hasattr(self.skills, "is_visible"):
                target_visible = self.skills.is_visible(target.name)
        except Exception:
            pass
        if not target_visible or is_character_hidden(gs_for_stealth, target.name, graph=self.graph, player=target):
            return (f"{attacker_name} reaches to disarm {target_name} - "
                    f"but {target_name} is not there to grab.")

        from engine.character_spatial import approach_character, _pm_get_player_node_id
        approach_character(self.graph, self.skills, target_name, actor_name=attacker_name)

        # Charmed / Frightened blocks mirror player_attack
        for inst in attacker.conditions.get("charmed", []):
            if inst.get("source") == target_name:
                self.skills.add_log_entry(
                    f"[COMBAT] {attacker_name} can't bring themselves to disarm {target_name} (charmed)."
                )
                return f"{attacker_name} hesitates - they can't bring themselves to disarm {target_name}."

        if attacker.has_condition("frightened"):
            from engine.conditions import frightened_block
            self_defense = self._can_frightened_self_defend(attacker, target)
            block = frightened_block(
                attacker, "character", source_name=target_name, self_defense=self_defense
            )
            if block:
                self.skills.add_log_entry(f"[COMBAT] {attacker_name} is too afraid to disarm {target_name}.")
                return f"{attacker_name} trembles - {block}"

        held_items = self._find_held_hand_items(target_name, target)
        if not held_items:
            return f"{target_name} isn't holding anything to disarm."

        chosen_slot = None
        item_node = None
        if item_name:
            wanted = item_name.lower().replace("_", " ").replace("-", " ").strip()
            for slot, node in held_items:
                norm = (node.properties.get("name") or node.name).lower().replace("_", " ").replace("-", " ")
                if wanted == norm:
                    chosen_slot, item_node = slot, node
                    break
            if item_node is None:
                for slot, node in held_items:
                    norm = (node.properties.get("name") or node.name).lower().replace("_", " ").replace("-", " ")
                    if wanted in norm:
                        chosen_slot, item_node = slot, node
                        break
            if item_node is None:
                return f"{target_name} isn't holding a '{item_name}' to disarm."
        else:
            chosen_slot, item_node = held_items[0]

        item_label = item_node.properties.get("name") or item_node.name
        props = item_node.properties or {}

        # Mark recent hostility so frightened target can retaliate
        current_tick = getattr(self.skills, "time_ticks", 0) or 0
        recent = getattr(target, "recent_attackers", None)
        if not isinstance(recent, dict):
            recent = {}
            target.recent_attackers = recent
        recent[attacker_name] = current_tick

        area_name = getattr(target, "current_area", None)
        self._emit_combat_fear_hooks(attacker_name, target_name, target, area_name)

        # Opposed check: Attacker (Athletics with STR or DEX, whichever is higher)
        # vs Defender (best of Athletics / Acrobatics, with grip & size modifiers).
        atk_str = (attacker.stats or {}).get("STR", 10)
        atk_dex = (attacker.stats or {}).get("DEX", 10)
        atk_ability = "DEX" if atk_dex > atk_str else "STR"

        def_skills = target.skills or {}
        def_kind = "Acrobatics" if def_skills.get("Acrobatics", 0) > def_skills.get("Athletics", 0) else "Athletics"

        def_mods = []
        tags = props.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip().lower() for t in tags.split(",")]
        else:
            tags = [str(t).lower() for t in tags]

        equip_slots = props.get("equip_slots") or []
        two_handed = bool(props.get("two_handed")) or "two_handed" in tags or (
            isinstance(equip_slots, (list, tuple))
            and "hand_left" in equip_slots and "hand_right" in equip_slots
            and props.get("requires_both_hands", False)
        )
        # Also detect two-handed if marker exists in the opposite hand
        marker = f"__multi_slot_{item_node.id}"
        target_equipped = getattr(target, "equipped", None) or {}
        if any(str(x) == marker for s in ("hand_left", "hand_right") for x in (target_equipped.get(s) or [])):
            two_handed = True
        if two_handed:
            def_mods.append(("two-handed grip", 2))

        size = str(props.get("size", "")).lower()
        weight = float(props.get("weight", 1.0) or 1.0)
        if size in ("large", "heavy") or weight >= 5.0:
            def_mods.append(("heavy item", 2))
        elif size in ("tiny", "small") or weight <= 0.5:
            def_mods.append(("light item", -1))

        atk_dis = attacker.has_condition("prone") or getattr(attacker, "state", "") == "prone" or attacker.has_condition("frightened")
        def_dis = target.has_condition("prone") or getattr(target, "state", "") == "prone" or target.has_condition("frightened")

        roll_fn = lambda: self.skills.roll_dice(1, 20)
        atk_res = check_resolve(
            attacker, kind="Athletics", ability=atk_ability,
            disadvantage=atk_dis, roll_fn=roll_fn,
        )
        def_res = check_resolve(
            target, kind=def_kind,
            disadvantage=def_dis, extra_mods=def_mods, roll_fn=roll_fn,
        )
        success = (not atk_res.auto_fail) and (def_res.auto_fail or atk_res.total > def_res.total)

        gs = self._game_state()
        triggers = getattr(gs, "triggers", None) if gs else None
        equip_sys = getattr(gs, "equipment", None) if gs else None
        target_id = _pm_get_player_node_id(self.skills, target_name)
        attacker_id = _pm_get_player_node_id(self.skills, attacker_name)

        def _record_disarm_event(outcome_str: str, desc: str) -> None:
            extra_meta = {
                "target": target_name,
                "item": item_label,
                "outcome": outcome_str,
            }
            try:
                self.skills.record_turn_event(
                    attacker_name, "disarm", desc, area_name=area_name, extra=extra_meta
                )
            except TypeError:
                self.skills.record_turn_event(
                    attacker_name, "disarm", desc, area_name=area_name
                )

        if success:
            # Remove from defender's equipped slots and graph edges
            for s in list(target_equipped.keys()):
                target_equipped[s] = [
                    x for x in target_equipped[s]
                    if x != item_node.id and str(x) != marker
                ]
            for edge in list(self.graph.get_edges_for_target(target_id, EDGE_EQUIPPED)):
                if edge.source == item_node.id:
                    self.graph.remove_edge(edge.source, edge.target, EDGE_EQUIPPED)
            self.graph.remove_edge(item_node.id, target_id, EDGE_CARRYING)
            self.graph.remove_edges_for_node(item_node.id, EDGE_CONNECTION)

            if triggers is not None and hasattr(triggers, "_execute_triggers"):
                triggers._execute_triggers(item_node, "on_unequip", game_state=gs)
            if equip_sys is not None:
                if hasattr(equip_sys, "_maybe_revoke_granted_ability"):
                    equip_sys._maybe_revoke_granted_ability(target_name, item_node)
                if hasattr(equip_sys, "_maybe_update_equipment_description"):
                    equip_sys._maybe_update_equipment_description(target)

            free_hand = self._free_hand_slot(attacker_name, attacker) if catch else None
            if catch and free_hand:
                self.graph.add_edge(Edge(
                    source=item_node.id,
                    target=attacker_id,
                    type=EDGE_EQUIPPED,
                    properties={"slot": free_hand, "layer": 1},
                ))
                if not isinstance(getattr(attacker, "equipped", None), dict):
                    attacker.equipped = {}
                attacker.equipped.setdefault(free_hand, []).append(item_node.id)
                if triggers is not None and hasattr(triggers, "_execute_triggers"):
                    triggers._execute_triggers(item_node, "on_equip", game_state=gs)
                if equip_sys is not None and hasattr(equip_sys, "_maybe_update_equipment_description"):
                    equip_sys._maybe_update_equipment_description(attacker)
                where_text = f"catching it in their {free_hand.replace('_', ' ')}"
            else:
                area_id = self._area_node_id(area_name)
                if area_id:
                    self.graph.add_edge(Edge(source=item_node.id, target=area_id, type=EDGE_IN))
                where_text = "knocking it to the ground"

            self.skills.add_log_entry(
                f"[COMBAT] {attacker_name} disarms {item_label} from {target_name}! "
                f"({atk_res.total} vs {def_res.total}) - {where_text}."
            )
            _record_disarm_event("success", f"disarmed {item_label} from {target_name}, {where_text}")
            return (
                f"{attacker_name} wrests the {item_label} from {target_name}'s grip, {where_text}!\n"
                f"  Disarm: {atk_res.total} vs {def_res.total} -> SUCCESS"
            )
        else:
            self.skills.add_log_entry(
                f"[COMBAT] {attacker_name} tries to disarm {item_label} from {target_name}, "
                f"but {target_name} keeps their grip ({atk_res.total} vs {def_res.total})."
            )
            _record_disarm_event("failed", f"tried to disarm {item_label} from {target_name} and failed")
            return (
                f"{attacker_name} lunges for {target_name}'s {item_label}, "
                f"but {target_name} keeps their grip!\n"
                f"  Disarm: {atk_res.total} vs {def_res.total} -> FAIL"
            )
