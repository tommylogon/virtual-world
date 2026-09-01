"""Spawn/build effect handlers (spawn_item, give_item, spawn_character, remove_item)."""

from graph import Edge, EDGE_IN, EDGE_CARRYING, EDGE_TRIGGERS


def _natural_article(name: str) -> str:
    """'a'/'an' for a noun phrase — 'an Everflame Ember', 'a Key'."""
    head = str(name or "").strip().lstrip('"\'')
    return "an" if head[:1].lower() in "aeiou" else "a"


def _capture_recent(self, game_state, item_node, capture: str, limit: int) -> list:
    """Pull recent speech/turn events for the current area into a text list.

    task-298: record what was actually said/nearby into a freshly spawned
    item's description (a camera photo, a recorder's tape, an EVP log).
    Sources (duck-typed, newest first): ``turn_events`` entries with
    ``action``/``actor``/``description``.

    capture modes:
      ``speech`` — spoken lines only (a recorder's tape)
      ``sight``  — visible events only, speech excluded (a camera photo)
      anything else — unfiltered (every described event in the area)
    """
    if game_state is None:
        return []
    events = getattr(game_state, "turn_events", None)
    if events is None:
        legacy = getattr(game_state, "legacy", None)
        events = getattr(legacy, "turn_events", None) if legacy is not None else None
    if not events:
        return []

    area_id = None
    if item_node is not None:
        for edge in self.graph.get_edges_for_source(item_node.id, EDGE_IN):
            area_id = edge.target
            break
    if area_id is None and game_state is not None and hasattr(game_state, "get_current_area_id"):
        try:
            area_id = game_state.get_current_area_id()
        except Exception:
            area_id = None
    area_node = self.graph.get_node(area_id) if area_id else None
    area_name = area_node.name if area_node is not None else None

    speech_actions = ("speech", "speak", "whisper", "say", "shout")
    lines = []
    for ev in reversed(events):
        if not isinstance(ev, dict):
            continue
        ev_area = ev.get("area") or ""
        if area_name and ev_area and ev_area != area_name:
            continue
        action = str(ev.get("action", "")).lower()
        text = str(ev.get("description") or ev.get("text") or "")
        if not text:
            continue
        if capture == "speech" and action not in speech_actions:
            continue
        if capture == "sight" and (action in speech_actions or action == "llm_log"):
            continue
        actor = str(ev.get("actor", "")).strip()
        lines.append(f"{actor}: {text}" if actor else text)
        if len(lines) >= limit:
            break
    return lines


def handle_spawn_item(self, params, context, item_node=None, game_state=None):
    """Spawn a new item into the current area (default) or into a container.

    params:
      item_id — library / graph id to spawn
      into — ``"area"`` (default) or ``"container"`` (``EDGE_IN`` into the
             triggering container; requires ``item_node``)
      capture — ``"speech"`` (recorder tape) or ``"sight"`` (camera photo);
             appends the captured lines to the spawned item's description
      capture_limit — max captured lines (default 5)
      message / fail_message — narration on success / capacity failure

    game_state must provide: game_state.get_current_area_id() -> str | None
    """
    spawn_id = params.get("item_id", "")
    if not spawn_id:
        return []
    spawn_node, _ = self._hydrate_item(spawn_id, params, always_fresh=True)
    if spawn_node is None:
        return []
    if params.get("current_state") and spawn_node is not None:
        spawn_node.properties["current_state"] = params["current_state"]

    # task-298: capture recent speech/events into the spawned item's
    # description (a recorder capturing what was actually said).
    capture = (params.get("capture") or "").strip().lower()
    if capture and spawn_node is not None:
        captured = _capture_recent(
            self, game_state, item_node, capture,
            int(params.get("capture_limit", 5)),
        )
        if captured:
            base = spawn_node.properties.get("description") or ""
            spawn_node.properties["description"] = (
                (base + "\n\n") if base else ""
            ) + "\n".join(captured)

    item_weight = float(spawn_node.properties.get("weight", 0) or 0)
    into = (params.get("into") or "area").lower()

    if into == "container":
        if item_node is None:
            return [params.get("fail_message", "Nothing to put that into.")]
        cap_error = self._check_container_capacity(
            game_state, item_node.id, item_weight
        )
        if cap_error:
            return [params.get("fail_message") or cap_error]
        for edge in self.graph.edges[:]:
            if edge.source == spawn_node.id and edge.type in (EDGE_IN, EDGE_CARRYING):
                self.graph.edges.remove(edge)
        self.graph.add_edge(
            Edge(source=spawn_node.id, target=item_node.id, type=EDGE_IN)
        )
        msg = params.get("message") or f"{_natural_article(spawn_node.name)} {spawn_node.name} appears inside the {item_node.name}."
        return [self._render_template_fn(msg, context)]

    area_id = game_state.get_current_area_id() if game_state else None
    if not area_id:
        return []
    for edge in self.graph.edges[:]:
        if edge.source == spawn_node.id and edge.type == EDGE_IN:
            self.graph.edges.remove(edge)
    self.graph.add_edge(
        Edge(source=spawn_node.id, target=area_id, type=EDGE_IN)
    )
    msg = params.get("message") or f"{_natural_article(spawn_node.name)} {spawn_node.name} appears!"
    return [self._render_template_fn(msg, context)]


