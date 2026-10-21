"""Tests for task-885: Play Mode vs Edit Mode (transient simulation sandbox).

Verifies:
1. Entering Play Mode takes an in-memory snapshot and updates status.
2. Actions and mutations advance the live world during Play Mode.
3. Autosave is diverted to sandbox_autosave.json and does not clobber data/autosave.json.
4. Stopping Play Mode restores the pre-play checkpoint and resets live state.
5. Scenario commit is blocked while in Play Mode.
6. Save and load game flow operates seamlessly in Play Mode.
"""

import json
import os
import pytest
from app import create_app
from routes.helpers import AUTOSAVE_PATH, SANDBOX_AUTOSAVE_PATH, save_autosave


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with isolated temp data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)

    app = create_app({"TESTING": True, "DATA_DIR": str(data_dir)})

    # Route autosave paths to tmp
    test_autosave = str(data_dir / "autosave.json")
    test_sandbox_autosave = str(data_dir / "sandbox_autosave.json")
    monkeypatch.setattr("routes.helpers.AUTOSAVE_PATH", test_autosave)
    monkeypatch.setattr("routes.helpers.SANDBOX_AUTOSAVE_PATH", test_sandbox_autosave)
    monkeypatch.setattr("routes.helpers.SAVES_DIR", str(saves_dir))
    monkeypatch.setattr("routes.saveload.SAVES_DIR", str(saves_dir))

    with app.test_client() as c:
        yield c, app


