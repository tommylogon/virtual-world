"""Emotion spike endpoint tests (task-96/350 robustness):
unknown/creative LLM labels must never 400 — they resolve semantically or
no-op gracefully (same contract as /emotions/map)."""

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    return app.test_client()


def _spike(client, name, label, extra=None):
    body = {"emotion": label, "intensity": 5, "delta": 7.5}
    if extra:
        body.update(extra)
    return client.post(f"/api/players/{name}/emotions", json=body)


def test_known_emotion_spikes(client):
    r = _spike(client, "rat", "happy")
    assert r.status_code == 200
    data = r.get_json()
    assert "emotions" in data


def test_unknown_emotion_is_graceful_noop(client):
    r = _spike(client, "rat", "zorbulon_quantum")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("ignored") == "zorbulon_quantum"
    assert "emotions" in data


def test_semantically_mappable_unknown_label_spikes(client):
    # 'relieved' is not a BASELINE but resolves via map_label substring.
    r = _spike(client, "rat", "relieved")
    assert r.status_code == 200
    data = r.get_json()
    assert "ignored" not in data


def test_missing_player_still_404(client):
    r = _spike(client, "Nobody Here", "happy")
    assert r.status_code == 404
