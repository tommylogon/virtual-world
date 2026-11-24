"""Tests for SQLite-backed Event Stream & LLM Trace store (engine/stream_store.py + routes/stream_ops.py)."""
from __future__ import annotations

from flask import Flask

from engine.stream_store import StreamStore
from routes.stream_ops import stream_ops_bp


def test_stream_store_chronology_and_filters():
    store = StreamStore(":memory:")
    e1 = store.append_event(kind="thought", actor="elena vance", tick=0, game_time="08:00", turn_id="t0-elena", payload={"text": "Check the fireplace."})
    e2 = store.append_event(kind="speech", actor="elena vance", tick=0, game_time="08:00", turn_id="t0-elena", payload={"text": "Stay away from the wine.", "tone": "serious"})
    e3 = store.append_event(kind="speech", actor="miki", tick=1, game_time="08:05", turn_id="t1-miki", payload={"text": "Did you hear that click?"})
    # Bogus phase name should be filtered out of list_actors()
    store.append_event(kind="rawllm", actor="think-decide", tick=1, payload={"tokens": 200})

    assert [e1["seq"], e2["seq"], e3["seq"]] == [1, 2, 3]

    all_evts = store.query_events(limit=10)
    assert [e["seq"] for e in all_evts] == [1, 2, 3, 4]

    # Tick range filter
    t1_only = store.query_events(tick_from=1, tick_to=1)
    assert [e["actor"] for e in t1_only] == ["miki", "think-decide"]

    # Actor + search filter
    wine = store.query_events(actor="elena vance", search="wine")
    assert len(wine) == 1
    assert wine[0]["kind"] == "speech"

    # Pagination
    older = store.query_events(before_seq=3, limit=2)
    assert [e["seq"] for e in older] == [1, 2]

    # Actors list excludes LLM phases
    assert store.list_actors() == ["elena vance", "miki"]

    # Trace round-trip
    store.save_llm_trace(request_id="req-1", actor="elena vance", phase="think-decide", prompt="sys+user", response='{"action":"wait"}', tokens_in=400, tokens_out=20, latency_ms=310)
    trace = store.get_llm_trace("req-1")
    assert trace is not None
    assert trace["tokens_in"] == 400
    assert trace["response"] == '{"action":"wait"}'

    # Clear wipes both events and traces
    deleted = store.clear_world()
    assert deleted == 4
    assert store.query_events() == []
    assert store.get_llm_trace("req-1") is None
    store.close()


def test_stream_ops_blueprint_roundtrip():
    app = Flask(__name__)
    app.stream_store = StreamStore(":memory:")
    app.register_blueprint(stream_ops_bp)
    client = app.test_client()

    r_post = client.post("/api/stream", json={"kind": "speech", "actor": "miki", "tick": 2, "payload": {"text": "Hello?"}})
    assert r_post.status_code == 201
    assert r_post.get_json()["event"]["seq"] == 1

    r_get = client.get("/api/stream?actor=miki")
    assert r_get.status_code == 200
    body = r_get.get_json()
    assert len(body["events"]) == 1
    assert body["actors"] == ["miki"]

    r_trace = client.post("/api/stream/traces", json={"request_id": "r-99", "actor": "miki", "phase": "think-decide", "prompt": "p", "response": "r"})
    assert r_trace.status_code == 201
    r_trace_get = client.get("/api/stream/traces/r-99")
    assert r_trace_get.status_code == 200
    assert r_trace_get.get_json()["trace"]["response"] == "r"

    r_del = client.delete("/api/stream")
    assert r_del.status_code == 200
    assert r_del.get_json()["deleted"] == 1
