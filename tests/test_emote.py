"""Tests for narrative emote processing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import MagicMock


def test_process_emote_returns_raw_text():
    """process_emote returns the raw '{actor} {emote_text}.' format."""
    from virtual_world_engine import VirtualWorld
    engine = VirtualWorld()
    engine.players = {"Alice": MagicMock(current_area="tavern")}
    engine.record_turn_event = MagicMock()

    result = engine.process_emote("Alice", "waves at Bob")
    assert result == "Alice waves at Bob."


def test_process_emote_logs_area_event():
    """process_emote should call record_turn_event with type='emote'."""
    from virtual_world_engine import VirtualWorld
    engine = VirtualWorld()
    engine.players = {"Alice": MagicMock(current_area="tavern")}
    engine.narration.logging_events.record_turn_event = MagicMock()

    result = engine.process_emote("Alice", "waves at Bob")
    engine.narration.logging_events.record_turn_event.assert_called_with(
        "Alice", "emote", "Alice waves at Bob.", area_name="tavern"
    )
