"""Persona growth effect handlers (task-829).

@module effect-handlers/persona
@contributes set_persona_field, add/remove_persona_id, advance_age trigger effects

Every 828 field changes at runtime through four effects, all targeting a
character and persisting on the node's structured block (the state); the
explicit Compile refreshes the prose (the projection):

- ``set_persona_field {path, value}`` - dotted path write
  (``appearance.eyes.color``, ``identity.age`` ...). Lenses, scissors,
  tattoo kits and prosthetics are content carrying this effect, not code.
- ``add_persona_id`` / ``remove_persona_id {field, id}`` - id-list growth
  both directions (kinks, fears, traumas, interests ...).
- ``advance_age {years}`` - author age override until task-735's clock.

Fear/interest mirroring: ``fears``/``traumas`` entries also land on
``player.fear_tags`` and ``interests``/``likes`` on
``player.interest_tags``, because ``engine/fear.py`` and attention read
the Player today. Mirroring is additive-only on ``set`` (removal flows
through ``remove_persona_id``), so a trigger-added tag from another
source is never silently dropped by a set.
"""

from engine import character_appearance as ca

#: Node-list fields mirrored onto the Player, and onto which tag list.
_MIRROR = {
    "fears": "fear_tags",
    "traumas": "fear_tags",
    "interests": "interest_tags",
    "likes": "interest_tags",
}


def _target_pair(self, game_state, params, context):
    """Resolve (player, character-node) for a persona effect."""
    target = params.get("target", "self")
    if target == "target":
        target = context.get("target_name") or (
            game_state.active_player if game_state else "")
    node_id = params.get("node_id", "")
    if game_state is None:
        return None, None
    if node_id and node_id != "self":
        node = game_state.graph.get_node(node_id)
        return None, node
    name = self._resolve_player_name(game_state, target)
    player = (game_state.players or {}).get(name)
    node = None
    for getter in ("_player_node_id",):
        fn = getattr(game_state, getter, None)
        if fn is None:
            continue
        try:
            node = game_state.graph.get_node(fn(name))
        except Exception:
            node = None
        if node is not None:
            break
    if node is None:
        pm = getattr(game_state, "player_manager", None)
        getter = getattr(pm, "get_player_node_id", None) if pm else None
        if getter is not None:
            try:
                node = game_state.graph.get_node(getter(name))
            except Exception:
                node = None
    return player, node


def _mirror_add(player, field, entry):
    attr = _MIRROR.get(field)
    if player is None or attr is None:
        return
    tags = getattr(player, attr, None)
    if not isinstance(tags, list):
        tags = []
        setattr(player, attr, tags)
    if entry not in tags:
        tags.append(entry)


def _mirror_remove(player, field, entry):
    attr = _MIRROR.get(field)
    if player is None or attr is None:
        return
    tags = getattr(player, attr, None)
    if isinstance(tags, list) and entry in tags:
        tags.remove(entry)


def handle_set_persona_field(self, params, context, item_node=None,
                             game_state=None):
    """params: {"path": "appearance.eyes.color", "value": "blue",
    "target": "self", "message": "..."}"""
    path = str(params.get("path", "")).strip()
    if not path:
        return []
    _, node = _target_pair(self, game_state, params, context)
    if node is None:
        return []
    try:
        ca.set_persona_field(node, path, params.get("value"))
    except ca.StructuredError:
        return []
    parts = path.split(".")
    if parts[0] == "personality" and len(parts) == 2 and parts[1] in _MIRROR:
        player, _ = _target_pair(self, game_state, params, context)
        for entry in ((ca.get_record(node).get("personality") or {})
                      .get(parts[1]) or []):
            _mirror_add(player, parts[1], entry)
    message = params.get("message")
    return [message] if message else []


def handle_add_persona_id(self, params, context, item_node=None,
                          game_state=None):
    """params: {"field": "fears", "id": "deep-water", "target": "self"}"""
    field = str(params.get("field", "")).strip()
    entry = str(params.get("id", "")).strip()
    if not field or not entry:
        return []
    player, node = _target_pair(self, game_state, params, context)
    if node is None:
        return []
    try:
        changed = ca.add_persona_id(node, field, entry)
    except ca.StructuredError:
        return []
    if changed:
        _mirror_add(player, field, entry)
    message = params.get("message")
    return [message] if message else []


def handle_remove_persona_id(self, params, context, item_node=None,
                             game_state=None):
    """params: {"field": "kinks", "id": "teasing", "target": "self"}"""
    field = str(params.get("field", "")).strip()
    entry = str(params.get("id", "")).strip()
    if not field or not entry:
        return []
    player, node = _target_pair(self, game_state, params, context)
    if node is None:
        return []
    try:
        changed = ca.remove_persona_id(node, field, entry)
    except ca.StructuredError:
        return []
    if changed:
        _mirror_remove(player, field, entry)
    message = params.get("message")
    return [message] if message else []


def handle_advance_age(self, params, context, item_node=None,
                       game_state=None):
    """params: {"years": 5, "target": "self", "message": "..."}

    Moves the lifecycle birth tick earlier (the clock agrees) as well as
    the authored display age, so the sheet never disagrees with time.
    """
    if "years" not in params:
        return []
    player, node = _target_pair(self, game_state, params, context)
    if node is None:
        return []
    try:
        ca.advance_age(node, params.get("years"))
    except ca.StructuredError:
        return []
    if player is not None and game_state is not None:
        # The clock agrees: move the birth tick earlier so derived age
        # and display age stay the same number.
        try:
            from engine import lifecycle as _lifecycle
            _lifecycle.shift_birth_tick(player, game_state, params.get("years"))
        except Exception:
            pass
    message = params.get("message")
    return [message] if message else []


HANDLERS = {
    "set_persona_field": handle_set_persona_field,
    "add_persona_id": handle_add_persona_id,
    "remove_persona_id": handle_remove_persona_id,
    "advance_age": handle_advance_age,
}
