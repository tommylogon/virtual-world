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


def _active_branch_id() -> str:
    world = getattr(current_app, "world", None)
    tm = getattr(world, "timeline_manager", None) if world is not None else getattr(current_app, "timeline_manager", None)
    if tm is not None and getattr(tm, "active_branch_id", None):
        return str(tm.active_branch_id)
    return "main"


def _get_timeline_manager():
    world = getattr(current_app, "world", None)
    if world is not None and getattr(world, "timeline_manager", None) is not None:
        return world.timeline_manager
    return getattr(current_app, "timeline_manager", None)


@stream_ops_bp.route("/api/stream", methods=["GET"])
def get_stream():
    store = _get_store()
    world_id = request.args.get("world_id") or _active_world_id()
    branch_id = request.args.get("branch_id") or _active_branch_id()
    use_lineage = request.args.get("lineage", "1") != "0"
    tm = _get_timeline_manager()
    world = getattr(current_app, "world", None)
    current_tick = int(getattr(world, "time_ticks", 0) or 0) if world is not None else 0
    tick_to = _int_arg("tick_to")

    if use_lineage and tm is not None and hasattr(tm, "get_ancestry"):
        ancestry = tm.get_ancestry(branch_id)
        events = store.query_branch_lineage(
            world_id=world_id,
            ancestry=ancestry,
            limit=_int_arg("limit") or 500,
            before_seq=_int_arg("before_seq"),
            after_seq=_int_arg("after_seq"),
            actor=request.args.get("actor") or None,
            kind=request.args.get("kind") or None,
            area=request.args.get("area") or None,
            tick_from=_int_arg("tick_from"),
            tick_to=tick_to,
            search=request.args.get("search") or None,
        )
    else:
        events = store.query_events(
            world_id=world_id,
            branch_id=branch_id if request.args.get("branch_id") else None,
            limit=_int_arg("limit") or 500,
            before_seq=_int_arg("before_seq"),
            after_seq=_int_arg("after_seq"),
            actor=request.args.get("actor") or None,
            kind=request.args.get("kind") or None,
            area=request.args.get("area") or None,
            tick_from=_int_arg("tick_from"),
            tick_to=tick_to,
            search=request.args.get("search") or None,
        )
    actors = store.list_actors(world_id=world_id)
    return jsonify({
        "world_id": world_id,
        "branch_id": branch_id,
        "current_tick": current_tick,
        "events": events,
        "actors": actors,
    })


@stream_ops_bp.route("/api/stream", methods=["POST"])
def post_stream():
    store = _get_store()
    data = request.get_json(silent=True) or {}
    kind = str(data.get("kind") or "").strip()
    if not kind:
        return jsonify({"error": "kind is required"}), 400
    world_id = str(data.get("world_id") or _active_world_id())
    branch_id = str(data.get("branch_id") or _active_branch_id())
    world = getattr(current_app, "world", None)
    default_tick = int(getattr(world, "time_ticks", 0) or 0) if world else 0
    evt = store.append_event(
        world_id=world_id,
        branch_id=branch_id,
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
    branch_id = str(data.get("branch_id") or _active_branch_id())
    tm = _get_timeline_manager()
    fork_tick = 0
    if tm is not None and branch_id in getattr(tm, "branches", {}):
        fork_tick = int(tm.branches[branch_id].fork_tick or 0)

    filtered_items = []
    for it in items:
        if not isinstance(it, dict):
            continue
        item_branch = it.get("branch_id")
        # Never re-insert inherited ancestor rows under a child branch
        if item_branch and str(item_branch) != branch_id:
            continue
        if branch_id != "main" and not item_branch and int(it.get("tick", 0) or 0) < fork_tick:
            continue
        filtered_items.append(it)

    if bool(data.get("replace", False)):
        if bool(data.get("replace_world", False)):
            store.clear_world(world_id=world_id)
        else:
            from_tick = data.get("from_tick")
            store.clear_branch(
                world_id=world_id,
                branch_id=branch_id,
                from_tick=int(from_tick) if from_tick is not None else None,
            )
    saved = store.append_events_batch(filtered_items, world_id=world_id, branch_id=branch_id)
    return jsonify({"ok": True, "count": len(saved), "world_id": world_id, "branch_id": branch_id}), 201


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
