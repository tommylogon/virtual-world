"""Tests for task-684: matches, candle_stub, and candlestick carry lighting triggers in library."""
from __future__ import annotations

import json
from pathlib import Path

ITEMS_DIR = Path("data/library/items")


def test_matches_library_triggers():
    path = ITEMS_DIR / "matches.json"
    assert path.exists(), "matches.json must exist"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "toggleable" in data.get("tags", []), "matches must have toggleable tag"
    triggers = data.get("triggers", [])
    assert isinstance(triggers, list) and len(triggers) >= 2, "matches must carry triggers list"
    trigger_types = {t.get("trigger_type") for t in triggers}
    assert "on_light" in trigger_types, "matches must carry on_light trigger"
    assert "on_toggle_off" in trigger_types, "matches must carry on_toggle_off trigger"


def test_candle_stub_library_triggers():
    path = ITEMS_DIR / "candle_stub.json"
    assert path.exists(), "candle_stub.json must exist"
    data = json.loads(path.read_text(encoding="utf-8"))
    tags = data.get("tags", [])
    assert isinstance(tags, list), "tags must be a normalized list, not an xml-dict wrapper"
    assert "toggleable" in tags, "candle_stub must have toggleable tag"
    triggers = data.get("triggers", [])
    assert isinstance(triggers, list) and len(triggers) >= 2, "triggers must be a list"
    trigger_types = {t.get("trigger_type") for t in triggers}
    assert "on_light" in trigger_types, "candle_stub must carry on_light trigger"
    assert "on_use" in trigger_types, "candle_stub must carry on_use trigger"


def test_candlestick_library_triggers():
    path = ITEMS_DIR / "candlestick.json"
    assert path.exists(), "candlestick.json must exist"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "toggleable" in data.get("tags", []), "candlestick must have toggleable tag"
    triggers = data.get("triggers", [])
    assert isinstance(triggers, list) and len(triggers) >= 2, "candlestick must carry triggers list"
    trigger_types = {t.get("trigger_type") for t in triggers}
    assert "on_light" in trigger_types, "candlestick must carry on_light trigger"
    assert "on_toggle_on" in trigger_types, "candlestick must carry on_toggle_on trigger"
    assert "on_toggle_off" in trigger_types, "candlestick must carry on_toggle_off trigger"


def test_zero_em_dashes_in_lighting_items():
    for name in ("matches.json", "candle_stub.json", "candlestick.json"):
        txt = (ITEMS_DIR / name).read_text(encoding="utf-8")
        bad = [ord(c) for c in txt if ord(c) in (8211, 8212)]
        assert bad == [], f"{name} contains em/en dashes: {bad}"
