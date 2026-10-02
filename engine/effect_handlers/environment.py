"""Environment effect handlers (set_environment, adjust_environment)."""

import time


def handle_set_environment(self, params, context, item_node=None, game_state=None):
    """Override environment properties (light, temperature, air, etc.) on a area node.

    game_state must provide: game_state._light_to_level(val) -> str
    """
    target_id = params.get("node_id", "")
    if not target_id and game_state:
        target_id = game_state.get_current_area_id()
    if not target_id:
        return []
    area_node = self.graph.get_node(target_id)
    if area_node is None:
        return []
    env = area_node.properties.get("environment", {})
    if not isinstance(env, dict):
        env = {}
    for key in ["light", "temperature", "air", "smell", "noise",
                "weather", "wind", "humidity"]:
        if key in params:
            if key == "light":
                env[key] = game_state._light_to_level(params[key])
            else:
                env[key] = params[key]
    # task-234: transparent is a WAY property, not an area env key.
    if params.get("transparent") is not None and area_node.type == "way":
        area_node.properties["transparent"] = bool(params["transparent"])
    area_node.properties["environment"] = env
    area_node.updated = time.time()
    return [params.get("message", f"The environment in {area_node.name} shifts.")]


def handle_adjust_environment(self, params, context, item_node=None, game_state=None):
    """Incrementally adjust environment properties (temperature, light, air, etc.).

    game_state must provide: game_state.get_current_area_id() -> str | None
    """
    if game_state is None:
        return []
    area_id = game_state.get_current_area_id()
    if not area_id:
        return []
    area_node = self.graph.get_node(area_id)
    if area_node is None:
        return []
    env = area_node.properties.get("environment", {})
    for key in ["temperature", "light"]:
        if key in params:
            try:
                current = int(env.get(key, 0))
                env[key] = max(-50, min(100, current + int(params[key])))
            except (ValueError, TypeError):
                pass
    for key in ["air", "smell", "noise", "weather", "wind", "humidity"]:
        if key in params:
            env[key] = params[key]
    # task-234: adjust_weather / adjust_wind / adjust_humidity cycle the enum.
    cycles = {
        "adjust_weather": (params.get("adjust_weather"), __import__("engine.weather_forecast", fromlist=["WEATHER_STATES"]).WEATHER_STATES),
        "adjust_wind": (params.get("adjust_wind"), __import__("engine.weather_forecast", fromlist=["WIND_STATES"]).WIND_STATES),
        "adjust_humidity": (params.get("adjust_humidity"), __import__("engine.weather_forecast", fromlist=["HUMIDITY_STATES"]).HUMIDITY_STATES),
    }
    for key, (steps, states) in cycles.items():
        if steps is None:
            continue
        current = env.get(key.replace("adjust_", ""), states[0])
        try:
            idx = states.index(current) + int(steps)
        except ValueError:
            idx = int(steps) % len(states)
        env[key.replace("adjust_", "")] = states[idx % len(states)]
    area_node.properties["environment"] = env
    area_node.updated = time.time()
    msg = params.get("message", "The environment shifts.")
    msg = self._render_template_fn(msg, context)
    return [msg]


def handle_apply_area_status(self, params, context, item_node=None, game_state=None):
    """task-233: add a dynamic status (on_fire, flooded, poison_gas, ...) to an area.

    Params: target (area id; blank = current area), status_type, severity,
    duration (ticks; blank = until cleared), source.
    """
    if game_state is None or not hasattr(game_state, "area_statuses"):
        return [params.get("message", "[apply_area_status] area status system unavailable.")]
    target_id = params.get("target") or params.get("node_id") or ""
    if not target_id and hasattr(game_state, "get_current_area_id"):
        target_id = game_state.get_current_area_id() or ""
    status_type = params.get("status_type") or params.get("status") or ""
    if not status_type:
        return [params.get("message", "[apply_area_status] requires 'status_type'.")]
    severity = params.get("severity", 1)
    duration = params.get("duration")
    ok = game_state.area_statuses.apply_status(
        target_id, status_type,
        severity=int(severity) if severity is not None else 1,
        duration=int(duration) if duration not in (None, "") else None,
        source=params.get("source"),
    )
    if not ok:
        return [params.get("message", f"[apply_area_status] unknown area or status '{status_type}'.")]
    definition = __import__("engine.area_statuses", fromlist=["AREA_STATUS_DEFINITIONS"]).AREA_STATUS_DEFINITIONS.get(status_type, {})
    label = definition.get("name", status_type)
    msg = params.get("message", f"{label} takes hold of the area.")
    return [self._render_template_fn(msg, context) if hasattr(self, "_render_template_fn") else msg]


