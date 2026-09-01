"""Conditions system — manages character status effects with MULTIPLE concurrent
instances per condition (Phase 1 + follow-up, task-trait-condition-system-v2).

The catalog (``CONDITION_DEFINITIONS``, defined in ``player``) is the single
source of truth: each condition has ONE canonical definition. Conditions are
stored per-character as ``{condition_id: [instance, instance, ...]}`` — five
vials of poison are five ``poisoned`` instances. Each instance carries optional
overrides: ``periodic`` (drain), ``ends_on`` (how it ends), ``symptoms``/``known``
(agent perception). Drains sum across instances; gates/mods are presence-based.

``state_timer`` remains as a backward-compat property over the current state
condition's longest finite duration (see ``Player.state_timer``).
"""

from typing import Dict, List, Optional

from engine.player_conditions import (
    CONDITION_DEFINITIONS, CONDITION_HIERARCHY, BLOCKING_CONDITIONS,
    CONDITION_EXCLUSIONS, PERIODIC_CONDITIONS, CONDITION_DEFAULT_TIMERS,
)


def condition_definition(condition: str) -> dict:
    """Return the canonical definition dict for a condition (empty if unknown)."""
    return CONDITION_DEFINITIONS.get(condition, {})


def effective_periodic(condition: str, instance: dict) -> dict:
    """Per-instance periodic drain override, else the catalog default."""
    periodic = instance.get("periodic")
    if periodic is None:
        periodic = CONDITION_DEFINITIONS.get(condition, {}).get("periodic", {})
    return periodic


def effective_ends_on(condition: str, instance: dict) -> list:
    """Per-instance ends_on override, else the catalog default."""
    ends_on = instance.get("ends_on")
    if ends_on is None:
        ends_on = CONDITION_DEFINITIONS.get(condition, {}).get("ends_on", [])
    return ends_on


def effective_known(condition: str, instance: dict) -> bool:
    """Per-instance known override, else the catalog default (True = self-evident)."""
    known = instance.get("known")
    if known is None:
        known = CONDITION_DEFINITIONS.get(condition, {}).get("known", True)
    return known


def effective_symptoms(condition: str, instance: dict) -> dict:
    """Per-instance symptoms override, else the catalog default."""
    symptoms = instance.get("symptoms")
    if symptoms is None:
        symptoms = CONDITION_DEFINITIONS.get(condition, {}).get("symptoms", {})
    return symptoms


def effective_periodic_for(condition: str, instance: dict) -> dict:
    """Per-instance periodic drain, else level-scaled (``level_periodic``),
    else the catalog default. Leveled conditions (exhausted) drain harder at
    higher levels: level 1 → −1 Energy, level 3 → −3, level 6 → −4."""
    periodic = instance.get("periodic")
    if periodic is not None:
        return periodic
    definition = CONDITION_DEFINITIONS.get(condition, {})
    level = instance.get("level")
    level_map = definition.get("level_periodic")
    if level and level_map and level in level_map:
        return level_map[level]
    return definition.get("periodic", {})


def effective_speed_mult(condition: str, instances: list) -> float:
    """The bearer's movement speed multiplier for a condition.

    Presence-based per condition id: instance override → level-scaled
    (``level_speed_mult``, e.g. exhausted) → catalog default.
    """
    for inst in instances or []:
        if "speed_mult" in inst:
            return inst["speed_mult"]
    level = None
    for inst in instances or []:
        if isinstance(inst.get("level"), int) and inst["level"] > 0:
            level = inst["level"]
            break
    definition = CONDITION_DEFINITIONS.get(condition, {})
    level_map = definition.get("level_speed_mult")
    if level and level_map and level in level_map:
        return level_map[level]
    return definition.get("speed_mult", 1.0)


def symptom_for(condition: str, instance: dict) -> Optional[str]:
    """The perception line an agent currently feels for *instance*.

    Symptoms are keyed by progression: min ticks remaining (or `level` for
    leveled diseases). The highest threshold reached wins; ``None`` = the agent
    feels nothing yet (e.g. a freshly-stabbed poison dose).
    """
    symptoms = effective_symptoms(condition, instance)
    if not symptoms:
        return None
    remaining = instance.get("duration")
    level = instance.get("level")
    key = level if isinstance(level, int) and level > 0 else remaining
    if key is None:
        # permanent condition: show the most severe (lowest) threshold
        return symptoms.get(min(symptoms))
    if isinstance(key, int) and key > 0:
        reached = [t for t in symptoms if isinstance(t, int) and t <= key]
        if reached:
            return symptoms.get(max(reached))
    return None


# conditions handled by dedicated prompt lines / system logic, not perception
_PERCEPTION_SKIP = {"awake", "dead", "grappled"}