def handle_give_item(self, params, context, item_node=None, game_state=None):
    """Place a library item directly into a character's inventory.

    params:
      item_id (str) — library id (or existing graph node id) to give.
      target — ``"self"`` (active player, default), ``"target"``
               (the on_use_on target), or a character name.
      message (str) — optional narration (supports {target_name}).
      display_name / description / current_state — overrides when
        hydrating from the library (same knobs as spawn_item).

    Unlike ``spawn_item`` (drops in the area), this attaches the item via
    a ``carrying`` edge, so the character is immediately infected / in
    possession — e.g. a failed Medicine check on a corpse puts the hidden
    disease carrier on you.
    """
    item_id = params.get("item_id", "")
    if not item_id:
        return []
    target = params.get("target", "self")
    if target == "target":
        target = context.get("target_name") or (game_state.active_player if game_state else "")
    if game_state is None:
        return []
    pname = self._resolve_player_name(game_state, target)
    player_node_id = f"player_{pname}".replace(" ", "_")
    if not self.graph.get_node(player_node_id):
        player_node = next((n for n in self.graph.nodes.values()
                            if n.type in ("player", "character") and n.name == pname), None)
        if player_node is None:
            return []
        player_node_id = player_node.id

    node, _ = self._hydrate_item(item_id, params, always_fresh=True)
    if node is None:
        return []
    if params.get("current_state") and node is not None:
        node.properties["current_state"] = params["current_state"]

    item_weight = float(node.properties.get("weight", 0) or 0)
    cap_error = self._check_target_capacity(game_state, pname, player_node_id, item_weight)
    if cap_error:
        return [cap_error]

    # Clear any area/container/carrying placement, then attach to the character
    for edge in self.graph.edges[:]:
        if edge.source == node.id and edge.type in (EDGE_IN, EDGE_CARRYING):
            self.graph.edges.remove(edge)
    self.graph.add_edge(
        Edge(source=node.id, target=player_node_id, type=EDGE_CARRYING)
    )
    msg = params.get("message", f"{node.name} is added to your inventory.")
    return [self._render_template_fn(msg, context)]


def handle_spawn_character(self, params, context, item_node=None, game_state=None):
    """Spawn a character from the library into the world.

    params:
      character_id — library id to spawn
      area — optional area name override (defaults to current actor's area)
      message — optional narration (supports {character_name})

    game_state must provide: add_player, get_player, get_current_area_id,
    set_player_area, active_player, graph.
    """
    char_id = params.get("character_id", "")
    if not char_id:
        return []

    player_obj, _ = self._hydrate_character(char_id, params, game_state)
    if player_obj is None:
        return []

    if params.get("display_name") or params.get("name"):
        player_obj.name = params.get("display_name") or params.get("name")
    if params.get("description"):
        player_obj.description = params["description"]
    if params.get("current_state"):
        player_obj.state = params["current_state"]

    area_name = params.get("area")
    if not area_name and game_state:
        area_id = game_state.get_current_area_id()
        if area_id:
            area_node = game_state.graph.get_node(area_id)
            if area_node:
                area_name = area_node.name

    if area_name:
        player_obj.current_area = area_name

    if game_state is None:
        return []

    prev_active = game_state.active_player
    game_state.add_player(player_obj)
    if game_state.active_player != prev_active:
        game_state.active_player = prev_active

    if area_name:
        game_state.set_player_area(player_obj.name, area_name)

    msg = params.get("message") or f"{player_obj.name} arrives!"
    return [self._render_template_fn(msg, context)]


def handle_remove_item(self, params, context, item_node=None, game_state=None):
    """Remove an item node from the graph entirely.

    game_state: unused.
    """
    remove_id = params.get("item_id", "")
    if not remove_id:
        return []
    self.graph.remove_node(remove_id)
    return [params.get("message", f"{remove_id} vanishes!")]


HANDLERS = {
    "spawn_item": handle_spawn_item,
    "give_item": handle_give_item,
    "spawn_character": handle_spawn_character,
    "remove_item": handle_remove_item,
}
