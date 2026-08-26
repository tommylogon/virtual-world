"""Teleport and movement effect handlers (teleport, unlock_way)."""

import time


def handle_teleport(self, params, context, item_node=None, game_state=None):
    """Teleport the active player to a different area.

    game_state must provide:
      game_state.player
      game_state._set_player_area(player_name, area_name)
      game_state.active_player
    """
    area_name = params.get("area", "")
    if not area_name or not game_state or not game_state.player:
        return []
    game_state._set_player_area(game_state.active_player, area_name)
    return [params.get("message", f"You are teleported to {area_name}!")]


def handle_unlock_way(
    self,
    params,
    context,
    item_node=None,
    target_item_node=None,
    game_state=None,
):
    """Set a door node to closed state (unlocking doesn't open it).

    ``way_id`` may be an explicit way id, ``"target"``, or blank — the
    latter two unlock the on_use_on target (the door the item was used
    on), resolved by the trigger system.

    game_state: unused.
    """
    way_id = params.get("way_id", "")
    way_node = (
        self.graph.get_node(way_id)
        if way_id and way_id != "target"
        else None
    )
    if way_node is None and way_id in ("", "target"):
        way_node = target_item_node
    if way_node and way_node.type == "way":
        way_node.properties["current_state"] = "closed"
        way_node.updated = time.time()
        return [params.get("message", "A lock clicks open!")]
    return []


HANDLERS = {
    "teleport": handle_teleport,
    "unlock_way": handle_unlock_way,
}
