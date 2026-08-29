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


# ── Emote person normalization (narrator stamps the name, so the phrase
#    itself must be third person: never "you"/"your"/"I"/"my") ──────────────

def test_normalize_emote_person_second_person_reflexive():
    from engine.narration import normalize_emote_person
    assert normalize_emote_person("hugs yourself tightly") == "hugs themselves tightly"


def test_normalize_emote_person_second_person_possessive():
    from engine.narration import normalize_emote_person
    assert normalize_emote_person("sinks down, hugging your knees to your chest") == \
        "sinks down, hugging their knees to their chest"


def test_normalize_emote_person_first_person_reflexive():
    from engine.narration import normalize_emote_person
    assert normalize_emote_person("shivers and hugs myself") == "shivers and hugs themselves"


def test_normalize_emote_person_leading_base_verb():
    from engine.narration import normalize_emote_person
    assert normalize_emote_person("hug my knees and shiver") == "hugs their knees and shiver"


def test_normalize_emote_person_leaves_third_person_alone():
    from engine.narration import normalize_emote_person
    assert normalize_emote_person("kisses Alice gently") == "kisses Alice gently"
    assert normalize_emote_person("leans in close") == "leans in close"
    assert normalize_emote_person("glances at the door") == "glances at the door"


def test_process_emote_stamps_third_person_under_name():
    """The full pipeline: a 2nd-person emote becomes a proper name-stamped line."""
    from virtual_world_engine import VirtualWorld
    engine = VirtualWorld()
    engine.players = {"Lyrie": MagicMock(current_area="hollow")}
    engine.narration.logging_events.record_turn_event = MagicMock()

    result = engine.process_emote("Lyrie", "hugs yourself tightly")
    assert result == "Lyrie hugs themselves tightly."


def test_process_emote_strips_leading_name_before_normalizing():
    """A name-prefixed, first-person emote gets one clean third-person line."""
    from virtual_world_engine import VirtualWorld
    engine = VirtualWorld()
    engine.players = {"Lyrie": MagicMock(current_area="hollow")}
    engine.narration.logging_events.record_turn_event = MagicMock()

    result = engine.process_emote("Lyrie", "Lyrie shivers and hugs myself")
    assert result == "Lyrie shivers and hugs themselves."
