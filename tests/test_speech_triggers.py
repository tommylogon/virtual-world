"""Verify on_speech wiring: speaking in an area fires item on_speech triggers
and the speech_matches contexts (contains/not_contains gate) reach llm_respond."""

import json

import pytest

from app import create_app
from graph import Node, Edge, EDGE_IN


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})


def _setup_area_item(app):
    g = app.world.graph
    aid = "area_speech_hall"
    g.add_node(Node(id=aid, type="area", name="Speech Hall", properties={}))
    iid = "item_talking_mirror"
    g.add_node(Node(id=iid, type="item", name="Talking Mirror", properties={}))
    g.add_edge(Edge(source=iid, target=aid, type=EDGE_IN))
    return aid, iid


def test_on_speech_fires_llm_respond(app):
    aid, iid = _setup_area_item(app)
    # create the mirror's on_speech password trigger in-world
    app.world.triggers.create_trigger(iid, "on_speech", effects=[
        {"type": "llm_respond", "params": {
            "instructions": "You are a mirror.", "fallback_message": "silence",
            "max_words": 5, "name": "The Mirror"}}
    ], conditions={"operator": "and", "conditions": [
        {"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}
    ]})
    # move the active player into the hall
    pname = app.world.active_player
    player = app.world.players[pname]
    player.current_area = "Speech Hall"
    app.world.player_manager._set_player_area(pname, "Speech Hall")
    # speak the magic words
    app.world.broadcast_speech(pname, "open sesame please")
    pending = list(app.world.llm_pending_requests)
    assert len(pending) == 1
    req = pending[0]
    assert req["speaker"] == "The Mirror"
    assert "open sesame please" in req["heard"]


def test_on_speech_wrong_words_no_request(app):
    aid, iid = _setup_area_item(app)
    app.world.triggers.create_trigger(iid, "on_speech", effects=[
        {"type": "llm_respond", "params": {
            "instructions": "mirror", "fallback_message": "silence",
            "max_words": 5, "name": "The Mirror"}}
    ], conditions={"operator": "and", "conditions": [
        {"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}
    ]})
    pname = app.world.active_player
    player = app.world.players[pname]
    player.current_area = "Speech Hall"
    app.world.player_manager._set_player_area(pname, "Speech Hall")
    app.world.broadcast_speech(pname, "wrong words today")
    assert len(app.world.llm_pending_requests) == 0


def test_on_speech_not_contains_gate(app):
    aid, iid = _setup_area_item(app)
    # not_contains branch: fires only when the phrase is NOT spoken
    app.world.triggers.create_trigger(iid, "on_speech", effects=[
        {"type": "llm_respond", "params": {
            "instructions": "mirror", "fallback_message": "silence",
            "max_words": 5, "name": "The Mirror"}}
    ], conditions={"operator": "and", "conditions": [
        {"type": "speech_matches", "phrase": "open sesame", "mode": "not_contains"}
    ]})
    pname = app.world.active_player
    player = app.world.players[pname]
    player.current_area = "Speech Hall"
    app.world.player_manager._set_player_area(pname, "Speech Hall")
    app.world.broadcast_speech(pname, "hello there")
    assert len(app.world.llm_pending_requests) == 1