def test_play_mode_enter_and_status(client):
    c, app = client

    # Initially in Edit Mode
    res = c.get("/api/play_mode/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["play_mode"] is False
    assert data["has_snapshot"] is False

    # Enter Play Mode
    res = c.post("/api/play_mode/enter")
    assert res.status_code == 200
    assert res.get_json()["play_mode"] is True

    # Status reflects Play Mode
    res = c.get("/api/play_mode/status")
    data = res.get_json()
    assert data["play_mode"] is True
    assert data["has_snapshot"] is True

    # /api/state reports is_play_mode
    res = c.get("/api/state")
    assert res.status_code == 200
    state = res.get_json()
    assert state.get("is_play_mode") is True

    # /api/scenario/status reports play_mode
    res = c.get("/api/scenario/status")
    assert res.status_code == 200
    status_data = res.get_json()
    assert status_data.get("play_mode") is True
    assert status_data.get("dirty") is False


def test_play_mode_isolation_and_revert_on_stop(client):
    c, app = client

    # Set up initial authored state
    node = list(app.world.graph.nodes.values())[0]
    orig_name = node.name
    orig_ticks = app.world.time_ticks

    # Enter Play Mode
    res = c.post("/api/play_mode/enter")
    assert res.status_code == 200

    # Advance world simulation ticks and mutate a node
    app.world.time_ticks += 42
    node.name = "mutated_in_sandbox"
    assert node.name == "mutated_in_sandbox"
    assert app.world.time_ticks == orig_ticks + 42

    # Stop Play Mode via /api/play_mode/stop
    res = c.post("/api/play_mode/stop")
    assert res.status_code == 200
    assert res.get_json()["play_mode"] is False

    # Live world restored to pre-play baseline
    assert app.world.time_ticks == orig_ticks
    restored_node = app.world.graph.get_node(node.id)
    assert restored_node.name == orig_name

    # Status is back to Edit Mode
    res = c.get("/api/play_mode/status")
    data = res.get_json()
    assert data["play_mode"] is False
    assert data["has_snapshot"] is False


def test_loading_scenario_while_playing_discards_old_checkpoint(client):
    c, app = client
    payload = app.world.to_dict()
    payload["_scenario_name"] = "replacement"
    payload["persist"] = False
    payload["players"] = {}
    payload["graph"] = {
        "nodes": {
            "area_replacement": {
                "id": "area_replacement",
                "name": "Replacement Room",
                "type": "area",
                "properties": {},
            }
        },
        "edges": [],
    }

    assert c.post("/api/play_mode/enter").get_json()["play_mode"] is True
    app.world.time_ticks += 42

    loaded = c.post("/api/load", json=payload)
    assert loaded.status_code == 200
    assert app.world.graph.get_node("area_replacement") is not None
    assert app.play_mode is False
    assert app._play_mode_snapshot is None

    stopped = c.post("/api/play_mode/stop")
    assert stopped.status_code == 200
    assert app.world.graph.get_node("area_replacement") is not None
    assert c.get("/api/play_mode/status").get_json() == {
        "play_mode": False,
        "has_snapshot": False,
    }


def test_play_mode_blocks_scenario_commit(client):
    c, app = client

    # Enter Play Mode
    c.post("/api/play_mode/enter")

    # Attempt commit
    res = c.post("/api/scenario/commit", json={})
    assert res.status_code == 400
    assert "Cannot commit scenario while in Play Mode" in res.get_json()["error"]


def test_play_mode_autosave_diverts_to_sandbox(client):
    c, app = client
    from routes.helpers import AUTOSAVE_PATH, SANDBOX_AUTOSAVE_PATH

    # Write initial authored autosave
    app.world.is_play_mode = False
    save_autosave(app.world)
    assert os.path.exists(AUTOSAVE_PATH)
    with open(AUTOSAVE_PATH, "r", encoding="utf-8") as f:
        orig_data = json.load(f)

    # Enter Play Mode
    c.post("/api/play_mode/enter")
    assert app.world.is_play_mode is True

    # Mutate and autosave
    app.world.time_ticks += 100
    save_autosave(app.world)

    # Primary autosave file is untouched
    with open(AUTOSAVE_PATH, "r", encoding="utf-8") as f:
        check_data = json.load(f)
    assert check_data["_autosave_meta"]["tick"] == orig_data["_autosave_meta"]["tick"]

    # Sandbox autosave contains the simulation state
    assert os.path.exists(SANDBOX_AUTOSAVE_PATH)
    with open(SANDBOX_AUTOSAVE_PATH, "r", encoding="utf-8") as f:
        sandbox_data = json.load(f)
    assert sandbox_data["_autosave_meta"]["tick"] == orig_data["_autosave_meta"]["tick"] + 100
    assert sandbox_data["_autosave_meta"]["is_play_mode"] is True


def test_play_mode_save_and_load_game_flow(client):
    c, app = client

    # Initial state
    orig_ticks = app.world.time_ticks

    # Enter Play Mode
    c.post("/api/play_mode/enter")

    # Advance simulation and save game
    app.world.time_ticks += 15
    save_res = c.post("/api/save-game", json={"name": "playtest_save"})
    assert save_res.status_code == 201
    filename = save_res.get_json()["filename"]

    # Advance further
    app.world.time_ticks += 30
    assert app.world.time_ticks == orig_ticks + 45

    # Load the savegame back while in Play Mode
    load_res = c.post(f"/api/load-game/{filename}")
    assert load_res.status_code == 200
    assert app.world.time_ticks == orig_ticks + 15
    assert getattr(app, "play_mode", False) is True
    assert getattr(app.world, "is_play_mode", False) is True

    # Stop Play Mode - should revert to original pre-play baseline
    stop_res = c.post("/api/saveload/restore_snapshot")
    assert stop_res.status_code == 200
    assert app.world.time_ticks == orig_ticks
    assert getattr(app, "play_mode", False) is False


def test_edit_mode_retains_normal_dirty_and_autosave(client):
    c, app = client
    from routes.helpers import AUTOSAVE_PATH

    # In Edit Mode
    res = c.get("/api/play_mode/status")
    assert res.get_json()["play_mode"] is False

    # Calling save_autosave in Edit Mode writes to AUTOSAVE_PATH
    app.world.time_ticks = 77
    save_autosave(app.world)
    assert os.path.exists(AUTOSAVE_PATH)
    with open(AUTOSAVE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["_autosave_meta"]["tick"] == 77
    assert data["_autosave_meta"].get("is_play_mode") is False

    # Mutating a node in edit mode bumps edit sequence
    app.config["TESTING"] = False
    init_seq = getattr(app.world, "_edit_seq", 0)
    node_id = list(app.world.graph.nodes.keys())[0]
    c.patch(f"/api/graph/node/{node_id}", json={"properties": {"test_prop": "val"}})
    assert getattr(app.world, "_edit_seq", 0) > init_seq
    status_res = c.get("/api/scenario/status")
    assert status_res.get_json()["dirty"] is True
