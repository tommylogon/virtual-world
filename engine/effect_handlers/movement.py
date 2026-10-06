"""Movement effect handlers for the virtual world trigger system."""


def handle_push_actor(self, params, context, item_node=None, game_state=None):
    """Push an actor along a connected downstream way using normal movement.

    params: {"direction": "south"}  OR  {"way_id": "way_river_01"}
    """
    if game_state is None:
        return []
    target = params.get("target", "self")
    if target == "target":
        target = context.get("target_name") or (
            game_state.active_player if game_state else ""
        )
    pname = self._resolve_player_name(game_state, target)
    player = getattr(game_state, "players", {}).get(pname)
    if player is None:
        return []
    direction = params.get("direction") or ""
    way_id = params.get("way_id") or ""
    area_id = player.current_area
    if not area_id:
        return []
    try:
        exits = game_state.build_exits_for_area(area_id, include_hidden=True) or {}
    except Exception:
        exits = {}
    dest = ""
    actual_direction = direction
    if way_id:
        for d, data in exits.items():
            if data.get("way_id") == way_id:
                dest = data.get("target") or ""
                actual_direction = d
                break
    else:
        data = exits.get(direction) or {}
        dest = data.get("target") or ""
    if not dest:
        return []
    old_active = getattr(game_state, "active_player", None)
    game_state.active_player = pname
    try:
        game_state.movement.move_to_area(actual_direction, kind="go")
        return []
    except Exception as exc:
        return [str(exc) or "the way is blocked"]
    finally:
        game_state.active_player = old_active


HANDLERS = {
    "push_actor": handle_push_actor,
}