def frightened_block(player, source_type: str, source_id=None, source_name=None) -> Optional[str]:
    """Return an in-world explanation if *player* fears something of
    *source_type* matching *source_id* or *source_name*; ``None`` otherwise.

    The frightened instance's ``source`` may be a node id or a display name —
    callers pass both. Gate semantics per source type:
      way        — won't use that passage again
      area       — won't re-enter the area
      item       — won't touch the item
      character  — won't approach or attack the character
    """
    for inst in (player.conditions.get("frightened") or []):
        src = inst.get("source")
        if not src or inst.get("source_type") != source_type:
            continue
        if src not in (source_id, source_name):
            continue
        phrases = {
            "way": f"You're too afraid to use the {src} again.",
            "area": f"You're too afraid to go back into the {src}.",
            "item": f"You're too afraid to touch the {src}.",
            "character": f"You're too afraid to even approach {src}.",
        }
        return phrases.get(source_type, f"Your fear of {src} holds you back.")
    return None


def perceived_conditions(player) -> list:
    """The perception lines an agent sees for their active conditions.

    Known conditions render their physical description (instance override wins,
    personalized with the source); hidden conditions render the symptom line for
    the current stage — or nothing yet. Raw condition ids are never exposed.
    Stacked instances each contribute (and identical lines are deduped).
    """
    lines = []
    seen = set()
    for cid in CONDITION_HIERARCHY:
        if cid in _PERCEPTION_SKIP:
            continue
        instances = player.conditions.get(cid) or []
        if not instances:
            continue
        definition = CONDITION_DEFINITIONS.get(cid, {})
        for inst in instances:
            if cid == "frightened" and inst.get("source"):
                text = f"Terrified of {inst['source']}."
            elif effective_known(cid, inst):
                text = inst.get("description") or definition.get("description") or cid
                if inst.get("source"):
                    text = f"{text} (from {inst['source']})"
            else:
                text = symptom_for(cid, inst)
            if text and text not in seen:
                seen.add(text)
                lines.append(text)
    return lines


def _condition_value(condition: str, instances: list, field: str, default):
    """Presence-based lookup: first instance override of *field*, else catalog."""
    for inst in instances or []:
        if field in inst:
            return inst[field]
    return CONDITION_DEFINITIONS.get(condition, {}).get(field, default)


def get_condition_mods(player) -> dict:
    """Aggregate combat modifiers from every active condition on *player*.

    Presence-based: one mod per condition regardless of how many instances it
    has (4 poisons don't multiply attack/defense). ``attack_mod`` applies to the
    character's own rolls; ``defense_mod`` is the character's defense —
    combat applies ``attack + attack_mod - target_defense_mod``, so a NEGATIVE
    defense (helpless conditions) means the attacker effectively gets +X.
    """
    attack_mod = 0
    defense_mod = 0
    for condition, instances in getattr(player, "conditions", {}).items():
        attack_mod += _condition_value(condition, instances, "attack_mod", 0)
        defense_mod += _condition_value(condition, instances, "defense_mod", 0)
    return {"attack_mod": attack_mod, "defense_mod": defense_mod}


def auto_fails_checks(player, sense: str) -> bool:
    """True if any active condition auto-fails checks requiring *sense*."""
    for condition, instances in getattr(player, "conditions", {}).items():
        if sense in _condition_value(condition, instances, "auto_fail_checks", []):
            return True
    return False


def auto_fails_saves(player, stat: str) -> bool:
    """True if any active condition auto-fails saves on ability *stat*."""
    for condition, instances in getattr(player, "conditions", {}).items():
        if stat in _condition_value(condition, instances, "auto_fail_saves", []):
            return True
    return False


def effective_speed(player) -> float:
    """Total movement speed multiplier across all active conditions
    (product of each condition's effective ``speed_mult``)."""
    speed = 1.0
    for condition, instances in getattr(player, "conditions", {}).items():
        speed *= effective_speed_mult(condition, instances)
    return speed


