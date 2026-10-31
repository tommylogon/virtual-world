"""Test 'text' and 'message' world actions integrating with The Commons (task-854)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import Node, Edge, EDGE_CARRYING


def _setup_app():
    app = create_app({"TESTING": True})
    return app


def _get_tags(m):
    if isinstance(m, dict):
        return m.get("tags", [])
    return getattr(m, "tags", [])


def _get_text(m):
    if isinstance(m, dict):
        return m.get("text", "")
    return getattr(m, "text", "")


def test_text_action_requires_phone():
    app = _setup_app()
    client = app.test_client()
    w = app.world

    hero = w.get_active_player_obj()
    if not hero:
        hero = next(iter(w.players.values()))
        w.player_manager.active_player = hero.name

    # Attempt to text without phone
    resp = client.post("/api/action", json={
        "command": "text Someone hey there",
        "character": hero.name,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "don't have a phone" in data.get("output", "")


def test_text_action_sends_dm_and_records_memories():
    app = _setup_app()
    client = app.test_client()
    w = app.world

    hero = w.get_active_player_obj()
    if not hero:
        hero = next(iter(w.players.values()))
        w.player_manager.active_player = hero.name

    other = next(p for p in w.players.values() if p.name != hero.name)

    # Spawn and give hero a phone
    phone_id = "test_phone_123"
    w.graph.add_node(Node(phone_id, type="item", name="smartphone", properties={"tags": ["device", "phone"]}))
    hero_node_id = w.player_manager._player_node_id(hero.name)
    w.graph.add_edge(Edge(phone_id, hero_node_id, EDGE_CARRYING))

    # Send direct text to other
    resp = client.post("/api/action", json={
        "command": f"text {other.name} Meet me at the lockers",
        "character": hero.name,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert f"You texted {other.name}" in data.get("output", "")

    # Check Commons DM channel
    dm_channel = w.commons.create_dm(hero.name, other.name)
    messages = [m for m in w.commons.messages if m["channel_id"] == dm_channel["id"]]
    assert len(messages) >= 1
    last_msg = messages[-1]
    assert last_msg["author"] == hero.name
    assert last_msg["text"] == "Meet me at the lockers"

    # Check memories
    hero_mems = [m for m in hero.memories if "text" in _get_tags(m)]
    assert len(hero_mems) >= 1

    other_mems = [m for m in other.memories if "text" in _get_tags(m)]
    assert len(other_mems) >= 1
    assert "Received text from" in _get_text(other_mems[-1])


def test_text_action_posts_to_channel():
    app = _setup_app()
    client = app.test_client()
    w = app.world

    hero = w.get_active_player_obj()
    if not hero:
        hero = next(iter(w.players.values()))
        w.player_manager.active_player = hero.name

    # Give hero a phone
    phone_id = "test_phone_channel"
    w.graph.add_node(Node(phone_id, type="item", name="smartphone", properties={"tags": ["device", "phone"]}))
    hero_node_id = w.player_manager._player_node_id(hero.name)
    w.graph.add_edge(Edge(phone_id, hero_node_id, EDGE_CARRYING))

    resp = client.post("/api/action", json={
        "command": "text #hellmouth who is bringing the snacks?",
        "character": hero.name,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "You posted to #hellmouth" in data.get("output", "")

    # Verify channel exists and message posted
    ch = next((c for c in w.commons.channels.values() if c.get("name") == "hellmouth"), None)
    assert ch is not None
    ch_messages = [m for m in w.commons.messages if m["channel_id"] == ch["id"]]
    assert len(ch_messages) >= 1
    assert ch_messages[-1]["text"] == "who is bringing the snacks?"
