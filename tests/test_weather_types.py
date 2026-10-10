"""Tests for the weather-type registry (task-772).

The vocabulary is library data now: `data/library/weather/*.json` is the source,
and `engine/weather_types` derives the tables the engine and UI read. These
tests pin that the registry loads, that the hardcoded tables are only a
fallback, and that a new record is picked up without a code change.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import weather_types

_REAL_DIR = weather_types.REGISTRY_DIR
_CANONICAL = ["clear", "cloudy", "windy", "rainy", "stormy", "foggy", "snowy"]
# The shipped registry adds the four extreme types (task-763); the fallback (used
# when the registry directory is absent) stays the original seven.
_REGISTRY = _CANONICAL + ["blizzard", "thunderstorm", "heatwave", "cold_snap"]


@pytest.fixture(autouse=True)
def _restore_registry():
    """Always put the real registry back, whatever a test monkeypatched."""
    yield
    weather_types.REGISTRY_DIR = _REAL_DIR
    weather_types.reload()


def test_registry_loads_in_canonical_order():
    assert weather_types.WEATHER_STATES == _REGISTRY
    assert weather_types.WEATHER_TIME_DC["stormy"] == 20
    assert weather_types.WEATHER_TIME_DC["clear"] == 10
    assert weather_types.WEATHER_LIGHT_MULT["stormy"] == 0.3
    assert weather_types.WEATHER_PROSE["snowy"].startswith("Snow is falling")
    # clear and windy say nothing (narrated elsewhere / not at all)
    assert weather_types.WEATHER_PROSE["clear"] == ""
    assert weather_types.WEATHER_PROSE["windy"] == ""


def test_normalize_reads_the_registry():
    assert weather_types.normalize_weather("rain") == "rainy"
    assert weather_types.normalize_weather("OVERCAST") == "cloudy"
    assert weather_types.normalize_weather("meteor shower") == ""
    assert weather_types.weather_light_mult("storm") == 0.3
    assert weather_types.weather_light_mult("nonsense") == 1.0


def test_fallback_when_the_registry_is_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(weather_types, "REGISTRY_DIR", tmp_path / "missing")
    weather_types.reload()
    assert weather_types.WEATHER_STATES == _CANONICAL
    assert weather_types.normalize_weather("snow") == "snowy"
    assert weather_types.weather_light_mult("stormy") == 0.3


def test_a_new_record_is_picked_up_without_a_code_change(monkeypatch, tmp_path):
    d = tmp_path / "weather"
    d.mkdir()
    (d / "acid_rain.json").write_text(json.dumps({
        "id": "acid_rain", "name": "Acid Rain", "kind": "extreme", "order": 8,
        "icon": "x", "light_mult": 0.4, "time_dc": 20,
        "description": "Rain hisses and burns.", "tags": ["weather", "extreme"],
    }), encoding="utf-8")
    monkeypatch.setattr(weather_types, "REGISTRY_DIR", d)
    weather_types.reload()
    assert "acid_rain" in weather_types.WEATHER_STATES
    assert weather_types.normalize_weather("acid_rain") == "acid_rain"
    assert weather_types.weather_light_mult("acid_rain") == 0.4
    assert weather_types.WEATHER_PROSE["acid_rain"] == "Rain hisses and burns."


def test_weather_forecast_reexports_the_registry():
    from engine import weather_forecast as wf
    assert wf.WEATHER_STATES == weather_types.WEATHER_STATES
    assert wf.WEATHER_TIME_DC["foggy"] == weather_types.WEATHER_TIME_DC["foggy"]
    assert wf.normalize_weather("fog") == "foggy"


def test_area_description_prose_covers_every_state():
    from engine import area_description as ad
    from engine.weather_forecast import WEATHER_STATES
    assert [s for s in WEATHER_STATES if s not in ad.WEATHER_PROSE] == []


def test_weather_is_a_registered_library_type():
    from routes import library_ops
    assert library_ops.VOCABULARY_TYPES.get("weather") == {
        "backing": "dir", "dir": "weather"}