def handle_clear_area_status(self, params, context, item_node=None, game_state=None):
    """task-233: remove a status from an area (or all statuses with 'all': true)."""
    if game_state is None or not hasattr(game_state, "area_statuses"):
        return []
    target_id = params.get("target") or params.get("node_id") or ""
    if not target_id and hasattr(game_state, "get_current_area_id"):
        target_id = game_state.get_current_area_id() or ""
    system = game_state.area_statuses
    if params.get("all"):
        area = system.graph.get_node(target_id) if target_id else None
        if area is None:
            return []
        area.properties["statuses"] = []
        return [params.get("message", "The area settles.")]
    status_type = params.get("status_type") or params.get("status") or ""
    if not status_type:
        return [params.get("message", "[clear_area_status] requires 'status_type'.")]
    ok = system.clear_status(target_id, status_type)
    if not ok:
        return []
    return [params.get("message", f"The {status_type.replace('_', ' ')} subsides.")]


def handle_set_wet(self, params, context, item_node=None, game_state=None):
    """task-231: set/clear the ``wet`` flag on an item — or on everything the
    actor has equipped when no node is named (rain, wading, flooding...)."""
    if game_state is None:
        return []
    wet = params.get("wet", True)
    wet = wet if isinstance(wet, bool) else str(wet).lower() == "true"
    targets = []
    node_id = params.get("node_id") or ""
    if node_id and node_id != "self":
        node = self.graph.get_node(node_id)
        if node is not None:
            targets.append(node)
    elif item_node is not None:
        targets.append(item_node)
    else:
        # No node named → soak everything the active character has equipped.
        #
        # Read from the `equipped` EDGES rather than from `player.equipped` or
        # from an `equipment.get_equipped_items` helper that does not exist:
        # task-654 made the edges and the dict one fact written by one writer, and
        # the edges are the store both readers use. The dict would have been a
        # second answer to the same question.
        targets.extend(_equipped_items(game_state, _active_player_obj(game_state)))

    if not targets:
        return []
    for node in targets:
        node.properties["wet"] = wet
    # task-489: reflect wetness in the garment's own `current_state`, which is the
    # mechanism task-215 kept once it cancelled numeric opacity/friction.
    _mark_wet_current_state(targets, wet)
    # task-489: and regenerate the appearance description, so a soaked character
    # stops being described as dry. Delegated to
    # `_maybe_update_equipment_description`, which already honours
    # `world.auto_generate_descriptions`.
    _regenerate_wet_descriptions(game_state, targets)
    label = "soaks" if wet else "dries"
    return [params.get("message", f"You are {label}ed.") if wet
            else params.get("message", "You dry out.")]


def _active_player_obj(game_state):
    """The active character as a ``Player``.

    ``world.active_player`` is a **name**, not an object — so the old code in this
    branch passed a string to a helper, which meant the "soak everything the
    active character has equipped" path (rain, wading, flooding) silently targeted
    nothing. Resolution order is the object first, because
    ``world.player_manager.get_active_player_obj()`` is the authoritative
    accessor and this handler should not re-implement it.
    """
    manager = getattr(game_state, "player_manager", None)
    if manager is not None:
        getter = getattr(manager, "get_active_player_obj", None)
        if callable(getter):
            try:
                active = getter()
                if active is not None:
                    return active
            except Exception:
                pass
    active = getattr(game_state, "active_player", None)
    players = getattr(game_state, "players", None)
    if isinstance(active, str) and isinstance(players, dict):
        return players.get(active)
    return active
    if not targets:
        return []
    for node in targets:
        node.properties["wet"] = wet
    _mark_wet_current_state(targets, wet)
    # task-489: a state change that alters what a garment reads as has to
    # regenerate the appearance description, or the character stays described as
    # dry until something else happens to rewrite it. This was the item task-215
    # lists as still open ("Rain -> clothing wet -> description regenerates"), and
    # task-486's `_get_state_hash` already fingerprints `current_state`, so the
    # cached description correctly notices the change.
    _regenerate_wet_descriptions(game_state, targets, wet)
    label = "soaks" if wet else "dries"
    return [params.get("message", f"You are {label}ed.") if wet else params.get("message", "You dry out.")]


