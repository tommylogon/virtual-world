"""Tests for listener-side language comprehension barriers (task-967)."""

from __future__ import annotations

from area import Area
from graph import Edge, Node, WorldGraph
from player import Player
from virtual_world_engine import VirtualWorld
from engine.language_barrier import (
    extract_known_names_for_listener,
    mask_text_for_listener,
    resolve_speaker_language,
)


def _setup_world():
    world = VirtualWorld()
    world.load_from_dict({
        "graph": {
            "nodes": {
                "area_hall": {"id": "area_hall", "type": "area", "name": "Hallway", "properties": {"description": "A quiet hall."}},
                "area_side": {"id": "area_side", "type": "area", "name": "Alcove", "properties": {"description": "A small alcove."}},
                "way_hall_side": {"id": "way_hall_side", "type": "way", "name": "archway", "properties": {"way_type": "open", "current_state": "open"}},
                "player_Sarah": {
                    "id": "player_Sarah", "type": "character", "name": "Sarah",
                    "properties": {"languages": [{"language": "english", "fluency": "native", "known_words": [], "literate": True}]},
                },
                "player_Kenji": {
                    "id": "player_Kenji", "type": "character", "name": "Kenji",
                    "properties": {"languages": [
                        {"language": "japanese", "fluency": "native", "known_words": [], "literate": True},
                        {"language": "english", "fluency": "broken", "known_words": ["bathroom", "wait", "hungry"], "literate": True},
                    ]},
                },
                "player_Miki": {
                    "id": "player_Miki", "type": "character", "name": "Miki",
                    "properties": {"languages": [
                        {"language": "japanese", "fluency": "native", "known_words": [], "literate": True},
                        {"language": "english", "fluency": "fluent", "known_words": [], "literate": True},
                    ]},
                },
            },
            "edges": [
                {"source": "area_hall", "target": "way_hall_side", "type": "connection", "properties": {"direction": "north"}},
                {"source": "way_hall_side", "target": "area_side", "type": "connection", "properties": {"direction": ""}},
                {"source": "area_side", "target": "way_hall_side", "type": "connection", "properties": {"direction": "south"}},
                {"source": "way_hall_side", "target": "area_hall", "type": "connection", "properties": {"direction": ""}},
            ],
        },
        "players": {
            "Sarah": {"name": "Sarah", "current_area": "Hallway"},
            "Kenji": {"name": "Kenji", "current_area": "Hallway"},
            "Miki": {"name": "Miki", "current_area": "Alcove"},
        },
        "active_player": "Sarah",
    })
    sarah = world.players["Sarah"]
    kenji = world.players["Kenji"]
    miki = world.players["Miki"]
    return world, sarah, kenji, miki


def test_mask_text_for_listener_levels():
    world, sarah, kenji, miki = _setup_world()

    assert resolve_speaker_language(sarah) == "english"
    assert resolve_speaker_language(kenji) == "japanese"
    assert resolve_speaker_language(kenji, explicit_lang="English") == "english"

    line = "Wait here while I check the hallway upstairs"
    masked_kenji, did_mask_kenji = mask_text_for_listener(line, "english", kenji)
    assert did_mask_kenji is True
    assert masked_kenji == "Wait ??? ??? ??? ??? ??? ??? ???"
    assert "hallway" not in masked_kenji
    assert "upstairs" not in masked_kenji

    masked_miki, did_mask_miki = mask_text_for_listener(line, "english", miki)
    assert did_mask_miki is False
    assert masked_miki == line

    # Known character/place names remain recognizable even with broken/none fluency
    sarah.languages = [{"language": "english", "fluency": "native", "known_words": [], "literate": True}]
    known = extract_known_names_for_listener(kenji, extra_names=["Sarah"])
    masked_named, _ = mask_text_for_listener("Sarah, wait outside", "english", kenji, known_names=known)
    assert masked_named == "Sarah, wait ???"

    # Legacy characters with no authored languages pass through unmasked
    legacy = Player("Guest")
    legacy.current_area = "Hallway"
    assert mask_text_for_listener(line, "english", legacy) == (line, False)


def test_broadcast_speech_masks_recent_hearing_and_tags_turn_event():
    world, sarah, kenji, miki = _setup_world()

    world.broadcast_speech("Sarah", "Wait here while I check the hallway upstairs", speech_level="shout")

    # Same-room broken-English listener receives masked text in recent_hearing
    assert kenji.recent_hearing, "expected Kenji to hear speech"
    k_entry = kenji.recent_hearing[-1]
    assert k_entry["lang"] == "english"
    assert k_entry["comprehension_masked"] is True
    assert k_entry["text"] == "Wait ??? ??? ??? ??? ??? ??? ???"
    assert "upstairs" not in k_entry["text"]

    # Adjacent-room fluent-English listener receives unmasked text
    assert miki.recent_hearing, "expected Miki in adjacent alcove to hear shout"
    m_entry = miki.recent_hearing[-1]
    assert m_entry["lang"] == "english"
    assert m_entry.get("comprehension_masked") is not True
    assert m_entry["text"] == "Wait here while I check the hallway upstairs"

    # Turn event carries normalized lang metadata for WITNESSED prompt assembly
    speak_events = [e for e in world.turn_events if e.get("action") == "speak"]
    assert speak_events
    assert speak_events[-1].get("lang") == "english"


def test_examine_inscription_respects_literacy_and_language():
    world, sarah, kenji, miki = _setup_world()

    note = Node(
        "item_note",
        "item",
        "crumpled note",
        {
            "description": "A folded slip of paper.",
            "inscriptions": [
                {"by": "Kenji", "text": "Meet at the shrine tonight", "lang": "japanese", "tick": 4}
            ],
        },
    )
    world.graph.add_node(note)
    world.graph.add_edge(Edge("item_note", "area_hall", "in"))

    # Sarah knows no Japanese -> cannot read the note
    world.set_active_player("Sarah")
    sarah_view = world.get_item_desc("crumpled note")
    assert "shrine" not in sarah_view
    assert "[japanese]" in sarah_view

    # Kenji is literate native in Japanese -> reads it cleanly
    world.set_active_player("Kenji")
    kenji_view = world.get_item_desc("crumpled note")
    assert "Meet at the shrine tonight" in kenji_view

    # Illiterate native cannot read written text even in their native language
    kenji.languages[0]["literate"] = False
    illit_view = world.get_item_desc("crumpled note")
    assert "shrine" not in illit_view
    assert "???" in illit_view
