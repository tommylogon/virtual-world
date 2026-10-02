"""task-590: library behaviours must reach the engine and actually run.

The Behaviours tab has always written ``data/library/behaviours/*.json`` while
``npc_behaviors`` read only ``player.behaviors``. These tests pin the engine
side: a saved behaviour referenced by a character runs, an unresolvable ref is
reported rather than dropped, and every file in the folder is consumed or named.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from engine import behaviors as behavior_library

ROOT = Path(__file__).resolve().parent.parent

LOOKOUT = {
    "name": "Lookout",
    "trigger": "on_tick",
    "priority": 5,
    "interval": 1,
    "conditions": {},
    "actions": [{"type": "set_npc_state", "state": "foraging"}],
}


def _fresh_app(tmp_path):
    data = str(tmp_path)
    os.makedirs(os.path.join(data, "library", "behaviours"), exist_ok=True)
    os.makedirs(os.path.join(data, "library", "characters"), exist_ok=True)
    app = create_app({"TESTING": True, "DATA_DIR": data})
    return app.test_client(), app, data


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle)


def test_referenced_library_behaviour_runs(tmp_path):
    client, app, data = _fresh_app(tmp_path)
    _write(os.path.join(data, "library", "behaviours", "lookout.json"), LOOKOUT)
    _write(os.path.join(data, "library", "characters", "guard.json"), {
        "name": "Guard",
        "simple_npc": True,
        "current_area": "Kitchen",
        "behaviors": [],
        "behavior_refs": ["lookout"],
    })
    # The default test world already has a Kitchen area.

    resp = client.post("/api/library/import/character/guard", json={"active": False})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    player = app.world.player_manager.players.get("Guard")
    assert player is not None
    assert any(b.get("_library_id") == "lookout" for b in player.behaviors)

    player.current_area = "Kitchen"
    app.world.time_ticks = 1
    app.world.npc_behaviors.process_simple_npcs("on_tick")
    assert player.npc_state == "foraging"


def test_unresolvable_ref_is_reported_not_dropped(tmp_path):
    client, app, data = _fresh_app(tmp_path)
    _write(os.path.join(data, "library", "characters", "ghost.json"), {
        "name": "Ghost",
        "simple_npc": True,
        "behaviors": [],
        "behavior_refs": ["no_such_behaviour"],
    })

    resp = client.post("/api/library/import/character/ghost", json={"active": False})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    warnings = resp.get_json()["behavior_warnings"]
    assert warnings and "no_such_behaviour" in warnings[0]
    player = app.world.player_manager.players.get("Ghost")
    assert player.behaviors == []


def test_every_file_is_consumed_or_reported(tmp_path):
    client, app, data = _fresh_app(tmp_path)
    behaviours = os.path.join(data, "library", "behaviours")
    _write(os.path.join(behaviours, "good.json"), LOOKOUT)
    with open(os.path.join(behaviours, "broken.json"), "w", encoding="utf-8") as handle:
        handle.write("{not json")

    library = behavior_library.load(data, fresh=True)
    assert "good" in library
    problems = dict(behavior_library.problems(data))
    assert "broken.json" in problems


def test_save_from_the_tab_is_picked_up_without_restart(tmp_path):
    client, app, data = _fresh_app(tmp_path)
    resp = client.post("/api/library/behaviours",
                       json={"id": "new_habit", "data": LOOKOUT})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    # _reload_condition_catalog reloaded the catalog on save.
    assert "new_habit" in behavior_library.load(data)


def test_every_shipped_behaviour_file_is_consumed():
    directory = ROOT / "data" / "library" / "behaviours"
    if not directory.is_dir():
        return
    library = behavior_library.load(fresh=True)
    for path in sorted(directory.glob("*.json")):
        assert path.stem in library, f"{path.name} is silently ignored by the engine"
    assert behavior_library.problems() == []
