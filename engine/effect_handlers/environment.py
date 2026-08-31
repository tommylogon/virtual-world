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


HANDLERS = {
    "set_environment": handle_set_environment,
    "adjust_environment": handle_adjust_environment,
}
