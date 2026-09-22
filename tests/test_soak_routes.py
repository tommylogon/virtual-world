"""Tests for the /api/soak endpoints (routes/soak.py + routes/soak_ops.py)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from engine import soak_runner as sr

SMALL = "data/scenarios/combat_pit.json"


def _client():
    app = create_app({'TESTING': True})
    return app.test_client(), app


def _drain():
    for run in list(sr._RUNS.values()):
        run.cancel()
    deadline = time.time() + 20
    while sr.active_run() and time.time() < deadline:
        time.sleep(0.02)
    for rid in list(sr._RUNS.keys()):
        try:
            sr.remove_run(rid)
        except RuntimeError:
            pass


def _wait_for_finish(client, run_id, timeout=60):
    deadline = time.time() + timeout
    body = None
    while time.time() < deadline:
        resp = client.get(f"/api/soak/runs/{run_id}")
        assert resp.status_code == 200
        body = resp.get_json()
        if body["finished"]:
            return body
        time.sleep(0.02)
    raise AssertionError(f"run did not finish: {body}")


def test_meta_lists_scenarios_and_defaults():
    client, _ = _client()
    body = client.get('/api/soak/meta').get_json()
    assert body["defaults"]["ticks"] == 10080
    assert body["active_run_id"] is None
    assert any(s["path"] == SMALL for s in body["scenarios"])
    assert "Hunger" in body["core_vitals"]
    assert body["limits"]["max_ticks"] >= 1


def test_start_poll_report_export_and_delete():
    _drain()
    client, _ = _client()
    resp = client.post('/api/soak/runs', json={
        "scenario": SMALL, "ticks": 12, "sample_every": 4,
        "label": "unit test run",
    })
    assert resp.status_code == 201
    run_id = resp.get_json()["run"]["id"]
    assert resp.get_json()["run"]["label"] == "unit test run"

    body = _wait_for_finish(client, run_id)
    assert body["run"]["status"] == "finished"
    assert body["samples"] and body["samples"][0]["tick"] == 4

    # Incremental polling: since swallows already-seen samples.
    full = client.get(f"/api/soak/runs/{run_id}").get_json()
    tail = client.get(f"/api/soak/runs/{run_id}?since={full['next_since']}").get_json()
    assert tail["samples"] == []

    report = client.get(f"/api/soak/runs/{run_id}/report")
    assert report.status_code == 200
    assert report.get_json()["summary"]["ticks_completed"] == 12

    download = client.get(f"/api/soak/runs/{run_id}/report?download=1")
    assert download.status_code == 200
    assert "attachment" in download.headers.get("Content-Disposition", "")

    for kind in ("samples", "deaths", "characters", "growth"):
        csv = client.get(f"/api/soak/runs/{run_id}/export?kind={kind}")
        assert csv.status_code == 200
        assert csv.mimetype == "text/csv"
        assert len(csv.data) > 0

    chars = client.get(f"/api/soak/runs/{run_id}/characters").get_json()["characters"]
    assert chars and chars[0]["name"]
    name = chars[0]["name"]
    series = client.get(f"/api/soak/runs/{run_id}/characters/{name}/series").get_json()
    assert series["name"] == name and series["ticks"]

    removed = client.delete(f"/api/soak/runs/{run_id}")
    assert removed.status_code == 200
    assert client.get(f"/api/soak/runs/{run_id}").status_code == 404
    _drain()


def test_validation_and_conflicts():
    _drain()
    client, _ = _client()
    assert client.post('/api/soak/runs', json={"scenario": SMALL, "ticks": 0}).status_code == 400
    assert client.post('/api/soak/runs', json={"scenario": SMALL, "ticks": 10 ** 9}).status_code == 400
    assert client.post('/api/soak/runs', json={"scenario": "../etc/passwd"}).status_code == 400
    assert client.post('/api/soak/runs', json={"scenario": SMALL,
                                               "decay_overrides": "oops"}).status_code == 400
    assert client.get('/api/soak/runs/nope').status_code == 404
    assert client.post('/api/soak/runs/nope/stop').status_code == 404

    first = client.post('/api/soak/runs', json={"scenario": SMALL, "ticks": 200000})
    assert first.status_code == 201
    run_id = first.get_json()["run"]["id"]
    conflict = client.post('/api/soak/runs', json={"scenario": SMALL, "ticks": 5})
    assert conflict.status_code == 409
    assert client.delete(f'/api/soak/runs/{run_id}').status_code == 409
    client.post(f'/api/soak/runs/{run_id}/stop')
    _wait_for_finish(client, run_id)
    assert client.delete(f'/api/soak/runs/{run_id}').status_code == 200
    _drain()


def test_soak_page_served():
    client, _ = _client()
    resp = client.get('/soak')
    assert resp.status_code == 200
    assert b'soak' in resp.data.lower()
