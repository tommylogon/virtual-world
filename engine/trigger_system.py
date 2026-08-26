"""Trigger system for the virtual world engine.

Manages trigger registration, condition evaluation, and effect execution
for item interactions, NPC behaviors, and world events.
"""

import random
import re
from typing import Any, Dict, List, Optional

from graph import Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_TRIGGERS, EDGE_CONNECTION
from .effects import Effects
from .item_actions import normalize_item_actions

# ─────────────────── Constants ───────────────────

TRIGGER_TYPES = [
    "on_take",
    "on_drop",
    "on_examine",
    "on_inspect",
    "on_use",
    "on_use_on",
    "on_look",
    "on_search",
    "on_tick",
    "on_eat",
    "on_drink",
    "on_read",
    "on_light",
    "on_activate",
    "on_equip",
    "on_unequip",
    "on_throw",
    "on_break",
    "on_depleted",
    "on_toggle_on",
    "on_toggle_off",
    "on_open",
    "on_close",
    "on_state_enter",
    "on_state_exit",
    "on_auto_open",
    "on_enter",
    "on_speech",
    "on_fail_jump",
    "on_fail_climb",
    "on_delayed",
]

EFFECT_TYPES = [
    "destroy_self",
    "message",
    "damage",
    "save",
    "heal",
    "spawn_item",
    "spawn_character",
    "give_item",
    "remove_item",
    "consume_item",
    "set_state",
    "set_environment",
    "teleport",
    "rename",
    "unlock_way",
    "drain",
    "set_description",
    "append_description",
    "adjust_vital",
    "adjust_environment",
    "set_hidden",
    "adjust_uses",
    "end_scenario",
    "restart_scenario",
    "apply_condition",
    "remove_condition",
    "apply_trait",
    "remove_trait",
    "add_tag",
    "remove_tag",
    "set_parameter",
    "adjust_parameter",
    "surface_memory",
    "suppress_memory",
    "unblock_memory",
    "schedule_trigger",
]


def _legacy_effects_from_properties(props: dict) -> Optional[List[dict]]:
    """Synthesize ``effects[]`` from pre-migration ``effect_type`` + ``effect_params``."""
    effect_type = props.get("effect_type")
    if isinstance(effect_type, list):
        effect_type = effect_type[0] if effect_type else None
    if not effect_type:
        return None
    effect_type = str(effect_type)

    raw_params = props.get("effect_params")
    params = dict(raw_params) if isinstance(raw_params, dict) else {}

    if effect_type == "message":
        message_params = dict(params)
        if not message_params.get("message"):
            message_params["message"] = props.get("success_message") or ""
        if props.get("fail_message") and not message_params.get("fail_message"):
            message_params["fail_message"] = props.get("fail_message")
        return [{"type": "message", "params": message_params}]

    if effect_type == "damage":
        narrative = params.pop("message", None)
        effects = [{"type": "damage", "params": params}]
        if narrative and str(narrative).strip():
            effects.append({"type": "message", "params": {"message": narrative}})
        return effects

    return [{"type": effect_type, "params": params}]


def _effects_list_from_properties(props: Optional[dict]) -> Optional[List[dict]]:
    """Return ``effects[]`` from props, falling back to legacy flat fields."""
    if not props:
        return None

    effects = props.get("effects")
    if isinstance(effects, list) and effects:
        typed = [effect for effect in effects if isinstance(effect, dict) and effect.get("type")]
        if typed:
            return typed

    return _legacy_effects_from_properties(props)


def _resolve_trigger_effects(trigger_edge: Edge, graph) -> List[dict]:
    """Resolve trigger effects from edge props, then linked trigger node, then legacy fields."""
    sources = [trigger_edge.properties]
    target_node = graph.get_node(trigger_edge.target)
    if target_node:
        sources.append(target_node.properties)

    for props in sources:
        resolved = _effects_list_from_properties(props)
        if resolved:
            return resolved

    return [{"type": "message", "params": {}}]


