"""Flask blueprint for Scenario Timeline, Branching, and Decision Redo (task-980)."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from engine.timeline import (
    TimelineManager,
    connect_branches,
    expand_timeline_earlier,
    record_world_checkpoint,
    restore_from_timeline,
    snapshot_for_timeline,
)
from engine.timeline_store import TimelineStore

timeline_ops_bp = Blueprint("timeline_ops", __name__)


def _active_world_id() -> str:
    world = getattr(current_app, "world", None)
    wid = (
        getattr(world, "_scenario_name", None)
        or getattr(world, "world_name", None)
        or getattr(world, "name", None)
        or "default"
    )
    return str(wid).strip() or "default"


def _get_timeline_store() -> TimelineStore:
    store = getattr(current_app, "timeline_store", None)
    if store is None:
        db_path = ":memory:" if current_app.config.get("TESTING") else "saves/timeline.db"
        store = TimelineStore(db_path=db_path)
        current_app.timeline_store = store
    return store


def _get_timeline() -> TimelineManager:
    world = getattr(current_app, "world", None)
    store = _get_timeline_store()
    wid = _active_world_id()
    if world is not None:
        tm = getattr(world, "timeline_manager", None)
        if tm is None:
            tm = TimelineManager()
            world.timeline_manager = tm
        if getattr(tm, "_store", None) is not store or getattr(tm, "_world_id", None) != wid:
            tm.attach_store(store, wid, hydrate=(len(tm.branches) <= 1 and not tm.branches["main"].checkpoints))
        main_b = tm.branches.get("main")
        if main_b is not None and not main_b.checkpoints and main_b.snapshot is None:
            snap = snapshot_for_timeline(world)
            if snap:
                tm.record_checkpoint(int(getattr(world, "time_ticks", 0) or 0), snap, branch_id="main")
        current_app.timeline_manager = tm
        return tm
    tm = getattr(current_app, "timeline_manager", None)
    if tm is None:
        tm = TimelineManager(store=store, world_id=wid)
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


@timeline_ops_bp.route("/api/timeline/expand-past", methods=["POST"])
def expand_past():
    """Shift calendar start earlier and offset existing ticks so prequel play opens before old Tick 0."""
    _get_timeline()
    world = getattr(current_app, "world", None)
    if world is None:
        return jsonify({"error": "No active world"}), 400
    data = request.get_json(silent=True) or {}
    delta_days = data.get("delta_days")
    if delta_days is None and data.get("months") is not None:
        cfg = getattr(world, "calendar_config", None) or {}
        dpm = max(1, int(cfg.get("days_per_month", 30) or 30))
        delta_days = int(data["months"]) * dpm
    if delta_days is None or int(delta_days) <= 0:
        return jsonify({"error": "delta_days (positive integer) or months is required"}), 400
    stream_store = getattr(current_app, "stream_store", None)
    res = expand_timeline_earlier(
        world,
        int(delta_days),
        stream_store=stream_store,
        world_id=_active_world_id(),
    )
    _clear_agent_caches()
    return jsonify(res)


@timeline_ops_bp.route("/api/timeline/connect", methods=["POST"])
def connect_timeline_branches():
    """Propagate prequel outcomes from source_branch_id onto target_branch_id into a new branch."""
    tm = _get_timeline()
    world = getattr(current_app, "world", None)
    if world is None:
        return jsonify({"error": "No active world"}), 400
    data = request.get_json(silent=True) or {}
    source_id = str(data.get("source_branch_id") or "").strip()
    target_id = str(data.get("target_branch_id") or "").strip()
    if not source_id or not target_id:
        return jsonify({"error": "source_branch_id and target_branch_id are required"}), 400
    # Ensure active branch head is saved before reading snapshots
    cur_snap = _snapshot_world()
    if cur_snap:
        tm.record_checkpoint(int(getattr(world, "time_ticks", 0) or 0), cur_snap, branch_id=tm.active_branch_id)
    try:
        res = connect_branches(world, source_id, target_id, label=str(data.get("label") or ""))
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    _clear_agent_caches()
    return jsonify(res), 201


@timeline_ops_bp.route("/api/timeline/fork-soak", methods=["POST"])
def fork_and_soak():
    """Fork a new isolated branch and run headless multi-day simulation directly into it (task-1012)."""
    from engine import timeskip

    tm = _get_timeline()
    world = getattr(current_app, "world", None)
    if world is None:
        return jsonify({"error": "No active world"}), 400
    data = request.get_json(silent=True) or {}
    default_tick = int(getattr(world, "time_ticks", 0) or 0)
    fork_tick = int(data.get("fork_tick", default_tick) or 0)

    total_minutes = data.get("minutes")
    if total_minutes is None and data.get("days") is not None:
        total_minutes = float(data["days"]) * 1440.0
    elif total_minutes is None and data.get("hours") is not None:
        total_minutes = float(data["hours"]) * 60.0
    if total_minutes is None:
        total_minutes = 1440.0  # default 1 day
    total_minutes = max(1, min(int(round(float(total_minutes))), int(timeskip.MAX_MINUTES) * 4))
    chunk_minutes = max(1, min(int(data.get("checkpoint_every_minutes") or 1440), total_minutes, 1440))

    # Save outgoing branch head before forking
    cur_snap = _snapshot_world()
    if cur_snap:
        tm.record_checkpoint(default_tick, cur_snap, branch_id=tm.active_branch_id)

    label = str(data.get("label") or f"Soak {total_minutes // 60}h @ Tick {fork_tick}").strip()
    branch = tm.fork_branch(
        label=label,
        from_branch_id=data.get("from_branch_id"),
        fork_tick=fork_tick,
        switch=True,
    )
    if fork_tick != default_tick and branch.snapshot:
        _restore_world(branch.snapshot)

    stream_store = getattr(current_app, "stream_store", None)
    wid = _active_world_id()
    remaining = total_minutes
    ticks_advanced = 0
    elapsed_minutes = 0
    checkpoints_recorded = 0
    summary_lines = []

    while remaining > 0:
        step_min = min(chunk_minutes, remaining)
        outcome = timeskip.advance_world(world, step_min)
        remaining -= step_min
        ticks_advanced += int(getattr(outcome, "ticks", 0) or 0)
        elapsed_minutes += int(getattr(outcome, "elapsed_minutes", step_min) or step_min)
        if outcome.lines:
            summary_lines.extend(outcome.lines[-6:])
        cur_tick = int(getattr(world, "time_ticks", 0) or 0)
        record_world_checkpoint(world, tick=cur_tick)
        checkpoints_recorded += 1
        if stream_store is not None:
            cal_lbl = world.calendar_label_for_tick(cur_tick) if hasattr(world, "calendar_label_for_tick") else f"Tick {cur_tick}"
            stream_store.append_event(
                world_id=wid,
                branch_id=tm.active_branch_id,
                kind="system",
                actor="World",
                tick=cur_tick,
                game_time=world.get_current_time() if hasattr(world, "get_current_time") else "",
                payload={
                    "type": "system",
                    "actor": "World",
                    "tick": cur_tick,
                    "text": f"[Soak checkpoint · {cal_lbl}] +{step_min}m ({len(outcome.lines or [])} notable events)",
                },
            )
        if not outcome.ok:
            break

    _clear_agent_caches()
    return jsonify({
        "ok": True,
        "active_branch_id": tm.active_branch_id,
        "branch": tm.active_branch.to_summary(),
        "tick": int(getattr(world, "time_ticks", 0) or 0),
        "ticks_advanced": ticks_advanced,
        "elapsed_minutes": elapsed_minutes,
        "checkpoints_recorded": checkpoints_recorded,
        "lines": summary_lines[-30:],
    }), 201
