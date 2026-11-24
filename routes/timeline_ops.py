"""Flask blueprint for Scenario Timeline, Branching, and Decision Redo (task-980)."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from engine.timeline import (
    TimelineManager,
    record_world_checkpoint,
    restore_from_timeline,
    snapshot_for_timeline,
)

timeline_ops_bp = Blueprint("timeline_ops", __name__)


def _get_timeline() -> TimelineManager:
    world = getattr(current_app, "world", None)
    if world is not None:
        tm = getattr(world, "timeline_manager", None)
        if tm is None:
            tm = TimelineManager()
            world.timeline_manager = tm
        main_b = tm.branches.get("main")
        if main_b is not None and not main_b.checkpoints and main_b.snapshot is None:
            snap = snapshot_for_timeline(world)
            if snap:
                tm.record_checkpoint(int(getattr(world, "time_ticks", 0) or 0), snap, branch_id="main")
        current_app.timeline_manager = tm
        return tm
    tm = getattr(current_app, "timeline_manager", None)
    if tm is None:
        tm = TimelineManager()
        current_app.timeline_manager = tm
    return tm


def _clear_agent_caches() -> None:
    current_app._agent_memory_manager = None
    current_app._agent_plan_manager = None


def _snapshot_world() -> dict:
    world = getattr(current_app, "world", None)
    if world is None:
        return {}
    snap = snapshot_for_timeline(world)
    if snap:
        return snap
    return {"time_ticks": int(getattr(world, "time_ticks", 0) or 0)}


def _restore_world(snapshot: dict) -> bool:
    world = getattr(current_app, "world", None)
    if world is None or not isinstance(snapshot, dict) or not snapshot:
        return False
    ok = restore_from_timeline(world, snapshot)
    if ok:
        _clear_agent_caches()
        try:
            data_dir = current_app.config.get("DATA_DIR")
            if data_dir:
                from engine.world.store import configure_scope_store
                configure_scope_store(world, data_dir)
        except Exception:
            pass
    return ok


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
    # Save current outgoing branch head before forking/switching
    if world is not None:
        cur_snap = _snapshot_world()
        if cur_snap:
            tm.record_checkpoint(default_tick, cur_snap, branch_id=tm.active_branch_id)
    snap = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else None
    if snap is None and fork_tick == default_tick:
        snap = _snapshot_world()
    do_switch = bool(data.get("switch", True))
    branch = tm.fork_branch(
        label=str(data.get("label") or ""),
        from_branch_id=data.get("from_branch_id"),
        fork_tick=fork_tick,
        fork_seq=data.get("fork_seq"),
        fork_datetime=str(data.get("fork_datetime") or ""),
        snapshot=snap,
        switch=do_switch,
    )
    restored = False
    if do_switch and fork_tick != default_tick and branch.snapshot:
        restored = _restore_world(branch.snapshot)
    elif do_switch:
        _clear_agent_caches()
    cur_tick = int(getattr(world, "time_ticks", 0) or 0) if world else fork_tick
    return jsonify({
        "ok": True,
        "active_branch_id": tm.active_branch_id,
        "branch": branch.to_summary(),
        "tick": cur_tick,
        "restored": restored,
        "ancestry": tm.get_ancestry(tm.active_branch_id),
    }), 201


@timeline_ops_bp.route("/api/timeline/switch", methods=["POST"])
def switch_branch():
    tm = _get_timeline()
    data = request.get_json(silent=True) or {}
    branch_id = str(data.get("branch_id") or "").strip()
    if not branch_id:
        return jsonify({"error": "branch_id is required"}), 400
    if branch_id not in tm.branches:
        return jsonify({"error": f"Unknown branch: {branch_id}"}), 404
    world = getattr(current_app, "world", None)
    if world is not None and branch_id != tm.active_branch_id:
        cur_snap = _snapshot_world()
        if cur_snap:
            tm.active_branch.snapshot = cur_snap
            tm.active_branch.checkpoints[int(getattr(world, "time_ticks", 0) or 0)] = cur_snap
    branch = tm.switch_branch(branch_id)
    restored = _restore_world(branch.snapshot) if (bool(data.get("restore", True)) and branch.snapshot) else False
    cur_tick = int(getattr(world, "time_ticks", 0) or 0) if world else branch.fork_tick
    return jsonify({
        "ok": True,
        "active_branch_id": tm.active_branch_id,
        "branch": branch.to_summary(),
        "tick": cur_tick,
        "restored": restored,
        "ancestry": tm.get_ancestry(tm.active_branch_id),
    })


@timeline_ops_bp.route("/api/timeline/redo", methods=["POST"])
def redo_decision():
    """Fork a clean sibling branch right before a character's decision so it can be redone."""
    tm = _get_timeline()
    data = request.get_json(silent=True) or {}
    character = str(data.get("character") or "").strip()
    if not character:
        return jsonify({"error": "character is required"}), 400
    world = getattr(current_app, "world", None)
    if world is not None:
        cur_snap = _snapshot_world()
        if cur_snap:
            tm.active_branch.snapshot = cur_snap
            tm.active_branch.checkpoints[int(getattr(world, "time_ticks", 0) or 0)] = cur_snap
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
    cur_tick = int(getattr(world, "time_ticks", 0) or 0) if world else at_tick
    return jsonify({
        "ok": True,
        "active_branch_id": tm.active_branch_id,
        "branch": res["branch"],
        "character": character,
        "fork_seq": res["fork_seq"],
        "tick": cur_tick,
        "restored": restored,
        "ancestry": tm.get_ancestry(tm.active_branch_id),
    }), 201