class TriggerSystem:
    """Evaluates trigger conditions and executes their effects.

    Depends on a WorldGraph, a skill-check service, and a logging
    callback.  All three are injected via the constructor.

    Most public methods accept a *game_state* object (duck-typed)
    that provides access to the mutable world state — player data,
    area helpers, scenario flags, etc.
    """

    def __init__(self, graph, skills, logging_events):
        """Initialise the trigger system.

        Parameters
        ----------
        graph : WorldGraph
            The world graph instance.
        skills : object
            An object providing a ``skill_check(skill_name, dc)`` method.
        logging_events : object
            An object providing an ``add_log_entry(text)`` method.
        """
        self.graph = graph
        self.skills = skills
        self.logging_events = logging_events
        self._last_skill_check_msg: Optional[str] = None
        self._last_save_msg: Optional[str] = None
        self._effects = Effects(graph, logging_events)
        self._effects.set_trigger_system(self)

    # ─────────────────── Item lookup helpers ───────────────────

    def _find_item_by_name(self, name: str, game_state=None):
        """Find an item node in the graph by name."""
        if not name:
            return None
        name_lower = name.lower()
        for node in self.graph.nodes.values():
            if node.type == "item":
                node_name = (node.name or node.properties.get("name", "")).lower()
                if node_name == name_lower:
                    return node
        return None

    def _find_target_node(self, name: str, game_state=None):
        """Resolve the used-on target node for an on_use_on interaction.

        Matches by name across *all* node types (items, ways, areas,
        characters), so tags can be checked on any of them. For ways,
        also tries exit-direction matching in the current area so phrases
        like "the north door" resolve to the door node.
        """
        if not name:
            return None
        needle = str(name).lower().strip()
        for node in self.graph.nodes.values():
            if (node.name or "").lower() == needle:
                return node
        if game_state is not None:
            try:
                area_id = game_state.get_current_area_id()
            except Exception:
                area_id = None
            if area_id:
                resolver = getattr(game_state, "resolve_exit", None)
                if resolver:
                    try:
                        _, way_node, _ = resolver(area_id, name)
                    except Exception:
                        way_node = None
                    if way_node:
                        return way_node
                matcher = getattr(game_state, "_match_exit_direction", None)
                matched_dir = None
                if matcher:
                    try:
                        matched_dir = matcher(area_id, name)
                    except Exception:
                        matched_dir = None
                if matched_dir:
                    for edge in self.graph.get_edges_for_source(area_id, EDGE_CONNECTION):
                        if edge.properties.get("direction", "") == matched_dir:
                            return self.graph.get_node(edge.target)
        return None

    # ─────────────────── Template rendering ───────────────────

    def _render_template(self, text: str, context: dict) -> str:
        """Replace ``{variable}`` placeholders with values from *context*.

        Supported patterns:

        * ``{variable_name}`` — direct lookup in the context dict.
        * ``{param:<key>}`` — lookup in ``context['item_params']``.
        * ``{prop:<key>}`` — lookup in ``context['item_properties']``.

        Unrecognised variables are left unchanged.
        """
        if not text:
            return text
        item_props = context.get("item_properties", {})
        if item_props:
            text = re.sub(
                r"\{prop:(\w+)\}",
                lambda m: str(item_props.get(m.group(1), m.group(0))),
                text,
            )
        item_params = context.get("item_params", {})
        if item_params:
            text = re.sub(
                r"\{param:(\w+)\}",
                lambda m: str(item_params.get(m.group(1), m.group(0))),
                text,
            )
        for key, value in context.items():
            if key in ("item_params", "item_properties"):
                continue
            text = text.replace("{" + key + "}", str(value))
        return text

    # ─────────────────── Condition evaluation ───────────────────

    def _resolve_save_target(self, target: str, game_state: Optional[Any] = None):
        """Resolve the player object a ``save_throw`` condition targets.

        ``"self"`` (or empty) → the active player; anything else is matched
        against ``game_state.players`` by exact or case-insensitive name.
        Returns ``None`` when no player can be resolved (condition fails).
        """
        if not target or target == "self":
            if game_state is not None:
                return getattr(game_state, "player", None)
            return None
        players = getattr(game_state, "players", None) or {}
        player = players.get(target)
        if player is None:
            needle = str(target).lower()
            player = next(
                (p for name, p in players.items() if str(name).lower() == needle),
                None,
            )
        return player

    def _resolve_condition_player(self, target: str, game_state: Optional[Any] = None):
        """Resolve the player a ``has_tag``/``has_trait`` condition checks.

        Same semantics as ``_resolve_save_target``: ``"self"``/empty → active
        player (falling back to ``game_state.active_player``), otherwise a
        named player from ``game_state.players``.
        """
        player = self._resolve_save_target(target, game_state)
        if player is not None:
            return player
        players = getattr(game_state, "players", None) or {}
        active = getattr(game_state, "active_player", None)
        if active:
            return players.get(active)
        return None

    @staticmethod
    def _compare(value, threshold, operator: str) -> bool:
        """Compare *value* against *threshold* with an operator string.

        Operators: ``lt``, ``le``, ``eq``, ``ge``, ``gt`` (aliases ``<``,
        ``<=``, ``==``, ``>=``, ``>``). Defaults to ``eq``.
        """
        try:
            return {
                "lt": value < threshold, "<": value < threshold,
                "le": value <= threshold, "<=": value <= threshold,
                "eq": value == threshold, "==": value == threshold, "=": value == threshold,
                "ge": value >= threshold, ">=": value >= threshold,
                "gt": value > threshold, ">": value > threshold,
            }[operator]
        except (KeyError, TypeError):
            return False

    def _area_node(self, game_state: Optional[Any] = None, item_node: Optional[Node] = None):
        """Resolve the area node for the current game state."""
        if game_state is None:
            return None
        area_id = None
        if hasattr(game_state, '_get_current_area_id'):
            try:
                area_id = game_state._get_current_area_id()
            except Exception:
                area_id = None
        if not area_id and hasattr(game_state, 'get_current_area_id'):
            try:
                area_id = game_state.get_current_area_id()
            except Exception:
                area_id = None
        if not area_id and item_node is not None:
            area_id = self._get_current_area_id(item_node, game_state)
        if not area_id:
            return None
        return self.graph.get_node(area_id)

    def _evaluate_trigger_condition(
        self,
        condition: dict,
        item_node: Optional[Node] = None,
        game_state: Optional[Any] = None,
    ) -> bool:
        """Evaluate a single trigger condition.

        Returns ``True`` if *condition* is empty/met, ``False`` otherwise.
        Unknown condition types return ``False`` (fail-safe).

        *game_state* must provide (when needed by the condition type):

        * ``game_state.active_player``
        * ``game_state._player_node_id(player_name)``
        * ``game_state._get_current_area_id()``
        * ``game_state.graph`` (accessible as ``self.graph``)
        """
        if not condition:
            return True
        condition_type = condition.get("type", "")
        condition_value = condition.get("value", "")

        if condition_type == "uses_reached":
            try:
                target_uses = int(condition_value)
                current_uses = (
                    int(item_node.properties.get("uses", -1))
                    if item_node
                    else -1
                )
                return current_uses <= target_uses
            except (ValueError, TypeError):
                return False

        elif condition_type == "uses_above":
            try:
                target_uses = int(condition_value)
                current_uses = (
                    int(item_node.properties.get("uses", -1))
                    if item_node
                    else -1
                )
                return current_uses > target_uses
            except (ValueError, TypeError):
                return False

        elif condition_type == "has_item":
            if not condition_value:
                return False
            if game_state is None:
                return False
            player_id = game_state._player_node_id(game_state.active_player)
            inventory_edges = self.graph.get_edges_for_target(
                player_id, EDGE_CARRYING
            )
            needle = str(condition_value).lower()
            return any(
                (node := self.graph.get_node(edge.source))
                and node.type == "item"
                and (needle in node.name.lower() or needle in node.id.lower())
                for edge in inventory_edges
            )

        elif condition_type == "has_items":
            items = condition.get("value", [])
            if not isinstance(items, list) or not items:
                return False
            if game_state is None:
                return False
            player_id = game_state._player_node_id(game_state.active_player)
            inventory_edges = self.graph.get_edges_for_target(
                player_id, EDGE_CARRYING
            )
            for item_name in items:
                needle = str(item_name).lower()
                found = any(
                    (node := self.graph.get_node(edge.source))
                    and node.type == "item"
                    and (
                        needle in node.name.lower()
                        or needle in node.id.lower()
                    )
                    for edge in inventory_edges
                )
                if not found:
                    return False
            return True

        elif condition_type == "state_equals":
            target_name = condition.get("target", "")
            if target_name:
                needle = str(target_name).lower()
                target_node = None
                for node_id, node in self.graph.nodes.items():
                    if needle in node.name.lower() or needle in node_id.lower():
                        target_node = node
                        break
                if target_node:
                    expected_state = str(condition.get("value", ""))
                    return (
                        target_node.properties.get("current_state", "")
                        == expected_state
                    )
                return False
            if "=" in condition_value:
                parts = condition_value.split("=", 1)
                node_id = parts[0].strip()
                expected_state = parts[1].strip()
                target_node = self.graph.get_node(node_id) if node_id else None
                if target_node:
                    return (
                        target_node.properties.get("current_state", "")
                        == expected_state
                    )
                return False
            if item_node:
                return (
                    item_node.properties.get("current_state", "")
                    == condition_value
                )
            return False

        elif condition_type == "random_chance":
            try:
                return random.random() < float(condition_value) / 100.0
            except (ValueError, TypeError):
                return False

        elif condition_type == "skill_check":
            skill = condition.get("skill", "Athletics")
            dc = int(condition.get("dc", 10))
            success, total, msg = self.skills.skill_check(skill, dc)
            self._last_skill_check_msg = msg
            return success

        elif condition_type == "save_throw":
            # Unified save condition (task-159): the target rolls a stat or
            # skill vs DC. Success means they avoided/resisted the danger, so
            # the condition passes and the trigger's effects fire (pair with a
            # damage effect's `save` param for halved damage instead).
            check = condition.get("stat") or condition.get("skill") or "DEX"
            dc = int(condition.get("dc", 12))
            player = self._resolve_save_target(condition.get("target", "self"), game_state)
            if player is None:
                return False
            success, total, msg = self.skills.saving_throw(player, check, dc)
            self._last_save_msg = msg
            return success

        elif condition_type == "temperature_below":
            try:
                threshold = int(condition_value)
                if game_state is None:
                    return False
                area_node = self._area_node(game_state, item_node)
                if area_node:
                    current = int(
                        area_node.properties.get("environment", {}).get(
                            "temperature", 21
                        )
                    )
                    return current < threshold
            except (ValueError, TypeError):
                pass
            return False

        elif condition_type == "temperature_above":
            try:
                threshold = int(condition_value)
                if game_state is None:
                    return False
                area_node = self._area_node(game_state, item_node)
                if area_node:
                    current = int(
                        area_node.properties.get("environment", {}).get(
                            "temperature", 21
                        )
                    )
                    return current > threshold
            except (ValueError, TypeError):
                pass
            return False

        elif condition_type == "area_temp":
            # Combined temperature condition with a comparator:
            # {"value": 20, "operator": "lt"|"le"|"eq"|"ge"|"gt"}
            try:
                threshold = float(condition_value)
                operator = condition.get("operator", "lt")
                area_node = self._area_node(game_state, item_node)
                if not area_node:
                    return False
                current = int(
                    area_node.properties.get("environment", {}).get(
                        "temperature", 21
                    )
                )
                return self._compare(current, threshold, operator)
            except (ValueError, TypeError):
                return False

        elif condition_type == "vital":
            # Combined vital condition:
            # {"stat": "HP", "value": 50, "operator": "lt"|"le"|"eq"|"ge"|"gt", "target": "self"|name}
            try:
                stat = condition.get("stat", "HP")
                threshold = float(condition_value)
                operator = condition.get("operator", "lt")
                player = self._resolve_condition_player(condition.get("target", "self"), game_state)
                if not player:
                    return False
                current = player.vitals.get(stat)
                if current is None:
                    return False
                return self._compare(current, threshold, operator)
            except (ValueError, TypeError):
                return False

        elif condition_type == "vital_above":
            try:
                stat = condition.get("stat", "HP")
                threshold = float(condition_value)
                player = self._resolve_condition_player(condition.get("target", "self"), game_state)
                if not player:
                    return False
                current = player.vitals.get(stat)
                if current is None:
                    return False
                return self._compare(current, threshold, "gt")
            except (ValueError, TypeError):
                return False

        elif condition_type == "vital_below":
            try:
                stat = condition.get("stat", "HP")
                threshold = float(condition_value)
                player = self._resolve_condition_player(condition.get("target", "self"), game_state)
                if not player:
                    return False
                current = player.vitals.get(stat)
                if current is None:
                    return False
                return self._compare(current, threshold, "lt")
            except (ValueError, TypeError):
                return False

        elif condition_type == "is_equipped":
            # {"item": "torch", "target": "self"|name}
            if game_state is None:
                return False
            player = self._resolve_condition_player(condition.get("target", "self"), game_state)
            if not player:
                return False
            player_id = getattr(game_state, "_player_node_id", lambda n: f"player_{n}")(player.name)
            needle = str(condition.get("item", "")).lower()
            if not needle:
                return False
            equipped_edges = self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED)
            return any(
                (node := self.graph.get_node(edge.source))
                and node.type == "item"
                and (needle in node.name.lower() or needle in node.id.lower())
                for edge in equipped_edges
            )

        elif condition_type == "time_of_day":
            # {"value": "14:00"} — compare the current game clock (HH:MM).
            target = str(condition_value).strip()
            if not target:
                return False
            current = None
            if game_state is not None and hasattr(game_state, "get_current_time"):
                try:
                    current = str(game_state.get_current_time())
                except Exception:
                    current = None
            if not current:
                return False
            target_hm = target[:5]
            return current[:5] == target_hm

        elif condition_type == "weather":
            # {"value": "rain"} — area environment's `weather` key (optional).
            if game_state is None:
                return False
            area_node = self._area_node(game_state, item_node)
            if not area_node:
                return False
            current = area_node.properties.get("environment", {}).get("weather", "")
            return str(current).lower() == str(condition_value).lower()

        elif condition_type == "has_trait":
            from engine.traits import TraitSystem
            if game_state is None:
                return False
            player = self._resolve_condition_player(condition.get("target", "self"), game_state)
            if not player:
                return False
            return TraitSystem.has_trait(player, condition_value)

        elif condition_type == "has_tag":
            if game_state is None:
                return False
            player = self._resolve_condition_player(condition.get("target", "self"), game_state)
            if not player:
                return False
            needle_values = condition_value if isinstance(condition_value, list) else [condition_value]
            needle_values = [str(v).strip().lower() for v in needle_values if str(v).strip()]
            tags = player.tags or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            return any(str(t).lower() in needle_values for t in tags)

        return False

    def _evaluate_conditions(
        self,
        conditions: Any,
        context: dict,
        game_state: Optional[Any] = None,
    ) -> bool:
        """Evaluate a condition tree against the given *context* dict.

        Accepts both tree format (dict with ``operator``/``conditions``)
        and flat list format (treated as AND group). Supports all
        condition types from NPC behavior AND item trigger systems.

        Returns ``True`` if conditions are met (or *conditions* is
        empty/``None``).  Unknown condition types return ``False``
        (fail-safe).
        """
        if not conditions:
            return True

        # Normalise list → AND tree
        if isinstance(conditions, list):
            conditions = {"operator": "and", "conditions": conditions}

        operator = conditions.get("operator")
        if operator:
            sub_conditions = conditions.get("conditions", [])
            if operator == "and":
                return all(
                    self._evaluate_conditions(c, context, game_state=game_state)
                    for c in sub_conditions
                )
            elif operator == "or":
                return any(
                    self._evaluate_conditions(c, context, game_state=game_state)
                    for c in sub_conditions
                )
            elif operator == "not":
                return (
                    not self._evaluate_conditions(
                        sub_conditions[0], context, game_state=game_state
                    )
                    if sub_conditions
                    else True
                )
            return False

        # ── Leaf conditions ──────────────────────────────────
        condition_type = conditions.get("type")
        item_node = context.get("item_node")
        gs = game_state or context.get("game_state")

        # --- NPC behaviour leaf types ---
        if condition_type == "eq":
            target_key = conditions.get("target")
            expected = conditions.get("value")
            actual = context.get(target_key)
            return actual == expected

        elif condition_type == "in_area":
            area_name = conditions.get("area")
            target = conditions.get("target", "npc")
            area_key = f"{target}_area"
            return context.get(area_key) == area_name

        elif condition_type == "tick_since_state":
            min_ticks = int(conditions.get("min_ticks", 0))
            enter_tick = context.get("state_enter_tick", 0)
            current_tick = context.get("current_tick", 0)
            return (current_tick - enter_tick) >= min_ticks

        elif condition_type == "proximity":
            max_areas = int(conditions.get("max_areas", 0))
            npc_area = context.get("npc_area")
            player_area = context.get("player_area")
            if max_areas == 0:
                return npc_area == player_area
            if npc_area == player_area:
                return True
            if max_areas >= 1 and npc_area:
                npc_exits = (
                    gs._build_exits_for_area(npc_area)
                    if gs
                    else {}
                )
                for exit_data in npc_exits.values():
                    if exit_data.get("target") == player_area:
                        return True
            return False

        # --- Shared leaf types (NPC + item triggers) ---
        elif condition_type in ("has_item", "random_chance"):
            if condition_type == "random_chance":
                chance_val = conditions.get("chance")
                if chance_val is None:
                    chance_val = conditions.get("value", 0)
                try:
                    threshold = float(chance_val)
                    # `chance` uses 0.0–1.0 (NPC behaviors); `value` uses 0–100 (item triggers).
                    if chance_val is conditions.get("value"):
                        threshold /= 100.0
                    elif threshold > 1.0:
                        threshold /= 100.0
                    return random.random() < threshold
                except (ValueError, TypeError):
                    return False

            # has_item — check player inventory via graph
            item_name = (
                conditions.get("item")
                or conditions.get("value")
                or ""
            )
            if not item_name:
                return False
            # Try NPC-style context inventory first
            target = conditions.get("target", "player")
            inv_key = f"{target}_inventory"
            inventory = context.get(inv_key, [])
            if inventory:
                return any(
                    item_name in i.get("name", "")
                    or item_name in i.get("id", "")
                    for i in inventory
                )
            # Fallback to graph-based inventory lookup (item trigger style)
            if gs is None or not hasattr(gs, '_player_node_id'):
                return False
            player_id = gs._player_node_id(gs.active_player)
            inv_edges = self.graph.get_edges_for_target(
                player_id, EDGE_CARRYING
            )
            needle = str(item_name).lower()
            return any(
                (node := self.graph.get_node(edge.source))
                and node.type == "item"
                and (needle in node.name.lower() or needle in node.id.lower())
                for edge in inv_edges
            )

        # --- Item trigger leaf types ---
        elif condition_type == "uses_reached":
            try:
                target_uses = int(conditions.get("value", 0))
                current_uses = (
                    int(item_node.properties.get("uses", -1))
                    if item_node
                    else -1
                )
                return current_uses <= target_uses
            except (ValueError, TypeError):
                return False

        elif condition_type == "uses_above":
            try:
                target_uses = int(conditions.get("value", 0))
                current_uses = (
                    int(item_node.properties.get("uses", -1))
                    if item_node
                    else -1
                )
                return current_uses > target_uses
            except (ValueError, TypeError):
                return False

        elif condition_type == "sound_heard":
            # Check if character has heard a specific sound pattern recently
            sound_pattern = conditions.get("pattern", "").lower()
            if gs is None or not hasattr(gs, 'players'):
                return False
            player = gs.players.get(gs.active_player) if gs.active_player else None
            if not player:
                return False
            
            # Check recent_hearing for matching sound
            recent_hearing = getattr(player, "recent_hearing", [])
            for entry in recent_hearing:
                if entry.get("type") == "sound_source":
                    heard_pattern = entry.get("sound_pattern", "").lower()
                    if sound_pattern in heard_pattern or heard_pattern in sound_pattern:
                        return True
                elif entry.get("type") == "speech":
                    # Also check for speech if pattern matches
                    heard_text = entry.get("text", "").lower()
                    if sound_pattern and sound_pattern in heard_text:
                        return True
            return False

        elif condition_type == "speech_matches":
            # Match the spoken text of an on_speech trigger against a phrase.
            # Reads `speech` from the trigger context (set by broadcast_speech).
            spoken = str(context.get("speech", "")).lower()
            phrase = str(conditions.get("phrase", "") or conditions.get("value", "")).lower()
            mode = str(conditions.get("mode", "contains")).lower()
            if not phrase or not spoken:
                return False
            if mode == "exact":
                return spoken.strip() == phrase.strip()
            if mode == "contains":
                return phrase in spoken
            if mode == "startswith":
                return spoken.strip().startswith(phrase.strip())
            if mode == "endswith":
                return spoken.strip().endswith(phrase.strip())
            # word-boundary aware substring ("fuzzy")
            return re.search(rf"\b{re.escape(phrase)}\b", spoken) is not None

        elif condition_type == "has_items":
            items = conditions.get("value", [])
            if not isinstance(items, list) or not items:
                return False
            if gs is None or not hasattr(gs, '_player_node_id'):
                return False
            player_id = gs._player_node_id(gs.active_player)
            inv_edges = self.graph.get_edges_for_target(
                player_id, EDGE_CARRYING
            )
            for item_name in items:
                needle = str(item_name).lower()
                found = any(
                    (node := self.graph.get_node(edge.source))
                    and node.type == "item"
                    and (needle in node.name.lower() or needle in node.id.lower())
                    for edge in inv_edges
                )
                if not found:
                    return False
            return True

        elif condition_type == "state_equals":
            condition_value = conditions.get("value", "")
            target_name = conditions.get("target", "")
            if target_name:
                needle = str(target_name).lower()
                target_node = None
                for node_id, node in self.graph.nodes.items():
                    if needle in node.name.lower() or needle in node_id.lower():
                        target_node = node
                        break
                if target_node:
                    expected_state = str(condition_value)
                    return (
                        target_node.properties.get("current_state", "")
                        == expected_state
                    )
                return False
            if "=" in condition_value:
                parts = condition_value.split("=", 1)
                node_id = parts[0].strip()
                expected_state = parts[1].strip()
                target_node = self.graph.get_node(node_id) if node_id else None
                if target_node:
                    return (
                        target_node.properties.get("current_state", "")
                        == expected_state
                    )
                return False
            if item_node:
                return (
                    item_node.properties.get("current_state", "")
                    == condition_value
                )
            return False

        elif condition_type == "skill_check":
            skill = conditions.get("skill", "Athletics")
            dc = int(conditions.get("dc", 10))
            success, total, msg = self.skills.skill_check(skill, dc)
            self._last_skill_check_msg = msg
            return success

        elif condition_type == "save_throw":
            # Unified save condition (task-159) — see the flat-condition
            # branch above for semantics.
            check = conditions.get("stat") or conditions.get("skill") or "DEX"
            dc = int(conditions.get("dc", 12))
            player = self._resolve_save_target(conditions.get("target", "self"), gs)
            if player is None:
                return False
            success, total, msg = self.skills.saving_throw(player, check, dc)
            self._last_save_msg = msg
            return success

        elif condition_type == "temperature_below":
            try:
                threshold = int(conditions.get("value", 0))
                area_id = (
                    gs._get_current_area_id()
                    if gs and hasattr(gs, '_get_current_area_id')
                    else None
                )
                if area_id:
                    area_node = self.graph.get_node(area_id)
                    if area_node:
                        current = int(
                            area_node.properties.get("environment", {}).get(
                                "temperature", 21
                            )
                        )
                        return current < threshold
            except (ValueError, TypeError):
                pass
            return False

        elif condition_type == "temperature_above":
            try:
                threshold = int(conditions.get("value", 0))
                area_id = (
                    gs._get_current_area_id()
                    if gs and hasattr(gs, '_get_current_area_id')
                    else None
                )
                if area_id:
                    area_node = self.graph.get_node(area_id)
                    if area_node:
                        current = int(
                            area_node.properties.get("environment", {}).get(
                                "temperature", 21
                            )
                        )
                        return current > threshold
            except (ValueError, TypeError):
                pass
            return False

        elif condition_type == "area_temp":
            try:
                threshold = float(conditions.get("value", 0))
                operator = conditions.get("operator", "lt")
                area_id = (
                    gs._get_current_area_id()
                    if gs and hasattr(gs, '_get_current_area_id')
                    else None
                )
                if area_id:
                    area_node = self.graph.get_node(area_id)
                    if area_node:
                        current = int(
                            area_node.properties.get("environment", {}).get(
                                "temperature", 21
                            )
                        )
                        return self._compare(current, threshold, operator)
            except (ValueError, TypeError):
                pass
            return False

        elif condition_type == "vital":
            try:
                stat = conditions.get("stat", "HP")
                threshold = float(conditions.get("value", 0))
                operator = conditions.get("operator", "lt")
                player = self._resolve_condition_player(conditions.get("target", "self"), gs)
                if not player:
                    return False
                current = player.vitals.get(stat)
                if current is None:
                    return False
                return self._compare(current, threshold, operator)
            except (ValueError, TypeError):
                return False

        elif condition_type == "vital_above":
            try:
                stat = conditions.get("stat", "HP")
                threshold = float(conditions.get("value", 0))
                player = self._resolve_condition_player(conditions.get("target", "self"), gs)
                if not player:
                    return False
                current = player.vitals.get(stat)
                if current is None:
                    return False
                return self._compare(current, threshold, "gt")
            except (ValueError, TypeError):
                return False

        elif condition_type == "vital_below":
            try:
                stat = conditions.get("stat", "HP")
                threshold = float(conditions.get("value", 0))
                player = self._resolve_condition_player(conditions.get("target", "self"), gs)
                if not player:
                    return False
                current = player.vitals.get(stat)
                if current is None:
                    return False
                return self._compare(current, threshold, "lt")
            except (ValueError, TypeError):
                return False

        elif condition_type == "is_equipped":
            if gs is None:
                return False
            player = self._resolve_condition_player(conditions.get("target", "self"), gs)
            if not player:
                return False
            player_id = getattr(gs, "_player_node_id", lambda n: f"player_{n}")(player.name)
            needle = str(conditions.get("item", "")).lower()
            if not needle:
                return False
            equipped_edges = self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED)
            return any(
                (node := self.graph.get_node(edge.source))
                and node.type == "item"
                and (needle in node.name.lower() or needle in node.id.lower())
                for edge in equipped_edges
            )

        elif condition_type == "time_of_day":
            target = str(conditions.get("value", "")).strip()
            if not target:
                return False
            current = None
            if gs is not None and hasattr(gs, "get_current_time"):
                try:
                    current = str(gs.get_current_time())
                except Exception:
                    current = None
            if not current:
                return False
            target_hm = target[:5]
            return current[:5] == target_hm

        elif condition_type == "weather":
            if gs is None:
                return False
            area_id = (
                gs._get_current_area_id()
                if hasattr(gs, '_get_current_area_id')
                else None
            )
            if not area_id:
                return False
            area_node = self.graph.get_node(area_id)
            if not area_node:
                return False
            current = area_node.properties.get("environment", {}).get("weather", "")
            return str(current).lower() == str(conditions.get("value", "")).lower()

        elif condition_type == "sound_heard":
            # Check if character has heard a specific sound pattern recently
            sound_pattern = conditions.get("pattern", "").lower()
            if gs is None or not hasattr(gs, 'players'):
                return False
            player = gs.players.get(gs.active_player) if gs.active_player else None
            if not player:
                return False
            
            # Check recent_hearing for matching sound
            recent_hearing = getattr(player, "recent_hearing", [])
            for entry in recent_hearing:
                if entry.get("type") == "sound_source":
                    heard_pattern = entry.get("sound_pattern", "").lower()
                    if sound_pattern in heard_pattern or heard_pattern in sound_pattern:
                        return True
                elif entry.get("type") == "speech":
                    # Also check for speech if pattern matches
                    heard_text = entry.get("text", "").lower()
                    if sound_pattern and sound_pattern in heard_text:
                        return True
            return False

        elif condition_type == "speech_matches":
            # Match the spoken text of an on_speech trigger against a phrase.
            # Reads `speech` from the trigger context (set by broadcast_speech).
            spoken = str(context.get("speech", "")).lower()
            phrase = str(conditions.get("phrase", "") or conditions.get("value", "")).lower()
            mode = str(conditions.get("mode", "contains")).lower()
            if not phrase or not spoken:
                return False
            if mode == "exact":
                return spoken.strip() == phrase.strip()
            if mode == "contains":
                return phrase in spoken
            if mode == "startswith":
                return spoken.strip().startswith(phrase.strip())
            if mode == "endswith":
                return spoken.strip().endswith(phrase.strip())
            # word-boundary aware substring ("fuzzy")
            return re.search(rf"\b{re.escape(phrase)}\b", spoken) is not None

        elif condition_type == "has_trait":
            from engine.traits import TraitSystem
            if gs is None:
                return False
            player = self._resolve_condition_player(conditions.get("target", "self"), gs)
            if not player:
                return False
            return TraitSystem.has_trait(player, conditions.get("value", ""))

        elif condition_type == "has_tag":
            needle_values = conditions.get("value") or []
            if isinstance(needle_values, str):
                needle_values = [needle_values]
            needle_values = [str(v).strip().lower() for v in needle_values if str(v).strip()]
            if not needle_values:
                return False
            target = conditions.get("target", "self")
            if target == "target":
                # The used-on node of an on_use_on trigger (way/item/area/character)
                node = context.get("target_node")
                if node is None:
                    return False
                tags = node.properties.get("tags", []) if node.properties else []
            else:
                if gs is None:
                    return False
                player = self._resolve_condition_player(target, gs)
                if not player:
                    return False
                tags = player.tags or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            return any(str(t).lower() in needle_values for t in tags)

        elif condition_type == "target_has_tag":
            # Backward-compat alias for the unified has_tag (target = used-on node).
            target_node = context.get("target_node")
            if target_node is None:
                return False
            needle_values = conditions.get("value") or []
            if isinstance(needle_values, str):
                needle_values = [needle_values]
            needle_values = [str(v).strip().lower() for v in needle_values if str(v).strip()]
            tags = target_node.properties.get("tags", []) if target_node.properties else []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            return any(str(t).lower() in needle_values for t in tags)

        return False

    # ─────────────────── NPC behavior actions ───────────────────

    def _execute_behavior_actions(
        self,
        char_name: str,
        actions: List[dict],
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Execute a list of action dicts for an NPC behaviour.

        Returns a list of output strings describing what happened.

        *game_state* must provide:

        * ``game_state.players`` — dict of all Player objects
        * ``game_state.active_player`` — current active player name (rw)
        * ``game_state.graph`` — the WorldGraph
        * ``game_state.broadcast_speech(speaker, text)``
        * ``game_state.time_ticks`` — current tick count
        * ``game_state._get_current_area_id()``
        * ``game_state.player`` — active Player object
        * ``game_state.current_area`` — Area object for current area
        """
        outputs = []
        if game_state is None:
            return outputs
        player = game_state.players.get(char_name)
        if player is None:
            return outputs
        old_active = game_state.active_player
        game_state.active_player = char_name
        try:
            for action in actions:
                action_type = action.get("type", "message")

                if action_type == "message":
                    text = action.get("text", "")
                    if not text.strip():
                        continue
                    outputs.append(f"[{char_name}] {text}")

                elif action_type == "speak":
                    text = action.get("text", "...")
                    game_state.broadcast_speech(char_name, text)
                    outputs.append(f'{char_name} says: "{text}"')

                elif action_type == "set_npc_state":
                    new_state = action.get("state", "idle")
                    if new_state != player.npc_state:
                        old_state = player.npc_state
                        player.npc_state = new_state
                        player.state_enter_tick = game_state.time_ticks
                        outputs.append(
                            f"[{char_name}] state: {old_state} -> {new_state}"
                        )

                elif action_type == "damage":
                    amount = int(action.get("amount", 5))
                    target = action.get("target", "player")
                    if target == "player":
                        target_player = (
                            game_state.players.get(game_state.active_player)
                            if game_state.active_player
                            else None
                        )
                        if target_player:
                            target_player.vitals["HP"] = max(
                                0,
                                target_player.vitals.get("HP", 100) - amount,
                            )
                            outputs.append(
                                f"{game_state.active_player} takes {amount} damage!"
                            )
                    elif target == "self" and player:
                        player.vitals["HP"] = max(
                            0, player.vitals.get("HP", 100) - amount
                        )
                        outputs.append(f"{char_name} takes {amount} damage!")

                elif action_type == "heal":
                    amount = int(action.get("amount", 10))
                    stat = action.get("stat", "HP")
                    target_name = action.get("target", "self")
                    target_player = (
                        game_state.players.get(target_name)
                        if target_name in game_state.players
                        else player
                    )
                    if target_player and stat in target_player.vitals:
                        target_player.vitals[stat] = min(
                            100,
                            target_player.vitals.get(stat, 100) + amount,
                        )

                elif action_type == "set_environment":
                    stat = action.get("stat", "temperature")
                    amount = int(action.get("amount", 0))
                    target_area_name = action.get("area", player.current_area)
                    target_area_node = None
                    for node in game_state.graph.nodes.values():
                        if node.type == "area" and node.name == target_area_name:
                            target_area_node = node
                            break
                    if target_area_node:
                        env = target_area_node.properties.setdefault(
                            "environment", {}
                        )
                        env[stat] = env.get(stat, 20) + amount
                        outputs.append(
                            f"The {stat} in {target_area_name} changes by {amount}."
                        )

                elif action_type == "spawn_item":
                    item_id = action.get("item_id", "")
                    if item_id and player.current_area:
                        area_id = game_state._get_current_area_id()
                        if area_id:
                            spawn_node = game_state.graph.get_node(item_id)
                            if spawn_node is None:
                                try:
                                    import os, json
                                    lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'library', 'items')
                                    lib_path = os.path.join(lib_dir, f"{item_id}.json")
                                    if os.path.exists(lib_path):
                                        with open(lib_path, 'r', encoding='utf-8') as f:
                                            lib_data = json.load(f)
                                except Exception:
                                    lib_data = {}

                                display_name = action.get("display_name") or action.get("name") or lib_data.get("name", item_id)
                                desc = action.get("description") or lib_data.get("description", "")
                                tags = lib_data.get("tags", [])
                                uses = lib_data.get("uses", -1)
                                weight = lib_data.get("weight", 0.1)

                                spawn_node = Node(
                                    id=item_id,
                                    type="item",
                                    name=display_name,
                                    properties={
                                        "description": desc,
                                        "tags": tags,
                                        "uses": uses,
                                        "weight": weight,
                                    },
                                )
                                game_state.graph.add_node(spawn_node)
                            for edge in game_state.graph.edges[:]:
                                if (
                                    edge.source == item_id
                                    and edge.type == EDGE_IN
                                ):
                                    game_state.graph.edges.remove(edge)
                            game_state.graph.add_edge(
                                Edge(
                                    source=item_id,
                                    target=area_id,
                                    type=EDGE_IN,
                                )
                            )

                elif action_type == "teleport":
                    target_area = action.get("area", "")
                    target_char = action.get("target", "player")
                    target_name = (
                        game_state.active_player
                        if target_char == "player"
                        else action.get("character_name", char_name)
                    )
                    target_player = game_state.players.get(target_name)
                    if target_player and target_area:
                        for node in game_state.graph.nodes.values():
                            if (
                                node.type == "area"
                                and node.name == target_area
                            ):
                                target_player.current_area = target_area
                                outputs.append(
                                    f"{target_name} vanishes and reappears elsewhere!"
                                )
                                break

                elif action_type == "go":
                    if hasattr(game_state, "npc_behaviors"):
                        msg = game_state.npc_behaviors.execute_go_action(
                            char_name, action
                        )
                        if msg:
                            outputs.append(msg)
                    else:
                        target_area = action.get("area") or action.get("room", "")
                        if target_area and player.current_area:
                            area_exists = any(
                                node.type == "area" and node.name == target_area
                                for node in game_state.graph.nodes.values()
                            )
                            if area_exists:
                                player.current_area = target_area
                                outputs.append(
                                    f"[{char_name}] moves to {target_area}."
                                )
                            else:
                                outputs.append(
                                    f"[{char_name}] cannot find area '{target_area}'."
                                )
        finally:
            game_state.active_player = old_active
        return outputs

    # ─────────────────── Available actions ───────────────────

    def _get_available_actions(self, item_node: Node) -> List[dict]:
        """Return a list of action descriptors for an item given the current context.

        The returned list is used by the UI to render available
        interaction buttons.

        *game_state* is not required here (graph info is accessed via
        ``self.graph`` and *item_node*).
        """
        actions = item_node.properties.get("actions", [])
        if isinstance(actions, str):
            actions = [a.strip() for a in actions.split(",")]
        actions = normalize_item_actions(actions)

        trigger_edges = self.graph.get_edges_for_source(
            item_node.id, EDGE_TRIGGERS
        )
        trigger_types = set()
        for trigger_edge in trigger_edges:
            trigger_node = self.graph.get_node(trigger_edge.target)
            if trigger_node:
                tt = trigger_node.properties.get("trigger_type", "")
                # trigger_type may be a single string or a list (multi-select editor)
                if isinstance(tt, list):
                    trigger_types.update(str(x) for x in tt)
                elif tt:
                    trigger_types.add(tt)

        tags = [t.lower() for t in item_node.properties.get("tags", [])]
        state = item_node.properties.get("current_state", "")
        result = []

        result.append(
            {
                "action": "examine",
                "label": "Examine the object",
                "enabled": True,
            }
        )

        if "take" in actions:
            result.append({"action": "take", "label": "Pick up", "enabled": True})

        if "drop" in actions:
            result.append(
                {
                    "action": "drop",
                    "label": "Drop from inventory",
                    "enabled": True,
                }
            )

        if "open" in actions or "openable" in tags:
            if state in ("closed", "normal", ""):
                result.append({"action": "open", "label": "Open", "enabled": True})
            else:
                result.append(
                    {
                        "action": "open",
                        "label": "Open",
                        "enabled": False,
                        "reason": "Already open",
                    }
                )

        if "close" in actions or (state == "open"):
            if state == "open":
                result.append(
                    {"action": "close", "label": "Close", "enabled": True}
                )
            else:
                result.append(
                    {
                        "action": "close",
                        "label": "Close",
                        "enabled": False,
                        "reason": "Already closed",
                    }
                )

        if "use" in actions or "on_use" in trigger_types or "on_use_on" in trigger_types:
            label = "Use"
            if "on_use_on" in trigger_types:
                for trigger_edge in trigger_edges:
                    trigger_node = self.graph.get_node(trigger_edge.target)
                    if not trigger_node:
                        continue
                    tt = trigger_node.properties.get("trigger_type", "")
                    tt_list = tt if isinstance(tt, list) else ([tt] if tt else [])
                    if "on_use_on" in tt_list:
                        target_name = trigger_node.properties.get(
                            "target_name", ""
                        )
                        if target_name:
                            label = f"Use on {target_name}"
                            break
            result.append({"action": "use", "label": label, "enabled": True})

        if "eat" in actions or "food" in tags:
            result.append({"action": "eat", "label": "Eat", "enabled": True})

        if "drink" in actions or "drink" in tags:
            result.append({"action": "drink", "label": "Drink", "enabled": True})

        if "on_toggle_on" in trigger_types or "on_toggle_off" in trigger_types:
            toggle_state = "on" if state == "off" else "off"
            result.append(
                {
                    "action": "toggle",
                    "label": f"Toggle {toggle_state}",
                    "enabled": True,
                }
            )

        return result

    # ─────────────────── Contextual failure messages ───────────────────

    def _contextual_failure(
        self, verb: str, target_name: str, available_actions: List[dict]
    ) -> str:
        """Generate a first-person contextual failure reason.

        Explains why *verb* can't be performed on *target_name*, and
        suggests available alternatives from the *available_actions* list.
        """
        reasons = {
            "take": "I reach for the {item} but stop — I have no need for it.",
            "use": "I examine the {item} but can't figure out what to do with it.",
            "eat": "I pause — that's not food.",
            "drink": "That's not something you drink.",
            "open": "The {item} doesn't open.",
            "close": "The {item} isn't something you can close.",
            "break": "I don't think breaking the {item} would accomplish anything.",
        }
        msg = reasons.get(verb, "I try, but nothing useful happens.")
        msg = msg.format(item=target_name)

        valid = [a["label"] for a in available_actions if a["enabled"]]
        if valid:
            msg += (
                f" I could {valid[0].lower()}"
                + (
                    f" or {', '.join(v.lower() for v in valid[1:])}."
                    if len(valid) > 1
                    else "."
                )
            )
        return msg

    # ─────────────────── Main trigger execution ───────────────────

    def _get_current_area_id(self, item_node: Node, game_state: Any) -> Optional[str]:
        """Find the area ID for a given item node or game state."""
        if game_state and hasattr(game_state, 'get_current_area_id'):
            area_id = game_state.get_current_area_id()
            if area_id:
                return area_id
        # Fallback: search edges for this item's location
        for edge in self.graph.edges:
            if edge.source == item_node.id and edge.type == EDGE_IN:
                return edge.target
        return None

    def _get_items_by_tag_in_area(self, tag: str, status: Optional[str], area_id: str) -> List[Node]:
        """Get all item nodes in a area matching a tag (and optionally a status)."""
        if status:
            return self.graph.get_items_by_tag_and_status(tag, status, area_id)
        return self.graph.get_items_by_tag(tag, area_id)

    # ── Unified effect target resolution ───────────────────────────────

    def _player_node_for_name(self, name: str) -> Optional[Node]:
        """Find a character node for a player display name (id may use a
        different separator/case than player_<name>)."""
        candidates = [
            f"player_{name}".replace(" ", "_"),
            f"player_{name}",
        ]
        for cid in candidates:
            node = self.graph.get_node(cid)
            if node:
                return node
        return next((n for n in self.graph.nodes.values()
                     if n.type in ("player", "character") and n.name == name), None)

    def _resolve_effect_targets(self, effect_params: dict, item_node: Node, game_state: Any = None) -> List[Node]:
        """Resolve the set of target nodes for an effect.

        Target spec (all optional, first matching wins):
          target_by: "name" | "tag" | "trait" | "type" | "all_in_area"
          target_value: the name / tag / trait / node type to match
          target_scope: "area" (default) | "world"
          target_tag: legacy tag fan-out (items in area)
          target_name: named target (character / node)

        Returns an empty list when there is no fan-out — the caller then runs
        the effect once against the default target (self / on_use_on target).
        """
        by = effect_params.get("target_by")
        value = effect_params.get("target_value")
        scope = effect_params.get("target_scope", "area")
        area_id = effect_params.get("area_id") or self._get_current_area_id(item_node, game_state)

        # Legacy tag fan-out (items in the area) — keep working.
        if not by:
            tag = effect_params.get("target_tag")
            if tag and area_id:
                require_status = effect_params.get("require_status")
                return self._get_items_by_tag_in_area(tag, require_status, area_id)
            if tag:
                return [n for n in self.graph.nodes.values() if tag in (n.properties.get("tags", []) or [])]
            return []

        if by == "name":
            name = str(value or "").lower()
            for node in self.graph.nodes.values():
                if node.name.lower() == name or node.id.lower() == name:
                    return [node]
            return []

        if by == "tag":
            tag = str(value or "").lower()
            # Characters: match against player.tags (live) — the graph node's
            # properties.tags may lag behind player mutations.
            if game_state is not None:
                players = getattr(game_state, "players", None) or {}
                char_results = []
                for pname, player in players.items():
                    if tag in [str(t).lower() for t in (player.tags or [])]:
                        node = self._player_node_for_name(pname)
                        if node:
                            char_results.append(node)
                if scope == "area" and area_id:
                    area_lower = area_id.lower()
                    char_results = [n for n in char_results
                                    if any(e.type == EDGE_IN and e.source == n.id and e.target.lower() == area_lower
                                           for e in self.graph.edges)]
                return char_results
            # No game state — fall back to graph tag scan.
            if scope == "world":
                return [n for n in self.graph.nodes.values()
                        if tag in [str(t).lower() for t in (n.properties.get("tags", []) or [])]]
            if area_id:
                return self._get_items_by_tag_in_area(tag, None, area_id)
            return []

        if by == "trait":
            trait = str(value or "").lower()
            if game_state is None:
                return []
            players = getattr(game_state, "players", None) or {}
            results = []
            for pname, player in players.items():
                if trait in [str(t).lower() for t in (player.traits or {}).keys()]:
                    node = self._player_node_for_name(pname)
                    if node:
                        results.append(node)
            return results

        if by == "type":
            node_type = str(value or "").lower()
            match_types = {node_type}
            if node_type in ("character", "player"):
                match_types = {"character", "player"}
            if scope == "world":
                return [n for n in self.graph.nodes.values() if n.type in match_types]
            if area_id:
                area_lower = area_id.lower()
                return [n for n in self.graph.nodes.values()
                        if n.type in match_types
                        and any(e.type == EDGE_IN and e.source == n.id and e.target.lower() == area_lower
                                for e in self.graph.edges)]
            return []

        if by == "all_in_area":
            if game_state is None or not area_id:
                return []
            players = getattr(game_state, "players", None) or {}
            area_lower = area_id.lower()
            results = []
            for pname, player in players.items():
                node = self._player_node_for_name(pname)
                if node and any(e.type == EDGE_IN and e.source == node.id and e.target.lower() == area_lower
                                for e in self.graph.edges):
                    results.append(node)
            return results

        return []

    def _execute_triggers(
        self,
        item_node: Node,
        trigger_type: str,
        target_name: Optional[str] = None,
        context: Optional[dict] = None,
        expected_target_state: Optional[str] = None,
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Execute all trigger edges from *item_node* matching *trigger_type*.

        Returns a list of output strings to append to the action result.

        Parameters
        ----------
        item_node : Node
            The item or node whose triggers should be evaluated.
        trigger_type : str
            The trigger type to match (e.g. ``"on_take"``, ``"on_use"``).
        target_name : str, optional
            Secondary target name (e.g. the target of ``on_use_on``).
        context : dict, optional
            Template-rendering context.  Auto-populated with default keys
            if not provided.
        expected_target_state : str, optional
            For ``on_state_enter`` / ``on_state_exit`` — the specific
            state to filter on.
        game_state : object, optional
            Duck-typed game state providing access to player data, area
            helpers, and scenario flags (see individual effect handler
            docstrings for requirements).

        *game_state* is consulted for the following when *context* is
        built or ``None``:

        * ``game_state.get_current_time()``
        * ``game_state.time_ticks``
        * ``game_state.turn_number``
        * ``game_state.active_player``
        * ``game_state.current_area``
        * ``game_state.player``
        """
        if item_node is None:
            return []
        outputs = []

        # ── Build template context ──
        if context is None:
            context = {}
        context.setdefault(
            "game_time",
            game_state.get_current_time() if game_state else "",
        )
        context.setdefault(
            "time_ticks", str(game_state.time_ticks) if game_state else ""
        )
        context.setdefault(
            "turn_number", str(game_state.turn_number) if game_state else ""
        )
        context.setdefault(
            "player_name", game_state.active_player if game_state else ""
        )
        context.setdefault(
            "area_name",
            game_state.current_area.name if game_state and game_state.current_area else "",
        )
        context.setdefault("item_name", item_node.name if item_node else "")
        context.setdefault(
            "item_state",
            item_node.properties.get("current_state", "") if item_node else "",
        )
        context.setdefault(
            "item_description",
            item_node.properties.get("description", "") if item_node else "",
        )
        context.setdefault("item_properties", item_node.properties if item_node else {})
        if item_node:
            context.setdefault(
                "item_params", item_node.properties.get("parameters", {})
            )
        if target_name is not None:
            context.setdefault("target_name", target_name)
        if game_state and game_state.player:
            context.setdefault(
                "player_hp", str(game_state.player.vitals.get("HP", 0))
            )
            context.setdefault(
                "player_energy",
                str(game_state.player.vitals.get("Energy", 0)),
            )
            context.setdefault(
                "player_sanity",
                str(game_state.player.vitals.get("Sanity", 0)),
            )
        if game_state and game_state.current_area:
            env = game_state.current_area.environment
            context.setdefault("area_light", str(env.get("light", "")))
            context.setdefault("area_temp", str(env.get("temperature", "")))
            context.setdefault("area_smell", env.get("smell", ""))

        # ── Walk trigger edges ──
        triggers = self.graph.get_edges_for_source(
            item_node.id, EDGE_TRIGGERS
        )
        for trigger_edge in triggers:
            trigger_types_on_edge = trigger_edge.properties.get("trigger_type", "")

            # ── Filter by trigger type ──
            if isinstance(trigger_types_on_edge, list):
                if trigger_type not in trigger_types_on_edge:
                    continue
                if trigger_type == "on_use_on" and target_name:
                    required_target = trigger_edge.properties.get(
                        "target_name", ""
                    ).lower()
                    if required_target and target_name.lower() != required_target:
                        continue
                    required_tag = trigger_edge.properties.get("target_tag", "")
                    if required_tag:
                        target_node = self._find_target_node(target_name, game_state)
                        if not target_node or required_tag not in (target_node.properties.get("tags", []) or []):
                            continue
            else:
                if (
                    trigger_types_on_edge == "on_use_on"
                    and target_name
                ):
                    required_target = trigger_edge.properties.get(
                        "target_name", ""
                    ).lower()
                    if required_target and target_name.lower() != required_target:
                        continue
                    required_tag = trigger_edge.properties.get("target_tag", "")
                    if required_tag:
                        target_node = self._find_target_node(target_name, game_state)
                        if not target_node or required_tag not in (target_node.properties.get("tags", []) or []):
                            continue
                elif trigger_types_on_edge != trigger_type and not (
                    trigger_types_on_edge.startswith("on_use_on")
                    and trigger_type == "on_use_on"
                ):
                    continue

            # ── Filter by expected target state ──
            if expected_target_state is not None:
                all_types = (
                    trigger_types_on_edge
                    if isinstance(trigger_types_on_edge, list)
                    else [trigger_types_on_edge]
                )
                if any(
                    type_name in ("on_state_enter", "on_state_exit")
                    for type_name in all_types
                ):
                    required_state = trigger_edge.properties.get(
                        "target_state", ""
                    )
                    if required_state and required_state != expected_target_state:
                        continue

            # ── Resolve conditions (backward-compatible lookup) ──
            conditions_list = trigger_edge.properties.get("conditions", None)
            if conditions_list is None:
                target_node = self.graph.get_node(trigger_edge.target)
                if target_node:
                    conditions_list = target_node.properties.get(
                        "conditions", None
                    )
            # Fallback: singular condition (legacy library format)
            if conditions_list is None or conditions_list == []:
                single = trigger_edge.properties.get("condition", None)
                if single is None:
                    target_node = self.graph.get_node(trigger_edge.target)
                    if target_node:
                        single = target_node.properties.get("condition", None)
                if single:
                    conditions_list = [single]
            if conditions_list is None:
                conditions_list = []

            # ── Resolve effects (effects[], or legacy effect_type/effect_params) ──
            effects_list = _resolve_trigger_effects(trigger_edge, self.graph)

            # ── Evaluate conditions (unified tree/flat) ──
            conditions_pass = True
            if conditions_list:
                cond_context = dict(context)
                cond_context["item_node"] = item_node
                if game_state is not None:
                    cond_context["game_state"] = game_state
                # Resolve the used-on target (on_use_on) up front so
                # target_has_tag conditions can inspect it. Ways resolve via
                # name or exit-direction; items/areas/characters by name.
                if trigger_type == "on_use_on" and target_name:
                    cond_context["target_node"] = self._find_target_node(
                        target_name, game_state
                    )
                if not isinstance(conditions_list, dict) or "operator" not in conditions_list:
                    # Flat list — apply conditions_logic
                    conditions_logic = trigger_edge.properties.get(
                        "conditions_logic", "and"
                    )
                    cond_tree = {
                        "operator": conditions_logic,
                        "conditions": conditions_list,
                    }
                else:
                    cond_tree = conditions_list

                conditions_pass = self._evaluate_conditions(
                    cond_tree, cond_context, game_state=game_state
                )

                if not conditions_pass:
                    fail_msg = (
                        effects_list[0]
                        .get("params", {})
                        .get("fail_message", "")
                        if effects_list
                        else ""
                    )
                    if fail_msg:
                        fail_msg = self._render_template(fail_msg, context)
                        outputs.append(fail_msg)

            # Surface skill-check / save roll messages
            if self._last_skill_check_msg:
                outputs.append(self._last_skill_check_msg)
                self._last_skill_check_msg = None
            if self._last_save_msg:
                outputs.append(self._last_save_msg)
                self._last_save_msg = None

            if not conditions_pass:
                continue

            # ── Execute all effects in order ──
            for effect in effects_list:
                effect_type = effect.get("type", "message")
                effect_params = effect.get("params", {})
                if not isinstance(effect_params, dict):
                    effect_params = {}

                if effect_params.get("success_message"):
                    effect_params = dict(effect_params)
                    effect_params["message"] = effect_params["success_message"]

                # Check for fan-out targeting (by name/tag/trait/type/all_in_area,
                # or legacy target_tag). When targets resolve, run the effect once
                # per target node; otherwise fall through to the single execution.
                targets = self._resolve_effect_targets(effect_params, item_node, game_state)
                if targets:
                    for target_node in targets:
                        # Build a context that references the target, not the trigger source
                        tag_context = dict(context)
                        tag_context["target_item_name"] = target_node.name
                        tag_context["target_item_state"] = target_node.properties.get("current_state", "")
                        tag_context["target_node"] = target_node
                        # For character targets, effect handlers resolve `target`
                        # against player names — pass the resolved name explicitly.
                        tparams = effect_params
                        if target_node.type in ("player", "character") and isinstance(effect_params, dict):
                            tparams = dict(effect_params)
                            tparams["target"] = tparams.get("target", "self")
                            if tparams["target"] in ("self", "all_in_area"):
                                tparams["target"] = target_node.name
                        outputs.extend(
                            self._effects.execute(
                                effect_type,
                                tparams,
                                tag_context,
                                item_node=target_node,
                                game_state=game_state,
                            )
                        )
                    continue  # skip the default single-item execution

                # For on_use_on, resolve target node for effects that need it
                target_item_node = None
                if trigger_type == "on_use_on" and target_name:
                    target_item_node = self._find_target_node(target_name, game_state)
                outputs.extend(
                    self._effects.execute(
                        effect_type,
                        effect_params,
                        context,
                        item_node=item_node,
                        target_item_node=target_item_node,
                        game_state=game_state,
                    )
                )

        return outputs

    # ─────────────────── Trigger testing (editor run button) ───────────────────

    def test_trigger(
        self,
        trigger_def: dict,
        item_node: Optional[Node] = None,
        game_state: Optional[Any] = None,
        dry_run: bool = True,
        context: Optional[dict] = None,
    ) -> dict:
        """Evaluate a single trigger definition against the live world.

        Used by the editor's "Run" button to test a trigger without having to
        play through the scenario. ``trigger_def`` is the trigger's ``properties``
        dict (``trigger_type``, ``conditions``, ``effects``, ``conditions_logic``).

        Returns a dict:
        - ``trigger_type`` — the trigger's type
        - ``conditions`` — list of ``{condition, expected, passed, detail}``
        - ``conditions_pass`` — whether all conditions evaluated true
        - ``fireable`` — whether the trigger type makes sense in this context
        - ``outputs`` — the messages the effects WOULD produce (dry run) or DID
          produce (live run)
        - ``side_effects`` — list of strings describing what a live run changed

        In dry-run mode, effects are NOT executed — instead each effect's type +
        params are reported as "would run". In live mode, effects run through the
        normal pipeline and ``outputs`` holds the real result messages.
        """
        trigger_type = trigger_def.get("trigger_type", "")
        # The editor stores trigger_type as an array (multi-select). Normalize
        # to the first entry so the fireable check + output label work.
        if isinstance(trigger_type, (list, tuple)):
            trigger_type = str(trigger_type[0]) if trigger_type else ""
        conditions = trigger_def.get("conditions", [])
        conditions_logic = trigger_def.get("conditions_logic", "and")
        effects = _effects_list_from_properties(trigger_def) or []
        if not effects:
            effects = [{"type": "message", "params": {}}]
        if context is None:
            context = {}
        context = dict(context)
        context["item_node"] = item_node
        if game_state is not None:
            context["game_state"] = game_state

        # Build template context like _execute_triggers does
        context.setdefault(
            "game_time", game_state.get_current_time() if game_state else ""
        )
        context.setdefault(
            "time_ticks", str(game_state.time_ticks) if game_state else ""
        )
        context.setdefault(
            "turn_number", str(game_state.turn_number) if game_state else ""
        )
        context.setdefault(
            "player_name", game_state.active_player if game_state else ""
        )
        context.setdefault(
            "area_name",
            game_state.current_area.name if game_state and game_state.current_area else "",
        )
        context.setdefault("item_name", item_node.name if item_node else "")
        context.setdefault(
            "item_state",
            item_node.properties.get("current_state", "") if item_node else "",
        )
        context.setdefault(
            "item_description",
            item_node.properties.get("description", "") if item_node else "",
        )
        context.setdefault("item_properties", item_node.properties if item_node else {})
        if item_node:
            context.setdefault(
                "item_params", item_node.properties.get("parameters", {})
            )
        if game_state and game_state.player:
            context.setdefault(
                "player_hp", str(game_state.player.vitals.get("HP", 0))
            )
            context.setdefault(
                "player_energy",
                str(game_state.player.vitals.get("Energy", 0)),
            )
            context.setdefault(
                "player_sanity",
                str(game_state.player.vitals.get("Sanity", 0)),
            )

        # Does this trigger type plausibly fire in this context?
        itemful_types = {
            "on_take", "on_drop", "on_examine", "on_inspect", "on_use",
            "on_use_on", "on_eat", "on_drink", "on_read", "on_light",
            "on_activate", "on_equip", "on_unequip", "on_throw", "on_break",
            "on_toggle_on", "on_toggle_off", "on_depleted", "on_open",
            "on_close", "on_state_enter", "on_state_exit", "on_auto_open",
        }
        if not trigger_type:
            fireable = False
            fireable_reason = "no trigger type selected"
        else:
            fireable = trigger_type not in itemful_types or item_node is not None
            fireable_reason = (
                "" if fireable else
                f"this trigger type ({trigger_type}) needs an item/way context to fire"
            )

        # Evaluate conditions individually + as a tree
        cond_results = []
        if conditions:
            cond_tree = (
                {"operator": conditions_logic, "conditions": conditions}
                if isinstance(conditions, list)
                else conditions
            )
            cond_pass = self._evaluate_conditions(
                cond_tree, context, game_state=game_state
            )
            for cond in (conditions if isinstance(conditions, list) else conditions.get("conditions", [])):
                ctype = cond.get("type", "")
                try:
                    # Evaluate via the tree wrapper so context (speech, area, etc.)
                    # reaches leaf conditions exactly like the live trigger walk.
                    passed = self._evaluate_conditions(
                        {"operator": "and", "conditions": [cond]},
                        context,
                        game_state=game_state,
                    )
                except Exception as e:  # pragma: no cover - defensive
                    passed = False
                cond_results.append({
                    "condition": ctype,
                    "passed": passed,
                    "detail": cond,
                })
        else:
            cond_pass = True
            cond_results = [{"condition": "(none)", "passed": True, "detail": {}}]

        outputs = []
        side_effects = []

        if dry_run or not cond_pass:
            # Report what WOULD run without touching the world
            for effect in effects:
                etype = effect.get("type", "message")
                eparams = effect.get("params", {})
                if isinstance(eparams, dict) and eparams.get("success_message"):
                    eparams = dict(eparams)
                    eparams["message"] = eparams["success_message"]
                rendered_msg = self._render_template(
                    eparams.get("message", ""), context
                )
                outputs.append(
                    f"[dry-run] {etype}" + (f": {rendered_msg}" if rendered_msg else "")
                )
                if etype in ("apply_trait", "remove_trait"):
                    target = eparams.get("target", "self")
                    side_effects.append(
                        f"would {etype.replace('_', ' ')} '{eparams.get('trait', '?')}' on {target}"
                    )
                elif eparams.get("node_id") or eparams.get("target"):
                    side_effects.append(f"would modify node: {eparams.get('node_id') or eparams.get('target')}")
                if etype in ("spawn_item", "remove_item", "teleport", "set_environment", "adjust_vital"):
                    side_effects.append(f"would run effect: {etype}")
        else:
            # Live run — build a fake trigger edge and walk it via _execute_triggers
            for effect in effects:
                etype = effect.get("type", "message")
                eparams = effect.get("params", {})
                if isinstance(eparams, dict) and eparams.get("success_message"):
                    eparams = dict(eparams)
                    eparams["message"] = eparams["success_message"]
                try:
                    result = self._effects.execute(
                        etype, eparams, context,
                        item_node=item_node, game_state=game_state,
                    )
                    outputs.extend(result)
                except Exception as e:  # pragma: no cover - defensive
                    outputs.append(f"[effect error: {e}]")

        return {
            "trigger_type": trigger_type,
            "conditions": cond_results,
            "conditions_pass": cond_pass,
            "fireable": fireable,
            "fireable_reason": fireable_reason,
            "outputs": outputs,
            "side_effects": side_effects,
        }
