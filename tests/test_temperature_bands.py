"""Trait-resolved blood-temperature bands (cold/hot-blooded species).

Warm-blooded is the default and must reproduce the historic hardcoded numbers
exactly, so existing characters are unaffected.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.traits import TEMPERATURE_BANDS, TraitSystem


class _Player:
    def __init__(self, traits=None):
        self.traits = traits or {}


def test_warm_blooded_default_matches_historic_thresholds():
    band = TraitSystem.get_temperature_band(_Player())
    # These are the numbers the engine hardcoded before bands existed.
    assert band["normal"] == 37.0
    assert band["cold_mild"] == 35.0
    assert band["cold_severe"] == 33.0
    assert band["heat_mild"] == 38.0
    assert band["heat_severe"] == 40.0
    assert band["cold_floor"] == 25.0
    assert band["heat_ceiling"] == 45.0
    assert band["ambient_cold"] == 5.0
    assert band["ambient_hot"] == 35.0
    assert band["cold_critical"] == 30.0
    assert band["heat_critical"] == 42.0


def test_cold_blooded_trait_selects_its_band():
    band = TraitSystem.get_temperature_band(_Player({"cold_blooded": True}))
    assert band == TEMPERATURE_BANDS["cold_blooded"]
    # A frog at 20C is mildly cool, NOT critical (the reported absurdity).
    assert band["cold_mild"] < 20.0 < band["normal"]
    assert 20.0 > band["cold_critical"]


def test_hot_blooded_trait_selects_its_band():
    band = TraitSystem.get_temperature_band(_Player({"hot_blooded": True}))
    assert band == TEMPERATURE_BANDS["hot_blooded"]
    assert band["normal"] == 40.0


def test_partial_override_dict_is_applied(monkeypatch):
    from engine import traits as traits_mod

    monkeypatch.setitem(traits_mod.TRAIT_DEFINITIONS, "test_temperate", {
        "effects": {"temperature_band": {"normal": 30.0, "heat_mild": 33.0}},
    })
    band = traits_mod.TraitSystem.get_temperature_band(_Player({"test_temperate": True}))
    assert band["normal"] == 30.0
    assert band["heat_mild"] == 33.0
    assert band["cold_mild"] == 35.0        # untouched keys keep warm-blooded values


def test_unknown_band_name_falls_back_to_warm_blooded(monkeypatch):
    from engine import traits as traits_mod

    monkeypatch.setitem(traits_mod.TRAIT_DEFINITIONS, "test_mystery_band", {
        "effects": {"temperature_band": "no_such_band"},
    })
    band = traits_mod.TraitSystem.get_temperature_band(_Player({"test_mystery_band": True}))
    assert band == TEMPERATURE_BANDS["warm_blooded"]
