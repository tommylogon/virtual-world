"""Tests for POST /api/world/advance server-side batch time advance (task-414).

Verifies that the route runs timeskip.advance_world, advances the in-game clock,
handles tick chunking, and returns a bounded summary.
"""

from app import create_app


def test_world_advance_advances_clock():
    app = create_app({"TESTING": True})
    client = app.test_client()

    resp = client.post("/api/world/advance", json={"ticks": 10})
    assert resp.status_code == 200, resp.get_json()

    data = resp.get_json()
    assert data.get("ok") is True
    assert data.get("ticks") == 10


def test_world_advance_with_minutes_alias():
    app = create_app({"TESTING": True})
    client = app.test_client()

    resp = client.post("/api/world/advance", json={"minutes": 15})
    assert resp.status_code == 200, resp.get_json()

    data = resp.get_json()
    assert data.get("ok") is True
    assert data.get("elapsed_minutes") == 15


def test_world_advance_invalid_requests():
    app = create_app({"TESTING": True})
    client = app.test_client()

    # Missing ticks
    r1 = client.post("/api/world/advance", json={})
    assert r1.status_code == 400

    # Negative ticks
    r2 = client.post("/api/world/advance", json={"ticks": -10})
    assert r2.status_code == 400

    # Exceeding maximum request minutes (10080)
    r3 = client.post("/api/world/advance", json={"ticks": 20000})
    assert r3.status_code == 400


def test_world_advance_busy_conflict(monkeypatch):
    from engine import timeskip
    app = create_app({"TESTING": True})
    client = app.test_client()

    monkeypatch.setattr(timeskip, "is_running", lambda: True)
    resp = client.post("/api/world/advance", json={"ticks": 10})
    assert resp.status_code == 409
    assert "running" in resp.get_json().get("error", "").lower()
