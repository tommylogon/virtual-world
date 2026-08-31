"""Combat system for the virtual world engine.

Handles player-vs-player attacks, weapon discovery, and combat resolution.
"""

import random
from typing import Optional, List
from graph import Node, EDGE_CARRYING, EDGE_EQUIPPED


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

    def _wake_on_damage(self, target_name, source=None, source_type=None):
        """Damage interrupts activities (wakes sleepers). Returns wake message."""
        try:
            return self.skills.activities.wake_on_damage(
                target_name, source=source, source_type=source_type
            )
        except Exception:
            return None

    def _armor_wear_text(self, target):
        """Natural-language armor-wear note for a hit (task-161) — never raw
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
        """Narrative-only wound description — NO hit points, no totals.

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
            return f"a heavy blow slams into the {region}" + (" — the area swells immediately." if damage >= 8 else " — a stinging bruise.")
        if damage >= 8:
            return f"a heavy hit lands in the {region}, knocking the wind out of them."
        return f"a glancing hit lands in the {region}."

    def _get_target_defense(self, target_player):
        from engine.equipment_bonuses import aggregate_bonuses, resisted_damage
        bonuses = aggregate_bonuses(target_player, self.graph)
        return bonuses["defense"]

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
                return f"{attacker_name} hesitates — they can't bring themselves to hurt {target_name}."

        # Frightened (character source): can't attack the character they fear
        if attacker.has_condition("frightened"):
            from engine.conditions import frightened_block
            block = frightened_block(attacker, "character", source_name=target_name)
            if block:
                self.skills.add_log_entry(f"[COMBAT] {attacker_name} is too afraid to attack {target_name}.")
                return f"{attacker_name} trembles — {block}"

        # Decrease target's relationship toward the attacker — catches the "psychotic friend" betrayal case
        target_rel = target.relationships.get(attacker_name, {"closeness": 0})
        target_rel["closeness"] = max(-100, target_rel["closeness"] - 30)
        target_rel["last_interaction_tick"] = getattr(self.skills, 'time_ticks', 0)
        target_rel.setdefault("interaction_count", 0)
        target_rel["interaction_count"] += 1
        target.relationships[attacker_name] = target_rel

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
        # TARGET's defense, subtracted here — a negative defense (helpless
        # conditions) hands the attacker +X.
        from engine.conditions import get_condition_mods
        attacker_mods = get_condition_mods(attacker)
        target_mods = get_condition_mods(target)
        attack_mod += attacker_mods["attack_mod"] - target_mods["defense_mod"]

        # Auto-select the attacker's best weapon when none was named. "attack X"
        # used to resolve BARE-HANDED even when a butcher carried a cleaver —
        # the weapon just sat unseen in inventory.
        if weapon_node is None:
            weapon_node = self._best_weapon_node(attacker_name)

        attack_roll = self.skills.roll_dice(1, 20, attacker.stats.get("STR", 10) + attack_mod)
        defense_roll = self.skills.roll_dice(1, 20, target.stats.get("DEX", 10))

        # Break the totals back into raw die + modifier for the breakdown.
        attack_raw = attack_roll - (attacker.stats.get("STR", 10) + attack_mod)
        defense_raw = defense_roll - target.stats.get("DEX", 10)
        str_mod_display = max(0, (attacker.stats.get("STR", 10) - 10) // 2)

        self.npc_behaviors.process_npcs_on_combat(
            {"combat_actors": [attacker_name, target_name]}
        )

        if attack_roll >= defense_roll:
            target_defense = self._get_target_defense(target)
            hp_before = target.vitals.get("HP", 0)
            hp_max = target.vitals.get("Max_HP", 100) or 100

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
                    dmg_mod = stat_mod + flat + (attack_bonus if self.skills.is_slasher(attacker_name) else 0)
                    damage = self.skills.roll_dice(count, sides, dmg_mod)
                    damage_raw = damage - dmg_mod
                    dmg_desc = f"{count}d{sides} ({damage_raw}) + {stat_mod} stat + {flat} flat"
                    if self.skills.is_slasher(attacker_name):
                        dmg_desc += f" + {attack_bonus} attack_bonus"
                    damage = max(1, damage - target_defense)
                    dmg_desc += f" = {damage} total, −{target_defense} armor" if target_defense > 0 else f" = {damage} total, −0 armor"
                else:
                    base_damage = parsed[2] or 5
                    dmg_mod = stat_mod + (attack_bonus if self.skills.is_slasher(attacker_name) else 0)
                    damage = self.skills.roll_dice(1, base_damage, dmg_mod)
                    damage_raw = damage - dmg_mod
                    dmg_desc = f"1d{base_damage} ({damage_raw}) + {stat_mod} stat"
                    if self.skills.is_slasher(attacker_name):
                        dmg_desc += f" + {attack_bonus} attack_bonus"
                    damage = max(1, damage - target_defense)
                    dmg_desc += f" = {damage} total, −{target_defense} armor" if target_defense > 0 else f" = {damage} total, −0 armor"

                if damage_type:
                    resisted = resisted_damage(damage, damage_type,
                                               {"resistances": self._get_target_resistances(target)})
                    resisted_by = damage - resisted
                    damage = resisted
                    if resisted_by > 0:
                        dmg_desc += f", {resisted_by} resisted ({damage_type})"
                else:
                    resisted_by = 0

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

                # Narrative-first result — NO hit-point numbers. Characters live
                # in wounds and conditions; HP stays engine-internal.
                wound = self._wound_sentence(damage, damage_type, region_phrase)
                armor_note = " Armor blunted the blow." if target_defense > 0 else ""
                resist_note = f" ({resisted_by} resisted)" if resisted_by > 0 else ""
                self.skills.add_log_entry(
                    f"[COMBAT] {attacker_name} attacks {target_name} with {weapon_name}! "
                    f"Attack d20({attack_raw}) + {attacker.stats.get('STR', 10)} STR + {attack_mod} mod = {attack_roll} "
                    f"vs d20({defense_raw}) + {target.stats.get('DEX', 10)} DEX = {defense_roll}: HIT — {wound}"
                )
                self.skills.record_turn_event(
                    attacker_name, "combat",
                    f"cuts {target_name} in the {(region_phrase or 'body').lower()} with {weapon_name}",
                    area_name=area_name
                )
                hit_msg = (
                    f"{attacker_name} attacks {target_name} with {weapon_name}!\n"
                    f"  Attack: d20({attack_raw}) + {attacker.stats.get('STR', 10)} STR + {attack_mod} mod = {attack_roll} "
                    f"vs d20({defense_raw}) + {target.stats.get('DEX', 10)} DEX = {defense_roll} → HIT\n"
                    f"  Result: {wound}{armor_note}{resist_note}"
                )
                if wake_msg:
                    hit_msg += f" {wake_msg}"
                if injury_note:
                    hit_msg += f" {target_name} — {injury_note}."
                hit_msg += self._armor_wear_text(target)

                # Stun on hit — driven by weapon stun_chance (0-100) and stun_duration.
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
                damage = self.skills.roll_dice(1, 4, str_bonus)
                damage_raw = damage - str_bonus
                damage = max(1, damage - target_defense)
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
                armor_note = " Armor blunted the blow." if target_defense > 0 else ""
                self.skills.add_log_entry(
                    f"[COMBAT] {attacker_name} attacks {target_name} with bare hands! "
                    f"Attack d20({attack_raw}) + {attacker.stats.get('STR', 10)} STR + {attack_mod} mod = {attack_roll} "
                    f"vs d20({defense_raw}) + {target.stats.get('DEX', 10)} DEX = {defense_roll}: HIT — {wound}"
                )
                self.skills.record_turn_event(
                    attacker_name, "combat",
                    f"punches {target_name} in the {(region_phrase or 'body').lower()}",
                    area_name=area_name
                )
                hit_msg = (
                    f"{attacker_name} attacks {target_name} with bare hands!\n"
                    f"  Attack: d20({attack_raw}) + {attacker.stats.get('STR', 10)} STR + {attack_mod} mod = {attack_roll} "
                    f"vs d20({defense_raw}) + {target.stats.get('DEX', 10)} DEX = {defense_roll} → HIT\n"
                    f"  Result: {wound}{armor_note}"
                )
                if wake_msg:
                    hit_msg += f" {wake_msg}"
                if injury_note:
                    hit_msg += f" {target_name} — {injury_note}."
                hit_msg += self._armor_wear_text(target)

            if target.vitals["HP"] <= 0:
                target.state = "dead"
                self.ghost_system.spawn_body_item(target_name, f"slain by {attacker_name}")
                # drops_held_items — death: what was in the hands falls to the floor
                try:
                    self.skills.item_actions.drop_held_items(self.skills, target_name)
                except Exception:
                    pass
                self.skills.add_log_entry(f"[{target_name}] has been killed by {attacker_name}!")
                return f"{hit_msg} {target_name} collapses — dead."
            return hit_msg
        else:
            self.skills.add_log_entry(
                f"[COMBAT] {attacker_name} attacks {target_name} with bare hands! "
                f"Attack d20({attack_raw}) + {attacker.stats.get('STR', 10)} STR + {attack_mod} mod = {attack_roll} "
                f"vs d20({defense_raw}) + {target.stats.get('DEX', 10)} DEX = {defense_roll}: MISSED"
            )
            self.skills.record_turn_event(
                attacker_name, "combat",
                f"attacks {target_name} bare-handed and misses",
                area_name=area_name
            )
            if weapon_node:
                weapon_name = weapon_node.properties.get('name') or weapon_node.name
                return (
                    f"{attacker_name} swings the {weapon_name} at {target_name} but misses!\n"
                    f"  Attack: d20({attack_raw}) + {attacker.stats.get('STR', 10)} STR + {attack_mod} mod = {attack_roll} "
                    f"vs d20({defense_raw}) + {target.stats.get('DEX', 10)} DEX = {defense_roll} → MISS"
                )
            return (
                f"{attacker_name} lunges at {target_name} with bare hands but misses!\n"
                f"  Attack: d20({attack_raw}) + {attacker.stats.get('STR', 10)} STR + {attack_mod} mod = {attack_roll} "
                f"vs d20({defense_raw}) + {target.stats.get('DEX', 10)} DEX = {defense_roll} → MISS"
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
        its own condition instances via the ``body_part`` override — so a gash
        on the arm and a bruise on the leg are mechanically distinct and heal
        independently (``ends_on: fix`` ends only the matching instances).
        Slashing/piercing wounds bleed at a lower threshold (they cut blood
        vessels — the condition matches the prose in _wound_sentence).
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
        handed even when the attacker held a weapon — the butcher's cleaver did
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
