"""Regression tests for lock-free external routes, non-world POST exemptions, and scoped pub/sub."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

from app import create_app
from engine.world_events import hub


def test_memory_retrieve_does_not_autosave_dirty_or_broadcast_world_changed():
    app = create_app({"TESTING": True})
    client = app.test_client()
    hero = app.world.get_active_player_obj() or next(iter(app.world.players.values()))
    hero.memories.append({"text": "Found a brass key by the fountain.", "tick": 1, "importance": 5})

    q = hub.subscribe()
    try:
        rev_before = app._state_revision
        edit_before = getattr(app.world, "_edit_seq", 0)
        undo_before = len(getattr(app, "_undo_stack", []))

        resp = client.post(
            f"/api/players/{hero.name}/memories/retrieve",
            json={"query": "brass key", "max_results": 3},
        )
        assert resp.status_code == 200
        assert app._state_revision == rev_before
        assert getattr(app.world, "_edit_seq", 0) == edit_before
        assert len(getattr(app, "_undo_stack", [])) == undo_before
        assert q.empty(), f"Expected no broadcast for memory retrieve, got {q.get_nowait()}"
    finally:
        hub.unsubscribe(q)


def test_non_world_posts_do_not_invalidate_state_or_broadcast():
    app = create_app({"TESTING": True})
    client = app.test_client()
    hero = app.world.get_active_player_obj() or next(iter(app.world.players.values()))

    q = hub.subscribe()
    try:
        rev_before = app._state_revision

        r1 = client.post("/api/action/validate", json={"action": "look", "character": hero.name})
        assert r1.status_code == 200
        assert app._state_revision == rev_before

        r_auto = client.post("/api/autocomplete", json={"prefix": "lo"})
        assert r_auto.status_code == 200
        assert app._state_revision == rev_before

        fake_resp = MagicMock(ok=True, status_code=200)
        fake_resp.json.return_value = {"data": [{"id": "test-model"}]}
        with patch("requests.get", return_value=fake_resp):
            r2 = client.post("/api/models", json={"api_base": "https://example.invalid/v1"})
        assert r2.status_code == 200
        assert app._state_revision == rev_before
        assert q.empty(), f"Expected no world_changed broadcast, got {q.get_nowait()}"
    finally:
        hub.unsubscribe(q)


def test_commons_messages_emit_commons_changed_unless_advancing_world_clock():
    app = create_app({"TESTING": True})
    client = app.test_client()
    hero = app.world.get_active_player_obj() or next(iter(app.world.players.values()))

    q = hub.subscribe()
    try:
        rev_before = app._state_revision
        r1 = client.post(
            "/api/commons/messages",
            json={"author": hero.name, "channel_id": "public", "text": "hey everyone"},
        )
        assert r1.status_code == 200
        assert app._state_revision == rev_before
        ev1 = q.get(timeout=1.0)
        assert ev1["type"] == "commons_changed"

        # With advance_tick=True in live world mode, world clock mutates -> world_changed + rev bump
        r2 = client.post(
            "/api/commons/messages",
            json={"author": hero.name, "channel_id": "public", "text": "time moves", "advance_tick": True},
        )
        assert r2.status_code == 200
        assert app._state_revision == rev_before + 1
        ev2 = q.get(timeout=1.0)
        assert ev2["type"] == "world_changed"
    finally:
        hub.unsubscribe(q)


def test_lock_free_external_proxy_routes_do_not_deadlock_under_write_lock():
    app = create_app({"TESTING": True})
    client = app.test_client()

    # Hold the global write lock on another thread and confirm /api/models still completes immediately.
    app._vw_rwlock.acquire_write()
    result = {}

    def _run():
        fake_resp = MagicMock(ok=True, status_code=200)
        fake_resp.json.return_value = {"data": [{"id": "fast-model"}]}
        with patch("requests.get", return_value=fake_resp):
            r = client.post("/api/models", json={"api_base": "https://example.invalid/v1"})
            result["status"] = r.status_code

    t = threading.Thread(target=_run)
    try:
        t.start()
        t.join(timeout=2.0)
        assert not t.is_alive(), "/api/models blocked on _vw_rwlock!"
        assert result.get("status") == 200
    finally:
        app._vw_rwlock.release_write()
