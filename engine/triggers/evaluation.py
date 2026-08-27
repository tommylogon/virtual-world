"""Single-condition evaluation helpers for TriggerSystem.

Task-343: all leaf evaluation lives in ``ConditionTreeMixin._evaluate_conditions``
(engine/triggers/condition_tree.py) — this module kept only its resolver/comparison
helpers plus a delegating ``_evaluate_trigger_condition`` so the single-condition
entry point (movement ``requires_open``, facade wrappers) evaluates through the
same leaf registry as tree/list conditions.
"""

from typing import Any, Optional

from graph import Node


class EvaluationMixin:
    """Mixin providing evaluation helpers for TriggerSystem."""

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

        Task-343: delegates to ``ConditionTreeMixin._evaluate_conditions`` so
        both entry points share one leaf implementation (previously the two
        evaluators duplicated ~20 leaves and diverged — e.g. ``random_chance``
        always divided by 100 here, while the tree honours NPC-style
        0.0–1.0 ``chance`` vs item-trigger 0–100 ``value``).

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
        context = {"item_node": item_node}
        if game_state is not None:
            context["game_state"] = game_state
        return self._evaluate_conditions(condition, context, game_state=game_state)

