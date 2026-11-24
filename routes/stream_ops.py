"""Flask blueprint for the SQLite-backed Event Stream API."""
from __future__ import annotations

from typing import Optional

from flask import Blueprint, current_app, jsonify, request

from engine.stream_store import StreamStore

stream_ops_bp = Blueprint("stream_ops", __name__)


def _get_store() -> StreamStore:
    store = getattr(current_app, "stream_store", None)
    if store is None:
        store = StreamStore()
        current_app.stream_store = store
    return store


def _active_world_id() -> str:
    world = getattr(current_app, "world", None)
    wid = (
        getattr(world, "_scenario_name", None)
        or getattr(world, "world_name", None)
        or getattr(world, "name", None)
        or "default"
    )
    return str(wid).strip() or "default"


def _int_arg(name: str) -> Optional[int]:
    val = request.args.get(name)
    if val is None or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        return None


@stream_ops_bp.route("/api/stream", methods=["GET"])
def get_stream():
    store = _get_store()
    world_id = request.args.get("world_id") or _active_world_id()
    events = store.query_events(
        world_id=world_id,
        limit=_int_arg("limit") or 500,
        before_seq=_int_arg("before_seq"),
        after_seq=_int_arg("after_seq"),
        actor=request.args.get("actor") or None,
        kind=request.args.get("kind") or None,
        area=request.args.get("area") or None,
        tick_from=_int_arg("tick_from"),
        tick_to=_int_arg("tick_to"),
        search=request.args.get("search") or None,
    )
    actors = store.list_actors(world_id=world_id)
    return jsonify({"world_id": world_id, "events": events, "actors": actors})


@stream_ops_bp.route("/api/stream", methods=["POST"])
def post_stream():
    store = _get_store()
    data = request.get_json(silent=True) or {}
    kind = str(data.get("kind") or "").strip()
    if not kind:
        return jsonify({"error": "kind is required"}), 400
    world_id = str(data.get("world_id") or _active_world_id())
    world = getattr(current_app, "world", None)
    default_tick = int(getattr(world, "time_ticks", 0) or 0) if world else 0
    evt = store.append_event(
        world_id=world_id,
        kind=kind,
        actor=str(data.get("actor") or "World"),
        tick=int(data.get("tick", default_tick) or 0),
        game_time=str(data.get("game_time") or ""),
        turn_id=data.get("turn_id"),
        area=data.get("area"),
        phase=data.get("phase"),
        outcome=data.get("outcome"),
        request_id=data.get("request_id"),
        payload=data.get("payload") if isinstance(data.get("payload"), dict) else {},
    )
    return jsonify({"ok": True, "event": evt}), 201


@stream_ops_bp.route("/api/stream/batch", methods=["POST"])
def post_stream_batch():
    store = _get_store()
    data = request.get_json(silent=True) or {}
    items = data.get("events")
    if not isinstance(items, list):
        return jsonify({"error": "events list is required"}), 400
    world_id = str(data.get("world_id") or _active_world_id())
    if bool(data.get("replace", False)):
        store.clear_world(world_id=world_id)
    saved = store.append_events_batch(items, world_id=world_id)
    return jsonify({"ok": True, "count": len(saved), "world_id": world_id}), 201


@stream_ops_bp.route("/api/stream", methods=["DELETE"])
def delete_stream():
    store = _get_store()
    world_id = request.args.get("world_id") or _active_world_id()
    deleted = store.clear_world(world_id=world_id)
    return jsonify({"ok": True, "world_id": world_id, "deleted": deleted})


@stream_ops_bp.route("/api/stream/traces", methods=["POST"])
def post_llm_trace():
    store = _get_store()
    data = request.get_json(silent=True) or {}
    req_id = str(data.get("request_id") or "").strip()
    if not req_id:
        return jsonify({"error": "request_id is required"}), 400
    world_id = str(data.get("world_id") or _active_world_id())
    saved = store.save_llm_trace(
        request_id=req_id,
        world_id=world_id,
        tick=int(data.get("tick", 0) or 0),
        actor=str(data.get("actor") or ""),
        phase=str(data.get("phase") or ""),
        prompt=str(data.get("prompt") or ""),
        response=str(data.get("response") or ""),
        tokens_in=int(data.get("tokens_in", 0) or 0),
        tokens_out=int(data.get("tokens_out", 0) or 0),
        latency_ms=int(data.get("latency_ms", 0) or 0),
    )
    return jsonify({"ok": True, "trace": saved}), 201


@stream_ops_bp.route("/api/stream/traces/<request_id>", methods=["GET"])
def get_llm_trace(request_id: str):
    store = _get_store()
    trace = store.get_llm_trace(request_id)
    if not trace:
        return jsonify({"error": f"Unknown trace: {request_id}"}), 404
    return jsonify({"ok": True, "trace": trace})
