"""Character tag effect handlers: interest and fear tags (task-469).

A trigger can author what a character is interested in or afraid of, e.g. an
on_enter trigger on a goblin camp adding ``goblin`` to a farmer's ``fear_tags``.
Tags are matched case-insensitively and stored on the Player, so they persist
with the save and drive the fear reaction in engine/fear.py.
"""


def _target_player(self, game_state, params, context):
    """Resolve the player an effect applies to (self | target | name)."""
    target = params.get("target", "self")
    if target == "target":
        target = context.get("target_name") or (game_state.active_player if game_state else "")
    if game_state is None:
        return None
    name = self._resolve_player_name(game_state, target)
    return game_state.players.get(name)


def _change(self, game_state, params, context, field, add):
    tag = str(params.get("tag", "")).strip().lower()
    if not tag:
        return []
    player = _target_player(self, game_state, params, context)
    if player is None:
        return []
    tags = getattr(player, field, None)
    if not isinstance(tags, list):
        tags = []
        setattr(player, field, tags)
    have = {str(t).lower() for t in tags}
    if add:
        if tag in have:
            return []
        tags.append(tag)
    else:
        if tag not in have:
            return []
        tags[:] = [t for t in tags if str(t).lower() != tag]
    message = params.get("message")
    return [message] if message else []


def handle_add_fear_tag(self, params, context, item_node=None, game_state=None):
    """params: {"tag": "goblin", "target": "self", "message": "..."}"""
    return _change(self, game_state, params, context, "fear_tags", True)


def handle_remove_fear_tag(self, params, context, item_node=None, game_state=None):
    return _change(self, game_state, params, context, "fear_tags", False)


def handle_add_interest_tag(self, params, context, item_node=None, game_state=None):
    return _change(self, game_state, params, context, "interest_tags", True)


def handle_remove_interest_tag(self, params, context, item_node=None, game_state=None):
    return _change(self, game_state, params, context, "interest_tags", False)


HANDLERS = {
    "add_fear_tag": handle_add_fear_tag,
    "remove_fear_tag": handle_remove_fear_tag,
    "add_interest_tag": handle_add_interest_tag,
    "remove_interest_tag": handle_remove_interest_tag,
}
