"""Time & weather effect handlers (task-234).

Adds trigger effects over the forecast/clock:
  - ``set_time`` / ``set_date`` — move the game clock / calendar
  - ``set_weather`` — GM-style global weather override for N turns
  - ``forecast_override`` — full override (weather/wind/humidity/temp/light/
    air/blood_moon) with optional countdown
  - ``adjust_forecast`` — delta-shift the active override
"""


def _set_keys(params, *keys):
    return {k: params.get(k) for k in keys if params.get(k) is not None}


def handle_set_time(params, context, item_node=None, game_state=None):
    """Set the game clock to a given hour (or HH:MM)."""
    if game_state is None:
        return []
    hour = params.get("hour")
    minute = params.get("minute", 0)
    if hour is None and params.get("time") is not None:
        hh, _, mm = str(params["time"]).partition(":")
        try:
            hour = int(hh or 0)
            minute = int(mm or 0)
        except (ValueError, TypeError):
            hour = None
    if hour is None:
        return [params.get("message", "[set_time] requires 'hour' or 'time'.")]
    game_state.set_game_time(int(hour), int(minute))
    return [params.get("message", f"The clock is set to {game_state.get_current_time()[:5]}.")]


def handle_set_date(params, context, item_node=None, game_state=None):
    """Set the game calendar (day/month/year — each optional)."""
    if game_state is None:
        return []
    day = params.get("day")
    month = params.get("month")
    year = params.get("year")
    if day is None and month is None and year is None:
        return [params.get("message", "[set_date] requires day/month/year.")]
    changed = game_state.set_game_date(day, month, year)
    if not changed:
        return [params.get("message", "[set_date] could not apply the requested date.")]
    return [params.get(
        "message",
        f"The date is set to Day {game_state.game_day}, Month {game_state.game_month}, Year {game_state.game_year}.")]


def handle_set_weather(params, context, item_node=None, game_state=None):
    """Globally set the weather (GM override, optional duration)."""
    if game_state is None:
        return []
    weather = params.get("weather")
    if not weather:
        return [params.get("message", "[set_weather] requires 'weather'.")]
    data = {"weather": weather}
    if params.get("duration_ticks") is not None:
        data["duration_ticks"] = int(params["duration_ticks"])
    game_state.set_forecast_override(data)
    return [params.get("message", f"The sky turns {weather}.")]


def handle_forecast_override(params, context, item_node=None, game_state=None):
    """Lock the forecast (globally) to explicit weather/wind/humidity/etc."""
    if game_state is None:
        return []
    data = _set_keys(params, "weather", "wind", "humidity", "temperature_mod",
                     "light_mod", "air", "blood_moon")
    if params.get("duration_ticks") is not None:
        data["duration_ticks"] = int(params["duration_ticks"])
    if params.get("clear") or params.get("clear_all"):
        data["clear_all"] = True
    game_state.set_forecast_override(data)
    keys = ", ".join(k for k in ("weather", "wind", "humidity", "temperature_mod",
                                 "light_mod", "air", "blood_moon") if k in data) or "nothing"
    return [params.get("message", f"Forecast override ({keys}).")]


def handle_adjust_forecast(params, context, item_node=None, game_state=None):
    """Delta-shift the active forecast override (temperature/light)."""
    if game_state is None:
        return []
    current = dict(getattr(game_state, "forecast_override", None) or {})
    if params.get("temperature_mod_delta") is not None:
        try:
            current["temperature_mod"] = float(current.get("temperature_mod", 0) or 0) + float(params["temperature_mod_delta"])
        except (ValueError, TypeError):
            pass
    if params.get("light_mod_delta") is not None:
        try:
            current["light_mod"] = float(current.get("light_mod", 0) or 0) + float(params["light_mod_delta"])
        except (ValueError, TypeError):
            pass
    if params.get("duration_ticks") is not None:
        current["duration_ticks"] = int(params["duration_ticks"])
    if not current:
        return [params.get("message", "[adjust_forecast] nothing to adjust.")]
    game_state.forecast_override = current
    return [params.get("message", "The forecast shifts.")]


HANDLERS = {
    "set_time": handle_set_time,
    "set_date": handle_set_date,
    "set_weather": handle_set_weather,
    "forecast_override": handle_forecast_override,
    "adjust_forecast": handle_adjust_forecast,
}
