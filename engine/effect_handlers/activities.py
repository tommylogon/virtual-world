"""Activity effect handlers for the virtual world trigger system.

@module effect_handlers/activities
@contributes the ``start_activity`` trigger effect
@docs docs/virtualWorld/Characters/Activities & States.md
"""


def handle_start_activity(self, params, context, item_node=None, game_state=None):
    """Start a persistent activity for the active actor.

    params: {"activity_type": "fishing", "target_item": "river",
             "duration_minutes": 120}
    """
    activity_type = str(params.get("activity_type") or "").strip()
    if not activity_type:
        return []
    target = params.get("target", "self")
    if target == "target":
        target = context.get("target_name") or (
            game_state.active_player if game_state else ""
        )
    pname = self._resolve_player_name(game_state, target) if game_state else target
    target_item = params.get("target_item")
    duration_ticks = params.get("duration_ticks")
    duration_minutes = params.get("duration_minutes")
    if game_state is not None:
        try:
            msg = game_state.activities.start_activity(
                pname, activity_type, target_item, duration_ticks,
                duration_minutes=duration_minutes,
            )
            return [msg]
        except Exception as exc:
            return [str(exc)]
    return [f"{pname} starts {activity_type}."]


HANDLERS = {
    "start_activity": handle_start_activity,
}
