"""Regression tests for action_handlers Commons texting and memory invariants (task-935, task-936)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import EDGE_CARRYING, Edge, Node


def _setup_app_with_phone():
    app = create_app({"TESTING": True})
    w = app.world
    hero = w.get_active_player_obj()
    if not hero:
        hero = next(iter(w.players.values()))
        w.player_manager.active_player = hero.name
    other = next(p for p in w.players.values() if p.name != hero.name)

    phone_id = "test_phone_action_handlers"
    w.graph.add_node(Node(phone_id, type="item", name="smartphone", properties={"tags": ["device", "phone"]}))
    hero_node_id = w.player_manager._player_node_id(hero.name)
    w.graph.add_edge(Edge(phone_id, hero_node_id, EDGE_CARRYING))
    return app, w, hero, other


def _mem_text(mem):
    if isinstance(mem, dict):
        return mem.get("text", "")
    return getattr(mem, "text", "")


def test_commons_text_dm_writes_ledger_without_template_memories():
    app, w, hero, other = _setup_app_with_phone()
    client = app.test_client()
    before_counts = {name: len(p.memories) for name, p in w.players.items()}

    resp = client.post("/api/action", json={
        "action": f"text {other.name} Meet me at the lockers",
        "character": hero.name,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("success") is True
    assert f"You texted {other.name}" in data.get("output", "")

    dm_channel = w.commons.create_dm(hero.name, other.name)
    messages = [m for m in w.commons.messages if m["channel_id"] == dm_channel["id"]]
    assert len(messages) == 1
    assert messages[0]["author"] == hero.name
    assert messages[0]["text"] == "Meet me at the lockers"

    # task-936: texting writes message ledger state only, never hardcoded template memories.
    for name, p in w.players.items():
        assert len(p.memories) == before_counts[name]
        texts = [_mem_text(m) for m in p.memories]
        assert not any(t.startswith("Texted ") or t.startswith("Received text from") for t in texts)


def test_commons_post_channel_writes_ledger_without_template_memories():
    app, w, hero, _ = _setup_app_with_phone()
    client = app.test_client()
    before_counts = {name: len(p.memories) for name, p in w.players.items()}

    resp = client.post("/api/action", json={
        "action": "text #hellmouth Who left the lantern burning?",
        "character": hero.name,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("success") is True
    assert "You posted to #hellmouth" in data.get("output", "")

    ch = next((c for c in w.commons.channels.values() if c.get("name") == "hellmouth"), None)
    assert ch is not None
    ch_messages = [m for m in w.commons.messages if m["channel_id"] == ch["id"]]
    assert len(ch_messages) == 1
    assert ch_messages[0]["author"] == hero.name
    assert ch_messages[0]["text"] == "Who left the lantern burning?"

    for name, p in w.players.items():
        assert len(p.memories) == before_counts[name]
        texts = [_mem_text(m) for m in p.memories]
        assert not any(t.startswith("Posted to #") or t.startswith("Saw message from") for t in texts)


def test_commons_message_alias_and_record_memory_flags_write_no_template_memories():
    app, w, hero, other = _setup_app_with_phone()
    client = app.test_client()
    before_counts = {name: len(p.memories) for name, p in w.players.items()}

    for payload in (
        {"action": f"message {other.name} Checking in", "character": hero.name, "record_memory": True},
        {"action": f"message {other.name} Testing mode", "character": hero.name, "record_memory": False},
        {"action": "message #general Status update", "character": hero.name, "record_memory": False},
    ):
        resp = client.post("/api/action", json=payload)
        assert resp.status_code == 200
        assert resp.get_json().get("success") is True

    assert len(w.commons.messages) == 3
    for name, p in w.players.items():
        assert len(p.memories) == before_counts[name]


def test_commons_text_without_phone_fails_cleanly():
    app = create_app({"TESTING": True})
    client = app.test_client()
    w = app.world
    hero = w.get_active_player_obj()
    if not hero:
        hero = next(iter(w.players.values()))
        w.player_manager.active_player = hero.name
    before_counts = {name: len(p.memories) for name, p in w.players.items()}
    before_msgs = len(w.commons.messages)

    resp = client.post("/api/action", json={
        "action": "text Someone hey there",
        "character": hero.name,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("success") is False
    assert "don't have a phone" in data.get("output", "")
    assert len(w.commons.messages) == before_msgs
    for name, p in w.players.items():
        assert len(p.memories) == before_counts[name]


def test_approach_character_is_not_classified_as_item():
    from routes.action_handlers import validate_action_command

    app, w, hero, other = _setup_app_with_phone()
    w.name_matcher._set_player_area(other.name, hero.current_area)
    assert w._match_item_name(other.name) is None
    res = validate_action_command(w, hero.name, f"approach {other.name}")
    assert res["valid"] is True, res
    assert res["category"] == "character", res
    assert "Character" in res["detail"] and "Item" not in res["detail"], res
