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

    # task-936: Commons message delivery does not inject hardcoded template memories
    hero_mems = [m for m in hero.memories if "text" in _get_tags(m)]
    assert len(hero_mems) == 0

    other_mems = [m for m in other.memories if "text" in _get_tags(m)]
    assert len(other_mems) == 0


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


def _give_phone(w, player_name, node_id, *, props=None):
    w.graph.add_node(Node(node_id, type="item", name="smartphone", properties=props or {"tags": ["device", "phone"]}))
    p_node_id = w.player_manager._player_node_id(player_name)
    w.graph.add_edge(Edge(node_id, p_node_id, EDGE_CARRYING))
    return w.graph.get_node(node_id)


def test_text_refuses_dead_or_powered_off_sender_phone():
    app = _setup_app()
    client = app.test_client()
    w = app.world

    hero = w.get_active_player_obj() or next(iter(w.players.values()))
    w.player_manager.active_player = hero.name
    other = next(p for p in w.players.values() if p.name != hero.name)

    _give_phone(w, hero.name, "dead_phone_1", props={"tags": ["device", "phone"], "uses": 0})
    resp = client.post("/api/action", json={
        "command": f"text {other.name} hello",
        "character": hero.name,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("success") is False
    assert "out of power or turned off" in data.get("output", "")

    # Also test current_state="off" via 'message' alias
    phone = w.graph.get_node("dead_phone_1")
    phone.properties["uses"] = 5
    phone.properties["current_state"] = "off"
    resp2 = client.post("/api/action", json={
        "command": f"message {other.name} hello again",
        "character": hero.name,
    })
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2.get("success") is False
    assert "out of power or turned off" in data2.get("output", "")


def test_dm_text_active_vs_silenced_vs_queued_recipient_phone():
    from engine.long_distance_comms import deliver_queued_dms

    app = _setup_app()
    client = app.test_client()
    w = app.world

    hero = w.get_active_player_obj() or next(iter(w.players.values()))
    w.player_manager.active_player = hero.name
    other = next(p for p in w.players.values() if p.name != hero.name)

    _give_phone(w, hero.name, "hero_phone_active")

    # 1. Recipient has NO phone -> queued, no notification event, no memory
    w.turn_events.clear()
    resp = client.post("/api/action", json={
        "command": f"text {other.name} Are you there?",
        "character": hero.name,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("success") is True
    assert "queued" in data.get("output", "")
    assert not any(e.get("action") == "phone_notification" for e in w.turn_events)
    assert len(getattr(w, "queued_dms", {}).get(other.name, [])) == 1
    assert not any("text" in _get_tags(m) for m in other.memories)

    # 2. Recipient gets an active phone and queued DMs deliver
    recip_phone = _give_phone(w, other.name, "other_phone_1", props={"tags": ["device", "phone"], "uses": 5})
    delivered_count = deliver_queued_dms(w, other.name)
    assert delivered_count == 1
    assert any(
        e.get("actor") == other.name and e.get("action") == "phone_notification"
        for e in w.turn_events
    )

    # 3. Recipient phone is silenced -> delivered immediately, NO notification event
    w.turn_events.clear()
    recip_phone.properties["silenced"] = True
    resp2 = client.post("/api/action", json={
        "command": f"text {other.name} Silent check",
        "character": hero.name,
    })
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2.get("success") is True
    assert "queued" not in data2.get("output", "")
    assert not any(e.get("action") == "phone_notification" for e in w.turn_events)

    # 4. Recipient phone is dead -> queued again
    recip_phone.properties["silenced"] = False
    recip_phone.properties["uses"] = 0
    resp3 = client.post("/api/action", json={
        "command": f"text {other.name} Battery dead?",
        "character": hero.name,
    })
    assert resp3.status_code == 200
    assert "queued" in resp3.get_json().get("output", "")
    assert not any(e.get("action") == "phone_notification" for e in w.turn_events)


def test_call_answer_hangup_action_handler_paths():
    app = _setup_app()
    client = app.test_client()
    w = app.world

    hero = w.get_active_player_obj() or next(iter(w.players.values()))
    w.player_manager.active_player = hero.name
    other = next(p for p in w.players.values() if p.name != hero.name)

    # Dead sender phone -> call fails
    hero_phone = _give_phone(w, hero.name, "call_hero_phone", props={"tags": ["device", "phone"], "uses": 0})
    resp_dead = client.post("/api/action", json={"command": f"call {other.name}", "character": hero.name})
    assert resp_dead.status_code == 200
    assert resp_dead.get_json().get("success") is False

    # Active sender phone, no recipient phone -> no answer
    hero_phone.properties["uses"] = 5
    resp_no_ans = client.post("/api/action", json={"command": f"call {other.name}", "character": hero.name})
    assert resp_no_ans.status_code == 200
    assert "no answer" in resp_no_ans.get_json().get("output", "")

    # Active recipient phone -> call rings, answer connects, hangup ends
    _give_phone(w, other.name, "call_other_phone", props={"tags": ["device", "phone"], "uses": 5})
    resp_call = client.post("/api/action", json={"command": f"call {other.name}", "character": hero.name})
    assert resp_call.status_code == 200
    assert "ringing" in resp_call.get_json().get("output", "")

    resp_ans = client.post("/api/action", json={"command": "answer", "character": other.name})
    assert resp_ans.status_code == 200
    assert "on a call" in resp_ans.get_json().get("output", "")
    assert other.has_condition("on_a_call")

    resp_hangup = client.post("/api/action", json={"command": "hangup", "character": hero.name})
    assert resp_hangup.status_code == 200
    assert "hang up" in resp_hangup.get_json().get("output", "")
    assert not other.has_condition("on_a_call")
