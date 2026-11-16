"""Unit tests for heard speech narration formatting (task-683)."""
from unittest.mock import MagicMock
from engine.sound import format_heard_narration
from engine.narration import NarrationSystem


def test_format_heard_narration_cleans_direction():
    # Door with _back suffix normalized to readable name
    speech_line = format_heard_narration('"elena!! the bookcase"', "library_door_back", is_speech=True)
    assert speech_line == "You hear someone speaking from the library door."

    # Normal snake_case exit name
    sound_line = format_heard_narration("a loud metallic thud", "front_gate", is_speech=False)
    assert sound_line == "You hear a loud metallic thud from the front gate."

    # Cardinal direction
    cardinal_line = format_heard_narration('"hello?"', "north", is_speech=True)
    assert cardinal_line == "You hear someone speaking from the north."

    # Empty direction fallback
    empty_line = format_heard_narration('"hello?"', "", is_speech=True)
    assert empty_line == "You hear someone speaking nearby."


def test_narration_heard_speech_formatting():
    graph = MagicMock()
    player_manager = MagicMock()
    area_description = MagicMock()
    lighting = MagicMock()
    tick_manager = MagicMock()
    logging_events = MagicMock()
    skills = MagicMock()
    node_ids = MagicMock()

    narration = NarrationSystem(
        graph,
        player_manager,
        area_description,
        lighting,
        tick_manager,
        logging_events,
        skills,
        node_ids,
    )

    player = MagicMock()
    player.name = "Jake"
    player.recent_hearing = [
        {
            "type": "speech",
            "speaker": "Elena",
            "text": "the bookcase!",
            "speech_level": "shout",
            "heard_from": "library_door_back",
        }
    ]
    player_manager.active_player = "Jake"
    player_manager.get_player.return_value = player

    area = MagicMock()
    area.name = "Foyer"
    area.environment = {"noise": "quiet"}
    player_manager.current_area = area

    result = narration.listen()
    # Speaker must remain Elena, origin normalized from library_door_back to library door
    assert '[Heard] Elena from the library door shouted: "the bookcase!"' in result
