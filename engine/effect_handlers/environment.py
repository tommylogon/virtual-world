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
        equipment = getattr(game_state, "equipment", None)
        getter = getattr(equipment, "get_equipped_items", None) if equipment else None
        if callable(getter):
            try:
                targets.extend(getter(game_state.active_player) or [])
            except Exception:
                targets = []
    if not targets:
        return []
    for node in targets:
        node.properties["wet"] = wet
    label = "soaks" if wet else "dries"
    return [params.get("message", f"You are {label}ed.") if wet else params.get("message", "You dry out.")]


HANDLERS = {
    "set_environment": handle_set_environment,
    "adjust_environment": handle_adjust_environment,
    "apply_area_status": handle_apply_area_status,
    "clear_area_status": handle_clear_area_status,
    "set_wet": handle_set_wet,
}
