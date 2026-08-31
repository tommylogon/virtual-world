"""Scenario manager (task-374) + import audit (task-375)."""

import json
import os

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    application = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    application.world._scenario_source = None
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def _seed(app, name):
    scdir = os.path.join(app.config['DATA_DIR'], 'scenarios')
    os.makedirs(scdir, exist_ok=True)
    path = os.path.join(scdir, f"{name}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({"name": name, "areas": {"Alpha": {"description": "x"}},
                   "players": {"Hero": {"name": "Hero"}}}, f)
    return path


def test_list_scenarios(app, client):
    _seed(app, "alpha")
    _seed(app, "beta")
    lst = client.get("/api/scenarios").get_json()
    names = [e["name"] for e in lst]
    assert "alpha" in names and "beta" in names
    alpha = next(e for e in lst if e["name"] == "alpha")
    assert alpha["areas"] == 1 and alpha["players"] == 1


def test_duplicate_scenario(app, client):
    _seed(app, "alpha")
    r = client.post("/api/scenarios/alpha/duplicate")
    assert r.status_code == 200
    assert r.get_json()["name"] == "alpha (copy)"
    assert os.path.exists(os.path.join(app.config['DATA_DIR'], 'scenarios', 'alpha (copy).json'))
    # duplicate of the copy gets a counter
    r2 = client.post("/api/scenarios/alpha (copy)/duplicate")
    assert r2.status_code == 200
    assert "alpha (copy 2)" in r2.get_json()["name"]


def test_rename_scenario(app, client):
    _seed(app, "alpha")
    r = client.post("/api/scenarios/alpha/rename", json={"name": "beta"})
    assert r.status_code == 200
    assert os.path.exists(os.path.join(app.config['DATA_DIR'], 'scenarios', 'beta.json'))
    assert not os.path.exists(os.path.join(app.config['DATA_DIR'], 'scenarios', 'alpha.json'))
    # empty name → 400
    assert client.post("/api/scenarios/beta/rename", json={"name": ""}).status_code == 400
    _seed(app, "gamma")
    assert client.post("/api/scenarios/beta/rename", json={"name": "gamma"}).status_code == 400


def test_delete_scenario(app, client):
    _seed(app, "alpha")
    assert client.delete("/api/scenarios/alpha").status_code == 200
    assert not os.path.exists(os.path.join(app.config['DATA_DIR'], 'scenarios', 'alpha.json'))
    assert client.delete("/api/scenarios/alpha").status_code == 404


def test_scenario_paths_never_escape(app, client):
    _seed(app, "alpha")
    # traversal attempts resolve inside the scenarios dir → 404 (no file)
    for bad in ("..%2F..%2Fsecret", "..\\..\\secret", "%2e%2e%2fsecret"):
        r = client.delete(f"/api/scenarios/{bad}")
        assert r.status_code in (404, 400)
    assert not os.path.exists(os.path.join(app.config['DATA_DIR'], 'secret'))


def test_import_audit_flags_problems(app, client):
    data = {
        "name": "Audit Me",
        "player": {"name": "Hero"},
        "current_area": "Alpha",
        "areas": {
            "Alpha": {"description": "x", "environment": {},
                      "items": [{"name": "Torch", "actions": "examine", "tags": ["light_source"]}]},
        },
    }
    r = client.post("/api/import/audit", json=data)
    assert r.status_code == 200
    body = r.get_json()
    assert body["areas"] == 1
    assert body["items"] == 1
    assert body["count"] > 0
    assert "info" in body["severities"]  # light_source without light_level → info
    assert body["players"] == 1


def test_import_audit_rejects_garbage(app, client):
    assert client.post("/api/import/audit", json={}).status_code == 400
