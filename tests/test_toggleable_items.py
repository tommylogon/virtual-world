"""Tests for ToggleableItems + the on_light companion trigger (task-396).

on_light was declared in constants but had no caller — the fix makes
toggle_item_status fire it alongside on_toggle_on when an item turns on, so
authors can bind "this got lit" flavor without the toggle_on/off dichotomy.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import MagicMock
from graph import Node, Edge, EDGE_TRIGGERS
from engine.toggleable_items import ToggleableItems
from engine.trigger_system import TriggerSystem
from engine.skills import SkillSystem
from engine.logging_events import GameLogger


@pytest.fixture
def graph():
    from graph import WorldGraph
    return WorldGraph()


@pytest.fixture
def trigger_system(graph):
    from engine.player_manager import PlayerManager
    pm = PlayerManager(None)
    return TriggerSystem(graph, SkillSystem(pm, GameLogger()), GameLogger())


def _make_item(graph, tid):
    item = Node(
        id=f"item_{tid}",
        type="item",
        name=tid,
        properties={
            "tags": ["toggleable", "light_source"],
            "current_state": "unlit",
            "uses": 5,
        },
    )
    graph.add_node(item)
    return item


def _wire_trigger(graph, item, label, tt, msg=None):
    props = {
        "trigger_type": tt,
        "conditions": [],
        "effects": [{"type": "message", "params": {"message": msg or f"{label} fired."}}],
        "success_message": "",
        "fail_message": "",
    }
    tn = Node(id=f"trig_{item.id}_{label}", type="logic_trigger", name=label, properties=props)
    graph.add_node(tn)
    graph.add_edge(Edge(source=item.id, target=tn.id, type=EDGE_TRIGGERS, properties=props))


def _make_player_manager(graph, trigger_system, carried=None, active_player="test"):
    pm = MagicMock()
    pm.active_player = active_player
    pm.players = {active_player: MagicMock(name=active_player)}
    pm.current_area = MagicMock(name="hall")
    pm.lighting = MagicMock()
    pm.lighting.get_ambient_light.return_value = 0
    pm.lighting.light_to_level.return_value = "dim"
    pm._execute_triggers = trigger_system._execute_triggers
    pm.add_log_entry = MagicMock()
    pm.record_turn_event = MagicMock()
    # Reachability: find_item_node returns a carried item by name.
    carried = carried or []
    pm.find_item_node = MagicMock(
        side_effect=lambda n: next((c for c in carried if c.name == n), None)
    )
    return pm


def test_toggle_on_fires_both_on_toggle_on_and_on_light(graph, trigger_system):
    """Flipping a toggleable ON runs BOTH on_toggle_on and its on_light companion."""
    item = _make_item(graph, "lantern")
    _wire_trigger(graph, item, "toggle_on", "on_toggle_on")
    _wire_trigger(graph, item, "light", "on_light")
    toggler = ToggleableItems(graph, None)
    pm = _make_player_manager(graph, trigger_system, carried=[item])
    result = toggler.toggle_item_status(pm, "lantern")
    assert item.properties["current_state"] == "lit"
    assert "toggle_on fired." in result
    assert "light fired." in result


def test_turn_off_fires_on_toggle_off_only(graph, trigger_system):
    """Turning OFF fires on_toggle_off, NOT on_light / on_toggle_on."""
    item = _make_item(graph, "lantern")
    item.properties["current_state"] = "lit"
    _wire_trigger(graph, item, "toggle_on", "on_toggle_on")
    _wire_trigger(graph, item, "light", "on_light")
    _wire_trigger(graph, item, "toggle_off", "on_toggle_off")
    toggler = ToggleableItems(graph, None)
    pm = _make_player_manager(graph, trigger_system, carried=[item])
    result = toggler.toggle_item_status(pm, "lantern")
    assert item.properties["current_state"] == "unlit"
    assert "toggle_off fired." in result
    assert "toggle_on fired." not in result
    assert "light fired." not in result


def test_depleted_toggle_fires_on_depleted(graph, trigger_system):
    """Consuming the last use on turn-on triggers on_depleted and resets state."""
    item = _make_item(graph, "candle")
    item.properties["uses"] = 1
    _wire_trigger(graph, item, "depleted", "on_depleted")
    toggler = ToggleableItems(graph, None)
    pm = _make_player_manager(graph, trigger_system, carried=[item])
    result = toggler.toggle_item_status(pm, "candle")
    assert item.properties.get("current_state") == "unlit"
    assert "depleted fired." in result


def test_non_toggleable_refused(graph, trigger_system):
    """A non-toggleable item can't be toggled."""
    item = Node(id="item_rock", type="item", name="rock",
                properties={"current_state": "normal", "tags": []})
    graph.add_node(item)
    toggler = ToggleableItems(graph, None)
    pm = _make_player_manager(graph, trigger_system, carried=[item])
    with pytest.raises(ValueError, match="can't be toggled"):
        toggler.toggle_item_status(pm, "rock")