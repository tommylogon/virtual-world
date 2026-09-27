"""Tests for the /api/soak endpoints (routes/soak.py + routes/soak_ops.py)."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from engine import soak_runner as sr

SMALL = "data/scenarios/combat_pit.json"
# A scenario with a real cast that actually makes background decisions, so the
# action stream is non-empty. Heavier to load, so used only where needed.
CAMP = "data/scenarios/kraktooth_goblin_camp.json"


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


def test_telemetry_endpoint_serves_the_space_time_data():
    """task-543/544: the view is drawn from this endpoint, not from a character's
    lived_log. Events are opt-in (`?events=1`) because they are the unbounded
    half of the store; the default response is the bounded, drawable half."""
    _drain()
    client, _ = _client()
    resp = client.post('/api/soak/runs', json={
        "scenario": CAMP, "ticks": 20, "background_all": True, "telemetry": True,
    })
    run_id = resp.get_json()["run"]["id"]
    _wait_for_finish(client, run_id)

    body = client.get(f"/api/soak/runs/{run_id}/telemetry").get_json()
    assert body["enabled"] is True
    assert body["intervals"]
    assert body["characters"] and body["areas"]
    assert body["integrity_ok"] is True
    assert "events" not in body, "events must be opt-in, not the default payload"

    with_events = client.get(f"/api/soak/runs/{run_id}/telemetry?events=1").get_json()
    assert with_events["events"]

    # The full run is downloadable as JSONL regardless of the hot window.
    download = client.get(f"/api/soak/runs/{run_id}/telemetry.jsonl")
    assert download.status_code == 200
    assert download.mimetype == "application/x-ndjson"
    lines = [json.loads(line) for line in download.data.decode("utf-8").splitlines()
             if line.strip()]
    assert lines, "the JSONL export must not be empty for a run with telemetry"
    # Every line is typed, so a consumer can filter the mixed stream. Presence
    # lines appear when an interval *closes*, so the first line is not
    # necessarily one — a character standing still has an open interval until the
    # run ends.
    kinds = {line["type"] for line in lines}
    assert "presence" in kinds
    assert "action" in kinds

    assert client.get('/api/soak/runs/nope/telemetry').status_code == 404
    assert client.get('/api/soak/runs/nope/telemetry.jsonl').status_code == 404
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