class ConditionsSystem:
    """Manages applying, removing, and processing conditions on characters."""

    def __init__(self, player_manager, game_state):
        self.player_manager = player_manager
        self.gs = game_state

    def apply_condition(self, player_name: str, condition: str,
                        duration: Optional[int] = None, source: Optional[str] = None,
                        level: Optional[int] = None, periodic: Optional[dict] = None,
                        extra_conditions: Optional[list] = None,
                        ends_on: Optional[list] = None, symptoms: Optional[dict] = None,
                        known: Optional[bool] = None,
                        source_type: Optional[str] = None):
        """Apply a condition instance. Duration in ticks (None = permanent)."""
        player = self.player_manager.players.get(player_name)
        if not player:
            return
        if duration is None and condition in CONDITION_DEFAULT_TIMERS:
            duration = CONDITION_DEFAULT_TIMERS[condition]
        player.add_condition(condition, duration=duration, source=source, level=level,
                             periodic=periodic, extra_conditions=extra_conditions,
                             ends_on=ends_on, symptoms=symptoms, known=known,
                             source_type=source_type)
        # drops_held_items — the character lets go of what's in their hands
        if self._effective_drops(player, condition):
            try:
                self.gs.item_actions.drop_held_items(self.gs, player_name)
            except Exception:
                pass

    def _effective_drops(self, player, condition: str) -> bool:
        """Effective ``drops_held_items`` for a condition (instance override wins)."""
        for inst in player.conditions.get(condition) or []:
            if "drops_held_items" in inst:
                return bool(inst["drops_held_items"])
        return bool(CONDITION_DEFINITIONS.get(condition, {}).get("drops_held_items", False))

    def remove_condition(self, player_name: str, condition: str):
        """Remove a condition (ALL of its instances)."""
        player = self.player_manager.players.get(player_name)
        if not player:
            return
        player.remove_condition(condition)

    def has_condition(self, player_name: str, condition: str) -> bool:
        """Check if a player has a condition (any instance present)."""
        player = self.player_manager.players.get(player_name)
        if not player:
            return False
        return player.has_condition(condition)

    def get_condition_instances(self, player_name: str, condition: str) -> List[dict]:
        """Return all per-instance metadata dicts for one condition (empty list)."""
        player = self.player_manager.players.get(player_name)
        if not player:
            return []
        return list(player.conditions.get(condition) or [])

    def can_act(self, player_name: str) -> bool:
        """Check if a player can act (not blocked by conditions)."""
        player = self.player_manager.players.get(player_name)
        if not player:
            return False
        return not bool(set(player.conditions) & set(BLOCKING_CONDITIONS))

    def can_speak(self, player_name: str) -> bool:
        """Check if a player can speak (no blocks_speech condition active)."""
        player = self.player_manager.players.get(player_name)
        if not player:
            return True
        for condition, instances in player.conditions.items():
            if _condition_value(condition, instances, "blocks_speech", False):
                return False
        return True

    def get_active_conditions(self, player_name: str) -> list:
        """Return active conditions with their per-instance metadata."""
        player = self.player_manager.players.get(player_name)
        if not player:
            return []
        result = []
        for c in CONDITION_HIERARCHY:
            instances = player.conditions.get(c)
            if not instances:
                continue
            for inst in instances:
                entry = {"condition": c}
                if isinstance(inst.get("duration"), int):
                    entry["ticks_remaining"] = inst["duration"]
                if inst.get("source"):
                    entry["source"] = inst["source"]
                if inst.get("level"):
                    entry["level"] = inst["level"]
                result.append(entry)
        return result

    def end_conditions(self, player_name: str, action: str) -> list:
        """End every instance whose effective ``ends_on`` includes *action*.

        Per-instance resolution: ``fix`` ends only the broken-leg ``prone``
        instance while ``stand`` ends only a knock-down one. Returns the
        removed ``(condition_id, source)`` pairs.
        """
        player = self.player_manager.players.get(player_name)
        if not player:
            return []
        return player.end_instances(action)

    def process_tick(self):
        """Process per-instance durations and periodic effects for all players.
        Called from tick_turn().

        - Drains SUMMED across every instance of a condition (4 poisons = 4x).
        - Each instance's duration ticks down independently and expires alone.
        - ``unconscious`` is engine-managed: its countdown is owned by
          tick_manager (Energy recovery + wake), not this tick.
        """
        engine_managed = {"unconscious"}
        for pname, player in list(self.player_manager.players.items()):
            if not player.conditions:
                continue

            # Apply periodic effects — instance override first, then level-scaled
            # (exhausted 1→6), then catalog, summed across every instance.
            for cid, instances in list(player.conditions.items()):
                if cid in engine_managed:
                    continue
                total = {}
                for inst in instances:
                    periodic = effective_periodic_for(cid, inst)
                    for stat, amount in periodic.items():
                        total[stat] = total.get(stat, 0) + amount
                for stat, amount in total.items():
                    # Guard: periodic effects must not CREATE vitals (task-206/209).
                    # An arousal periodic on a non-mature world must not leak an
                    # Arousal/Stimulation/Pleasure key into player.vitals.
                    if stat not in player.vitals:
                        continue
                    current = player.vitals.get(stat, 0)
                    player.vitals[stat] = max(0, current + amount)

            # Decrement each timed instance's own duration; remove expired ones
            for cid, instances in list(player.conditions.items()):
                if cid in engine_managed:
                    continue
                kept = []
                for inst in instances:
                    duration = inst.get("duration")
                    if duration is None or duration <= 0:
                        kept.append(inst)
                        continue
                    inst["duration"] = duration - 1
                    if inst["duration"] > 0:
                        kept.append(inst)
                if kept:
                    player.conditions[cid] = kept
                else:
                    player.remove_condition(cid)
