"""Flask blueprint for Scenario Timeline, Branching, and Decision Redo (task-980)."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from engine.timeline import TimelineManager

timeline_ops_bp = Blueprint("timeline_ops", __name__)


def _get_timeline() -> TimelineManager:
    tm = getattr(current_app, "timeline_manager", None)
    if tm is None:
        tm = TimelineManager()
        current_app.timeline_manager = tm
    return tm


def _snapshot_world() -> dict:
    world = getattr(current_app, "world", None)
    if world is None:
        return {}
    try:
        from engine.serialization import serialize_world
        return serialize_world(world)
    except Exception:
        return {"time_ticks": int(getattr(world, "time_ticks", 0) or 0)}


def _restore_world(snapshot: dict) -> bool:
    world = getattr(current_app, "world", None)
    if world is None or not isinstance(snapshot, dict) or not snapshot:
        return False
    try:
        from engine.serialization import deserialize_world
        deserialize_world(world, snapshot)
        return True
    except Exception:
        return False


@timeline_ops_bp.route("/api/timeline/branches", methods=["GET"])
def list_branches():
    tm = _get_timeline()
    return jsonify({
        "active_branch_id": tm.active_branch_id,
        "branches": tm.list_branches(),
    })


@timeline_ops_bp.route("/api/timeline/checkpoint", methods=["POST"])
def record_checkpoint():
    tm = _get_timeline()
    data = request.get_json(silent=True) or {}
    world = getattr(current_app, "world", None)
    tick = int(data.get("tick", getattr(world, "time_ticks", 0) if world else 0) or 0)
    snap = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else _snapshot_world()
    tm.record_checkpoint(tick, snap, branch_id=data.get("branch_id"))
    return jsonify({"ok": True, "branch_id": tm.active_branch_id, "tick": tick})


@timeline_ops_bp.route("/api/timeline/fork", methods=["POST"])
def fork_branch():
    tm = _get_timeline()
    data = request.get_json(silent=True) or {}
    world = getattr(current_app, "world", None)
    default_tick = int(getattr(world, "time_ticks", 0) or 0) if world else 0
    fork_tick = int(data.get("fork_tick", default_tick) or 0)
    snap = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else None
    if snap is None and fork_tick == default_tick:
        snap = _snapshot_world()
    branch = tm.fork_branch(
        label=str(data.get("label") or ""),
        from_branch_id=data.get("from_branch_id"),
        fork_tick=fork_tick,
        fork_seq=data.get("fork_seq"),
        fork_datetime=str(data.get("fork_datetime") or ""),
        snapshot=snap,
        switch=bool(data.get("switch", True)),
    )
    return jsonify({"ok": True, "active_branch_id": tm.active_branch_id, "branch": branch.to_summary()}), 201


@timeline_ops_bp.route("/api/timeline/switch", methods=["POST"])
def switch_branch():
    tm = _get_timeline()
    data = request.get_json(silent=True) or {}
    branch_id = str(data.get("branch_id") or "").strip()
    if not branch_id:
        return jsonify({"error": "branch_id is required"}), 400
    try:
        branch = tm.switch_branch(branch_id)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    restored = _restore_world(branch.snapshot) if (bool(data.get("restore", True)) and branch.snapshot) else False
    return jsonify({
        "ok": True,
        "active_branch_id": tm.active_branch_id,
        "branch": branch.to_summary(),
        "restored": restored,
    })


@timeline_ops_bp.route("/api/timeline/redo", methods=["POST"])
def redo_decision():
    """Fork a clean sibling branch right before a character's decision so it can be redone."""
    tm = _get_timeline()
    data = request.get_json(silent=True) or {}
    character = str(data.get("character") or "").strip()
    if not character:
        return jsonify({"error": "character is required"}), 400
    at_tick = int(data.get("at_tick", 0) or 0)
    at_seq = data.get("at_seq")
    res = tm.redo_decision(
        character=character,
        at_tick=at_tick,
        at_seq=int(at_seq) if at_seq is not None else None,
        label=str(data.get("label") or ""),
        from_branch_id=data.get("from_branch_id"),
    )
    restored = _restore_world(res["restore_snapshot"]) if res.get("restore_snapshot") else False
    return jsonify({
        "ok": True,
        "active_branch_id": tm.active_branch_id,
        "branch": res["branch"],
        "character": character,
        "fork_seq": res["fork_seq"],
        "restored": restored,
    }), 201
