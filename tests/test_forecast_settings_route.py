"""Forecast authoring route (task-762).

The World Sky modal authors `forecast_schedule` over
`GET`/`POST /api/settings/forecast`. The POST used to whitelist a fixed set of
keys, so the task-763 generated-field fields (`area_overrides`, `date_overrides`)
would have been silently stripped on save. This pins the round-trip.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _client():
    from app import create_app
    app = create_app({"TESTING": True})
    return app, app.test_client()


def test_forecast_schedule_round_trips_through_the_route():
    _app, client = _client()
    schedule = {
        "mode": "generated", "seed": 42, "granularity": "weekly",
        "current_state": "cloudy", "transition_interval": 3,
        "transition_table": {"clear": {"cloudy": 3}},
        "entries": [{"offset": 0, "weather": "snowy", "wind": "gale",
                     "wind_direction": "north", "temperature_mod": -4,
                     "light_mod": -20, "air": "thin", "message": "snow begins"}],
        "area_overrides": {"area_x": "stormy"},
        "date_overrides": {"5": "foggy"},
    }
    resp = client.post("/api/settings/forecast", json={"schedule": schedule})
    assert resp.status_code == 200, resp.get_data(as_text=True)

    got = client.get("/api/settings/forecast").get_json()["forecast_schedule"]
    assert got["mode"] == "generated"
    assert got["seed"] == 42
    assert got["granularity"] == "weekly"
    assert got["transition_interval"] == 3
    assert got["transition_table"] == {"clear": {"cloudy": 3}}
    assert got["entries"][0]["weather"] == "snowy"
    assert got["entries"][0]["wind_direction"] == "north"
    assert got["entries"][0]["temperature_mod"] == -4
    # task-763 overrides must survive the POST (the whitelist used to drop them).
    assert got["area_overrides"] == {"area_x": "stormy"}
    assert got["date_overrides"] == {"5": "foggy"}


def test_the_get_exposes_the_generated_field_key():
    _app, client = _client()
    body = client.get("/api/settings/forecast").get_json()
    assert "weather_field" in body
    assert isinstance(body["weather_field"], dict)
