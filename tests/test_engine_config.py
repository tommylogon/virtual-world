"""Tests for the centralized Engine Config (task-304).

Verifies:
  - GET /api/settings/engine_config returns values + schema + section metadata.
  - Saving a value persists it and the engine modules reflect it live.
  - Reset restores the built-in defaults.
  - Unknown/malformed keys are ignored without crashing.
"""
import pytest

from engine import runtime_config
from engine.environment_propagation import _heat_base_rate
from engine.lighting import _spill_factor
from engine.sound import _way_barriers, _speech_levels, _noise_levels

#: Baseline engine values a clean install should see (mirrors DEFAULTS).
BASELINE = {
    "sound.speech_whisper": 0,
    "sound.speech_normal": 1,
    "sound.speech_shout": 2,
    "sound.speech_scream": 3,
    "sound.way_open": 0.5,
    "sound.way_closed": 1,
    "sound.way_locked": 2,
    "sound.way_blocked": 2,
    "sound.way_hidden": 2,
    "sound.way_see_through": 0.75,
    "sound.noise_silent": 0,
    "sound.noise_quiet": 0,
    "sound.noise_normal": 1,
    "sound.noise_loud": 2,
    "sound.noise_chaotic": 2,
    "heat.base_rate": 0.05,
    "heat.max_delta": 2.0,
    "light.spill_factor": 0.5,
}


@pytest.fixture(autouse=True)
def isolated_config(tmp_path):
    """Point the singleton RuntimeConfig at a throwaway file + reset each test."""
    original = runtime_config.config._config_file
    runtime_config.config._config_file = str(tmp_path / "engine_config.json")
    runtime_config.config.reset()
    yield
    runtime_config.config._config_file = original


def _make_client():
    from app import create_app
    app = create_app({"TESTING": True})
    return app.test_client()


def test_get_returns_defaults():
    client = _make_client()
    resp = client.get("/api/settings/engine_config")
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data.keys()) == {"values", "schema", "sections"}
    for key, value in BASELINE.items():
        assert data["values"][key] == value
    # Schema exposure drives a schema-less UI — must exist for every value key
    for key in data["values"]:
        assert key in data["schema"], f"missing schema entry for {key}"
        assert "section" in data["schema"][key]
        assert "label" in data["schema"][key]
    assert set(data["sections"].keys()) >= {"sound", "heat", "light"}


def test_save_persists_and_engine_is_live():
    client = _make_client()
    client.post("/api/settings/engine_config", json={"values": {"heat.base_rate": 0.11}})
    # Re-read: server wrote the file and returned the merged value.
    resp = client.get("/api/settings/engine_config")
    assert resp.get_json()["values"]["heat.base_rate"] == 0.11
    # Engine reads config live — no restart needed.
    assert _heat_base_rate() == 0.11


def test_sound_and_light_reflect_override():
    client = _make_client()
    client.post("/api/settings/engine_config", json={
        "values": {
            "sound.way_open": 0.9,
            "sound.speech_scream": 5,
            "light.spill_factor": 0.25,
        }
    })
    assert _way_barriers()["open"] == 0.9
    assert _speech_levels()["scream"] == 5
    assert _noise_levels()["chaotic"] == 2  # untouched
    assert _spill_factor() == 0.25


def test_reset_restores_defaults():
    client = _make_client()
    client.post("/api/settings/engine_config", json={"values": {"sound.way_locked": 9}})
    resp = client.post("/api/settings/engine_config/reset")
    assert resp.status_code == 200
    assert resp.get_json()["values"]["sound.way_locked"] == BASELINE["sound.way_locked"]


def test_unknown_and_bad_keys_are_ignored():
    client = _make_client()
    resp = client.post("/api/settings/engine_config", json={
        "values": {
            "nonsense.key": 123,
            "sound.way_open": "not-a-number",
            "heat.base_rate": 0.33,
        }
    })
    assert resp.status_code == 200
    values = resp.get_json()["values"]
    assert "nonsense.key" not in values
    # Bad value for a float key is skipped, leaving the previous value.
    assert values["sound.way_open"] == BASELINE["sound.way_open"]
    assert values["heat.base_rate"] == 0.33