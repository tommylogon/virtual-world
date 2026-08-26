"""Item verb facade.

The verb families live in focused modules under ``engine/items/`` (task-314
verb-family split); ``ItemActions`` composes them and owns the shared context
(graph, matching, trigger system, equipment, ghost system, world) plus the
capacity plumbing. Public helpers (``normalize_item_actions``,
carry-weight math, ``AmbiguousItemError``) are re-exported here so existing
imports keep working.
"""

from typing import Optional

from graph import EDGE_IN

from engine.items.consume_actions import ConsumeActionsMixin
from engine.items.carry_weight import (
    BASE_CARRY_CAPACITY,
    get_carry_load_ratio,
    sum_carry_weight,
)
from engine.items.errors import AmbiguousItemError
from engine.items.examine_actions import ExamineActionsMixin
from engine.items.place_actions import PlaceActionsMixin
from engine.items.take_drop_actions import TakeDropActionsMixin
from engine.items.transfer_actions import TransferActionsMixin
from engine.items.use_actions import UseActionsMixin

__all__ = [
    "AmbiguousItemError",
    "BASE_CARRY_CAPACITY",
    "INVERSE_ACTIONS",
    "ItemActions",
    "get_carry_load_ratio",
    "normalize_item_actions",
    "sum_carry_weight",
]

#: Actions that imply their inverse — defining one on an item auto-adds the other.
INVERSE_ACTIONS = {
    "take": "drop",
    "drop": "take",
    "equip": "unequip",
    "unequip": "equip",
    "open": "close",
    "close": "open",
}


def normalize_item_actions(actions):
    """Enrich an item's action list with the inverse of each defined action.

    Accepts a comma-separated string or a list of strings. Returns a
    deduplicated, whitespace-trimmed list. Unknown actions are kept as-is.
    """
    if isinstance(actions, str):
        actions = [a.strip() for a in actions.split(",")]
    actions = [a.strip() for a in (actions or []) if a and a.strip()]
    for action in list(actions):
        inverse = INVERSE_ACTIONS.get(action)
        if inverse and inverse not in actions:
            actions.append(inverse)
    return actions


class ItemActions(
    TakeDropActionsMixin,
    PlaceActionsMixin,
    TransferActionsMixin,
    ConsumeActionsMixin,
    UseActionsMixin,
    ExamineActionsMixin,
):
    """Handles all item-related actions: take, drop, use, eat, drink,
    examine, and inventory management."""

    def __init__(self, graph, matching, trigger_system, equipment, ghost_system, world):
        self.graph = graph
        self.matching = matching
        self.trigger_system = trigger_system
        self.equipment = equipment
        self.ghost_system = ghost_system
        # The owning VirtualWorld. Effects need it as game_state
        # (spawn_item/consume_item silently no-op without it).
        self.world = world

    def _exec_triggers(self, item_node, trigger_type, **kwargs):
        """Run trigger edges for *item_node*, always passing the world as
        game_state so world-dependent effects (spawn_item, consume_item,
        set_environment, …) work instead of silently no-op'ing."""
        return self.trigger_system._execute_triggers(
            item_node,
            trigger_type,
            game_state=getattr(self, "world", None),
            **kwargs
        )

    def _check_player_capacity(self, player_manager, item_weight: float, player_name: str = None) -> Optional[str]:
        """Check if a character can carry another item on top of what they hold.

        Capacity = ``BASE_CARRY_CAPACITY`` × trait ``carry_capacity_mod`` effects
        (trait schema v2). Returns an error message or None.

        ``player_name`` defaults to the active player; pass an explicit name to
        check a different character (used by the ``give_item`` trigger effect).
        """
        player_name = player_name or player_manager.active_player
        player = player_manager.players.get(player_name)
        if not player or item_weight <= 0:
            return None
        from engine.traits import TraitSystem
        player_id_fn = getattr(player_manager, 'get_player_node_id', None) or getattr(player_manager, '_player_node_id', None)
        if player_id_fn is None:
            return None
        player_id = player_id_fn(player_name)
        capacity = BASE_CARRY_CAPACITY * TraitSystem.get_carry_capacity_mod(player)
        current = sum_carry_weight(self.graph, player_id)
        if current + item_weight > capacity:
            return (
                f"That would exceed your carrying capacity "
                f"({current:.1f}/{capacity:.1f} kg)."
            )
        return None

    def _get_effective_weight(self, node, is_equipped=False, container_mod=1.0) -> float:
        return _node_effective_weight(node, is_equipped=is_equipped, container_mod=container_mod)

    def _sum_container_contents(self, container_id: str, container_mod: float) -> float:
        return _sum_container_contents(self.graph, container_id, container_mod)

    def _sum_carry_weight(self, player_id: str) -> float:
        return sum_carry_weight(self.graph, player_id)

    def get_carry_load_ratio(self, player_manager, player_name: str = None) -> dict:
        return get_carry_load_ratio(self.graph, player_manager, player_name=player_name)

    def _check_container_capacity(self, container_node_id: str, item_weight: float) -> Optional[str]:
        """Check if an item can fit in a container. Returns error message or None."""
        container_node = self.graph.get_node(container_node_id)
        if not container_node:
            return None
        max_cap = container_node.properties.get("max_weight_capacity")
        if max_cap is None:
            return None
        current_weight = 0
        for edge in self.graph.get_edges_for_target(container_node_id, EDGE_IN):
            content_node = self.graph.get_node(edge.source)
            if content_node:
                current_weight += content_node.properties.get("weight", 0)
        remaining = max_cap - current_weight
        if item_weight > remaining:
            container_name = container_node.name
            return (
                f"The {container_name} can't hold that — it's too heavy "
                f"(capacity: {current_weight:.1f}/{max_cap} kg)."
            )
        return None

