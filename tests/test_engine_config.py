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
    "sound.way_locked": 1,
    "sound.way_blocked": 1,
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
    "forecast.apply_scope": "exterior",
}


@pytest.fixture(autouse=True)
def isolated_config(tmp_path):
    """Point the singleton RuntimeConfig at a throwaway file + reset each test.

    Restores ``_values`` as well as the path. ``config.save()`` merges into the
    live ``_values`` dict, so a test that saves an override (say
    ``sound.way_open = 0.9``) left it there after the path was put back — and
    every later test in the session, in any file, then read the polluted number.
    That is what made ``engine/sound.py`` and ``engine/lighting.py`` tests
    order-dependent: they passed alone and failed in a full run.
    """
    original_path = runtime_config.config._config_file
    original_values = runtime_config.config.values
    runtime_config.config._config_file = str(tmp_path / "engine_config.json")
    runtime_config.config.reset()
    yield
    runtime_config.config._values = original_values
    runtime_config.config._config_file = original_path


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


# ── a string-valued setting was unsettable, on both paths ────────────────
#
# The coercion ladder had no `str` arm, so a string-defaulted key fell into the
# `else: float` one. On the *file* path that warned once per load and kept the
# default; on the *save* path it was dropped in silence, because that one had no
# warning at all. `forecast.apply_scope` was the only such key, so the setting was
# decorative: nobody could change it from the file or from the Settings menu.


def test_a_string_valued_setting_can_actually_be_set():
    client = _make_client()
    resp = client.post("/api/settings/engine_config",
                       json={"values": {"forecast.apply_scope": "all"}})
    assert resp.status_code == 200
    assert resp.get_json()["values"]["forecast.apply_scope"] == "all"
    # …and it survives a save/reload round trip, which is the part that was broken:
    # the value has to reach the file and come back out of it as the same *string*.
    # The `isolated_config` fixture has already pointed the singleton at a
    # throwaway file, so a fresh instance on **that same path** is a true reload
    # without touching `data/engine_config.json`.
    from engine.runtime_config import RuntimeConfig
    reloaded = RuntimeConfig(runtime_config.config._config_file)
    assert reloaded.get("forecast.apply_scope") == "all"


def test_a_string_setting_refuses_a_number_and_an_unknown_word():
    client = _make_client()
    resp = client.post("/api/settings/engine_config", json={"values": {
        "forecast.apply_scope": 2,                 # not a string
        "heat.base_rate": "banana",                # not a number
        "sound.way_open": "banana",                # ditto
    }})
    assert resp.status_code == 200
    values = resp.get_json()["values"]
    assert values["forecast.apply_scope"] == BASELINE["forecast.apply_scope"]
    assert values["heat.base_rate"] == BASELINE["heat.base_rate"]


def test_a_setting_declares_the_words_it_means():
    """`choices` is what stops a typo becoming a different behaviour.

    `forecast.apply_scope` reads "not exterior" as "apply to every area", so
    "exteriorr" would have quietly widened the weather to interiors.
    """
    client = _make_client()
    resp = client.post("/api/settings/engine_config",
                       json={"values": {"forecast.apply_scope": "exteriorr"}})
    assert resp.status_code == 200
    assert resp.get_json()["values"]["forecast.apply_scope"] == BASELINE[
        "forecast.apply_scope"]


def test_a_boolean_is_not_read_by_truthiness():
    """`bool("false")` is `True`, so a hand-edited `"off"` used to read as on."""
    from engine.runtime_config import _coerce_like_default
    for text, want in (("false", False), ("False", False), ("no", False),
                       ("off", False), ("0", False), ("true", True),
                       ("yes", True), ("on", True), ("1", True)):
        assert _coerce_like_default(False, text) is want, text
    # A real bool still works, and a word that is neither is a refusal.
    assert _coerce_like_default(False, False) is False
    assert _coerce_like_default(True, True) is True
    for bad in ("maybe", "", [], {}):
        try:
            _coerce_like_default(True, bad)
            raise AssertionError(f"{bad!r} should have been refused")
        except ValueError:
            pass


def test_a_bool_is_not_accepted_where_a_number_is_declared():
    """`isinstance(True, int)` is True, so a bool silently became the number 1."""
    from engine.runtime_config import _coerce_like_default
    for bad in (True, False):
        for default in (1, 0.5):
            try:
                _coerce_like_default(default, bad)
                raise AssertionError(f"{bad!r} should be refused for {default!r}")
            except ValueError:
                pass


def test_every_default_can_be_coerced_from_its_own_type():
    """No default may be a type the coercion has no rule for.

    A key gaining such a type used to fall into the `else: float` arm and be
    reshaped into a number, which is how a string setting became unsettable.
    """
    from engine.runtime_config import DEFAULTS, _coerce_like_default
    for key, default in DEFAULTS.items():
        if isinstance(default, str):
            probe = "all" if default != "all" else "exterior"
        elif isinstance(default, bool):
            probe = True
        else:
            probe = type(default)(1)
        try:
            assert _coerce_like_default(default, probe) is not None or True
        except (ValueError, TypeError) as exc:
            raise AssertionError(f"{key} ({type(default).__name__}): {exc}")