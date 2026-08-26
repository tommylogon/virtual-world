"""Single-condition evaluation helpers for TriggerSystem.

Moved from engine/trigger_system.py.
"""

import random
from typing import Any, Optional

from graph import EDGE_CARRYING, EDGE_EQUIPPED, Node


class EvaluationMixin:
    """Condition evaluation methods."""

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
