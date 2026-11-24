"""Tests for Scenario Timeline, Branching, and Decision Redo (task-980)."""
from __future__ import annotations

from flask import Flask

from engine.timeline import TimelineManager
from routes.timeline_ops import timeline_ops_bp


def test_timeline_fork_isolation_and_decision_redo():
    tm = TimelineManager()
    tm.record_checkpoint(0, {"time_ticks": 0, "players": {"elena": {"area": "foyer"}}})
    tm.record_checkpoint(3, {"time_ticks": 3, "players": {"elena": {"area": "library"}}})

    # Redo Elena's decision at tick 0 (seq 12)
    res = tm.redo_decision(character="elena", at_tick=0, at_seq=12)
    redo_id = res["branch"]["branch_id"]
    assert tm.active_branch_id == redo_id
    assert res["fork_seq"] == 11
    assert res["restore_snapshot"]["players"]["elena"]["area"] == "foyer"

    # Mutate the redo branch; main must remain untouched
    tm.record_checkpoint(1, {"time_ticks": 1, "players": {"elena": {"area": "garden"}}})
    main_branch = tm.switch_branch("main")
    assert main_branch.snapshot["players"]["elena"]["area"] == "library"
    assert tm.branches[redo_id].snapshot["players"]["elena"]["area"] == "garden"

    # Serialize / load round-trip
    raw = tm.serialize()
    tm2 = TimelineManager()
    tm2.load(raw)
    assert tm2.active_branch_id == "main"
    assert set(tm2.branches.keys()) == {"main", redo_id}
    assert tm2.branches[redo_id].checkpoints[1]["players"]["elena"]["area"] == "garden"


def test_timeline_ops_routes():
    app = Flask(__name__)
    app.timeline_manager = TimelineManager()
    app.register_blueprint(timeline_ops_bp)
    client = app.test_client()

    r_cp = client.post("/api/timeline/checkpoint", json={"tick": 0, "snapshot": {"time_ticks": 0, "note": "start"}})
    assert r_cp.status_code == 200

    r_redo = client.post("/api/timeline/redo", json={"character": "miki", "at_tick": 0, "at_seq": 5, "label": "Try whispering instead"})
    assert r_redo.status_code == 201
    body = r_redo.get_json()
    assert body["character"] == "miki"
    assert body["fork_seq"] == 4
    new_bid = body["branch"]["branch_id"]

    r_list = client.get("/api/timeline/branches")
    assert r_list.status_code == 200
    assert r_list.get_json()["active_branch_id"] == new_bid
    assert len(r_list.get_json()["branches"]) == 2

    r_sw = client.post("/api/timeline/switch", json={"branch_id": "main", "restore": False})
    assert r_sw.status_code == 200
    assert r_sw.get_json()["active_branch_id"] == "main"
