"""Naming the live scenario (the top-bar chip, task-408 follow-up).

The name is not cosmetic: it decides where a COMMIT writes. A world booted from
a shared source (the boot template) would otherwise commit straight back into
that file — which is how a camp edit could overwrite `world_template.json`.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


def _client(tmp_path):
    data_dir = tmp_path / "data"
    (data_dir / "scenarios").mkdir(parents=True, exist_ok=True)
    app = create_app({"TESTING": True, "DATA_DIR": str(data_dir)})
    return app.test_client(), app, data_dir


def test_naming_sets_the_world_name(tmp_path):
    client, app, _data_dir = _client(tmp_path)
    resp = client.post('/api/scenario/name', json={"name": "kraktooth_goblin_camp"})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["name"] == "kraktooth_goblin_camp"
    assert app.world._scenario_name == "kraktooth_goblin_camp"


def test_naming_repoints_the_save_target(tmp_path):
    client, app, data_dir = _client(tmp_path)
    client.post('/api/scenario/name', json={"name": "My Camp"})
    source = getattr(app.world, "_scenario_source", None)
    assert source, "expected a save target"
    assert Path(source).name == "My Camp.json"
    assert Path(source).parent == data_dir / "scenarios"


def test_unsafe_characters_are_sanitised(tmp_path):
    client, app, _data_dir = _client(tmp_path)
    resp = client.post('/api/scenario/name', json={"name": "camp/../etc:passwd"})
    assert resp.status_code == 200
    name = resp.get_json()["name"]
    assert "/" not in name and ":" not in name and ".." not in name
    assert Path(app.world._scenario_source).name == f"{name}.json"


def test_existing_target_is_never_clobbered(tmp_path):
    client, app, data_dir = _client(tmp_path)
    existing = data_dir / "scenarios" / "taken.json"
    existing.write_text(json.dumps({"graph": {"nodes": {}, "edges": []}}), encoding="utf-8")
    before = existing.read_text(encoding="utf-8")

    resp = client.post('/api/scenario/name', json={"name": "taken"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body.get("warning"), "expected a warning about the existing file"
    # The file is untouched and the save target did not move onto it.
    assert existing.read_text(encoding="utf-8") == before
    assert getattr(app.world, "_scenario_source", None) != str(existing)


def test_source_path_supplies_a_missing_name(tmp_path):
    """A blank name is the failure mode that made saves land as "unnamed" and
    left the frontend's background-map cache unreachable."""
    world = create_app({"TESTING": True}).world
    world._scenario_name = ""
    world.set_scenario_source(str(tmp_path / "kraktooth_goblin_camp.json"))
    assert world._scenario_name == "kraktooth_goblin_camp"


def test_an_existing_name_beats_the_filename(tmp_path):
    world = create_app({"TESTING": True}).world
    world._scenario_name = "violet_parr_scenario"
    world.set_scenario_source(str(tmp_path / "something_else.json"))
    assert world._scenario_name == "violet_parr_scenario"


def test_clearing_the_source_leaves_the_name_alone(tmp_path):
    world = create_app({"TESTING": True}).world
    world.set_scenario_source(str(tmp_path / "named_world.json"))
    world.set_scenario_source(None)
    assert world._scenario_source is None
    assert world._scenario_name == "named_world"


def test_missing_name_is_rejected(tmp_path):
    client, _app, _data_dir = _client(tmp_path)
    assert client.post('/api/scenario/name', json={}).status_code == 400
    assert client.post('/api/scenario/name', json={"name": "   "}).status_code == 400
