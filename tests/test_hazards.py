"""Tests for the terrain hazard registry (task-745)."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import hazards


def test_shipped_registry_validates_clean():
    assert hazards.validate() == []


def test_registry_has_the_named_categories():
    ids = set(hazards.hazards())
    for hid in ("river", "rapids", "cliff", "fall", "thorns", "pit", "bridge_jump"):
        assert hid in ids, f"missing hazard {hid}"


def test_dc_ladder_picks_the_highest_rung_at_or_below_strength():
    # river ladder: 1:8 5:12 10:15 15:18 20:22
    assert hazards.dc_for("river", 0) == 8     # below the lowest rung -> lowest
    assert hazards.dc_for("river", 1) == 8
    assert hazards.dc_for("river", 5) == 12
    assert hazards.dc_for("river", 9) == 12    # between rungs -> lower rung
    assert hazards.dc_for("river", 20) == 22
    assert hazards.dc_for("river", 99) == 22   # above the highest -> highest


def test_dc_for_an_unknown_hazard_is_none():
    assert hazards.dc_for("nonexistent", 10) is None


def test_a_hazard_references_a_real_ability():
    for hid, rec in hazards.hazards().items():
        assert rec["ability"] in ("STR", "DEX", "CON", "INT", "WIS", "CHA"), hid


def test_an_unknown_ability_is_rejected():
    data = copy.deepcopy(hazards.load())
    data["hazards"]["bad"] = {
        "name": "Bad", "ability": "LUCK", "dc": {"1": 10},
        "on_fail": {"conditions": [], "tags": []},
        "message_success": "ok", "message_fail": "no",
    }
    problems = " ".join(hazards.validate(data))
    assert "ability must be one of" in problems


def test_an_empty_ladder_is_rejected():
    data = copy.deepcopy(hazards.load())
    data["hazards"]["bad"] = {
        "name": "Bad", "ability": "STR", "dc": {},
        "on_fail": {"conditions": [], "tags": []},
        "message_success": "ok", "message_fail": "no",
    }
    problems = " ".join(hazards.validate(data))
    assert "dc must be a non-empty" in problems


def test_ladder_tolerates_non_numeric_entries():
    assert hazards.ladder({"dc": []}) == []
    assert hazards.ladder({"dc": {"x": "y", "5": 12}}) == [(5, 12)]
    assert hazards.ladder({}) == []
