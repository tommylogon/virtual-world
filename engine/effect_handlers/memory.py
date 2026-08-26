"""Memory effect handlers (surface_memory, suppress_memory, unblock_memory)."""


def handle_surface_memory(self, params, context, item_node=None, game_state=None):
    """Force a matching memory into active recall with a salience boost.

    params:
      tags (list[str]) — memories tagged with ALL of these are matched.
      keywords (str) — text substring match (case-insensitive).
      salience_boost (int, default 3) — temporary relevance bump written
        into the memory entry as ``salience_override``.
      message (str) — optional narrative line; if empty, no output is
        emitted when there is no match.

    game_state must provide:
      game_state.players — dict of Player objects
      game_state.active_player — current active player name
    """
    tags = [str(t).lower() for t in (params.get("tags") or []) if t]
    keywords = (params.get("keywords") or "").lower().strip()
    salience_boost = int(params.get("salience_boost", 3))
    msg_template = params.get("message", "")

    player = self._resolve_memory_target(params, game_state)
    if player is None:
        return [msg_template] if msg_template else []

    matches = []
    for m in player.memories:
        if m.get("suppressions"):
            continue
        mem_tags = [t.lower() for t in (m.get("tags") or [])]
        tag_match = bool(tags) and all(t in mem_tags for t in tags)
        kw_match = bool(keywords) and keywords in m.get("text", "").lower()
        if (tags and tag_match) or (keywords and kw_match) or (not tags and not keywords):
            m["salience_override"] = salience_boost
            matches.append(m)

    if not matches:
        return [msg_template] if msg_template else []

    matches.sort(key=lambda m: m.get("importance", 5), reverse=True)
    top = matches[0]
    outputs = []
    if msg_template:
        outputs.append(msg_template.replace("{memory}", top.get("text", "")))
    return outputs


def handle_suppress_memory(self, params, context, item_node=None, game_state=None):
    """Mark matching memories as inaccessible for `duration` turns.

    params:
      tags (list[str])
      keywords (str)
      duration (int, default 1) — turns to suppress; 0 = permanent until
        ``unblock_memory`` fires.
      scope (str, default "self") — "self" or explicit character name.

    game_state must provide:
      game_state.players — dict of Player objects
      game_state.active_player — current active player name
    """
    player = self._resolve_memory_target(params, game_state)
    if player is None:
        return []
    tags = params.get("tags") or []
    keywords = params.get("keywords", "")
    duration = int(params.get("duration", 1))
    scope = params.get("scope", "self")
    suppressed = player.suppress_memory(tags=tags, keywords=keywords, duration=duration, scope=scope)
    msg = params.get("message", "")
    if suppressed and msg:
        return [msg]
    return []


def handle_unblock_memory(self, params, context, item_node=None, game_state=None):
    """Remove active suppressions from matching memories.

    params:
      tags (list[str])
      keywords (str)
      scope (str, default "self")

    game_state must provide:
      game_state.players — dict of Player objects
      game_state.active_player — current active player name
    """
    player = self._resolve_memory_target(params, game_state)
    if player is None:
        return []
    tags = params.get("tags") or []
    keywords = params.get("keywords", "")
    scope = params.get("scope", "self")
    unblocked = player.unblock_memory(tags=tags, keywords=keywords, scope=scope)
    msg = params.get("message", "")
    if unblocked and msg:
        return [msg]
    return []


HANDLERS = {
    "surface_memory": handle_surface_memory,
    "suppress_memory": handle_suppress_memory,
    "unblock_memory": handle_unblock_memory,
}