def _regenerate_wet_descriptions(game_state, targets) -> None:
    """Re-derive the appearance description for whoever is wearing these items.

    ``_maybe_update_equipment_description`` already honours
    ``world.auto_generate_descriptions``, so this respects it by delegating
    rather than re-checking. Failures are swallowed: a soak should never abort
    because a description could not be rewritten.
    """
    equipment = getattr(game_state, "equipment", None)
    if equipment is None:
        return
    players = getattr(game_state, "players", None)
    if not isinstance(players, dict):
        return
    worn = {getattr(node, "id", None) for node in targets or ()}
    for player in list(players.values()):
        equipped = getattr(player, "equipped", None) or {}
        worn_by_player = any(item in worn for stack in equipped.values()
                             if isinstance(stack, (list, tuple))
                             for item in stack)
        if not worn_by_player:
            continue
        try:
            equipment._maybe_update_equipment_description(player)
        except Exception:
            continue


#: The `current_state` a soaked garment carries. task-215 re-scoped layer
#: visibility to the item's own description rather than to numeric `opacity`, and
#: named `current_state` as one of the three things to keep — so this is how a
#: wet garment *reads* rather than a number the engine multiplies.
WET_CURRENT_STATE = "soaked"


def _equipped_items(game_state, player) -> list:
    """Every item node *player* is wearing, read from the `equipped` edges."""
    if player is None:
        return []
    world = getattr(game_state, "world", None) or game_state
    graph = getattr(world, "graph", None)
    if graph is None:
        return []
    try:
        from graph import EDGE_EQUIPPED
        player_manager = getattr(world, "player_manager", None)
        node_id = player_manager.get_player_node_id(
            getattr(player, "name", "")) if player_manager else None
        if not node_id:
            return []
        items = []
        for edge in graph.get_edges_for_target(node_id, EDGE_EQUIPPED):
            node = graph.get_node(edge.source)
            if node is not None and getattr(node, "type", None) == "item":
                items.append(node)
        return items
    except Exception:
        return []


def _mark_wet_current_state(nodes, wet: bool) -> None:
    """Reflect wetness in each garment's ``current_state``.

    Wetness is a **state**, not an adjective, so it belongs in the field the
    appearance prompt already renders rather than in a new numeric prop: a linen
    dress reads "Light linen, almost sheer in the sun." and then reads wet. Doing
    it this way is task-215's stated preference and costs no vocabulary.

    Two rules that only a test found:

    * **Soaking does not overwrite a state the author set.** A coat that was
      already ``"torn"`` reads torn, not soaked — and ``current_state`` is a
      single field, so there is no room for both. Wetness still shows up, because
      the ``wet`` property is what the insulation penalty reads.
    * **Drying removes only what a soak wrote.** Removing the field
      unconditionally would delete ``"torn"`` the moment the weather cleared.
    """
    for node in nodes or ():
        current = (node.properties or {}).get("current_state")
        if not wet:
            if current == WET_CURRENT_STATE:
                node.properties.pop("current_state", None)
            continue
        if not current:
            node.properties["current_state"] = WET_CURRENT_STATE



HANDLERS = {
    "set_environment": handle_set_environment,
    "adjust_environment": handle_adjust_environment,
    "apply_area_status": handle_apply_area_status,
    "clear_area_status": handle_clear_area_status,
    "set_wet": handle_set_wet,
}
