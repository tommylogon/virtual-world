"""Unit tests for long-distance communication (phones, walkie-talkies, radios) - task-299."""

import json
from pathlib import Path
import pytest

from area import Area
from graph import EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN, Edge, Node
from player import Player
from virtual_world_engine import VirtualWorld
from engine.items.action_contract import is_part, is_portable, parent_of
from engine.long_distance_comms import (
    is_device_active,
    get_device_comms_channel,
    get_device_speakerphone,
    initiate_call,
    answer_call,
    end_call,
    toggle_speakerphone,
    tune_channel,
)


def _setup_world():
    w = VirtualWorld()
    area_a = Area("Command Center", "A room full of monitors.", [])
    area_b = Area("Distant Ridge", "A cold windblown ridge far away.", [])
    area_c = Area("Underground Bunker", "A fortified room with heavy blast doors.", [])
    w.movement.add_area(area_a)
    w.movement.add_area(area_b)
    w.movement.add_area(area_c)

    # Players
    alice = Player("Alice")
    alice.current_area = "Command Center"
    w.player_manager.players["Alice"] = alice
    w.name_matcher._set_player_area("Alice", "Command Center")

    bob = Player("Bob")
    bob.current_area = "Distant Ridge"
    w.player_manager.players["Bob"] = bob
    w.name_matcher._set_player_area("Bob", "Distant Ridge")

    cara = Player("Cara")
    cara.current_area = "Underground Bunker"
    w.player_manager.players["Cara"] = cara
    w.name_matcher._set_player_area("Cara", "Underground Bunker")

    dave = Player("Dave")
    dave.current_area = "Distant Ridge"  # In same room as Bob, bystander
    w.player_manager.players["Dave"] = dave
    w.name_matcher._set_player_area("Dave", "Distant Ridge")

    return w


def _give_radio(w, player_name: str, channel: str = "alpha", speakerphone: bool = False, battery_uses: int = 20):
    radio = Node(
        id=f"item_radio_{player_name.lower()}",
        type="item",
        name=f"{player_name}'s Radio",
        properties={
            "actions": ["examine", "take", "drop", "use"],
            "tags": ["device", "radio", "communication", "electric"],
            "comms_channel": channel,
            "speakerphone": speakerphone,
            "current_state": "lit",
            "uses": -1,
        },
    )
    w.graph.add_node(radio)

    battery = Node(
        id=f"item_battery_{player_name.lower()}",
        type="item",
        name="radio battery",
        properties={
            "actions": ["examine", "use"],
            "tags": ["part", "electric", "power_source", "battery"],
            "current_state": "lit",
            "uses": battery_uses,
        },
    )
    w.graph.add_node(battery)
    # Part is inside radio
    w.graph.add_edge(Edge(source=battery.id, target=radio.id, type=EDGE_IN))

    # Radio is carried by player
    p_id = w.player_manager.get_player_node_id(player_name)
    w.graph.add_edge(Edge(source=radio.id, target=p_id, type=EDGE_CARRYING))

    return radio, battery


def _give_phone(w, player_name: str, battery_uses: int = 24):
    phone = Node(
        id=f"item_phone_{player_name.lower()}",
        type="item",
        name=f"{player_name}'s Phone",
        properties={
            "actions": ["examine", "take", "drop", "use"],
            "tags": ["device", "phone", "communication", "electric"],
            "current_state": "lit",
            "uses": -1,
            "speakerphone": False,
        },
    )
    w.graph.add_node(phone)

    battery = Node(
        id=f"item_battery_{player_name.lower()}",
        type="item",
        name="phone battery",
        properties={
            "actions": ["examine", "use"],
            "tags": ["part", "electric", "power_source", "battery"],
            "current_state": "lit",
            "uses": battery_uses,
        },
    )
    w.graph.add_node(battery)
    w.graph.add_edge(Edge(source=battery.id, target=phone.id, type=EDGE_IN))

    p_id = w.player_manager.get_player_node_id(player_name)
    w.graph.add_edge(Edge(source=phone.id, target=p_id, type=EDGE_CARRYING))

    return phone, battery


# ── Criterion 1: Device composition & child parts ───────────────────────────

def test_device_composition_and_non_portable_parts():
    w = _setup_world()
    radio, battery = _give_radio(w, "Alice", channel="alpha")

    assert is_part(battery)
    assert not is_part(radio)
    assert is_portable(radio)
    assert parent_of(w.graph, battery) is radio
    assert "power" not in battery.properties
    assert "power" not in radio.properties
    assert battery.properties["uses"] == 20


# ── Criterion 2 & 3: Comms channel relay and channel isolation ──────────────

def test_comms_channel_speech_relays_across_distances():
    w = _setup_world()
    _give_radio(w, "Alice", channel="alpha")
    _give_radio(w, "Bob", channel="alpha")
    _give_radio(w, "Cara", channel="beta")  # Cara is on different channel

    bob = w.player_manager.players["Bob"]
    cara = w.player_manager.players["Cara"]

    # Alice speaks on channel alpha from Command Center
    w.broadcast_speech("Alice", "meet at the east gate", area_name="Command Center")

    # Bob (on alpha) hears it in recent_hearing despite being in distant ridge
    bob_hearings = [h for h in bob.recent_hearing if h.get("heard_via") == "comms"]
    assert len(bob_hearings) == 1
    assert bob_hearings[0]["speaker"] == "Alice"
    assert bob_hearings[0]["text"] == "meet at the east gate"
    assert bob_hearings[0]["comms_channel"] == "alpha"

    # Cara (on beta) hears nothing
    cara_hearings = [h for h in getattr(cara, "recent_hearing", []) if h.get("heard_via") == "comms"]
    assert len(cara_hearings) == 0


def test_speakerphone_isolation_and_bystander_hearing():
    w = _setup_world()
    _give_radio(w, "Alice", channel="alpha")
    bob_radio, _ = _give_radio(w, "Bob", channel="alpha", speakerphone=False)

    bob = w.player_manager.players["Bob"]
    dave = w.player_manager.players["Dave"]  # In same room as Bob

    # 1. With speakerphone OFF on Bob's radio
    w.broadcast_speech("Alice", "secret transmission 1", area_name="Command Center")

    # Bob heard it through earpiece
    assert any(h.get("text") == "secret transmission 1" for h in bob.recent_hearing)
    # Dave (bystander) heard nothing
    assert not any(h.get("text") == "secret transmission 1" for h in getattr(dave, "recent_hearing", []))

    # 2. Toggle speakerphone ON on Bob's radio
    bob_radio.properties["speakerphone"] = True

    w.broadcast_speech("Alice", "loud transmission 2", area_name="Command Center")

    # Bob heard it
    assert any(h.get("text") == "loud transmission 2" for h in bob.recent_hearing)
    # Dave (bystander) now heard it via speakerphone
    assert any(h.get("text") == "loud transmission 2" and h.get("heard_via") == "speakerphone"
               for h in getattr(dave, "recent_hearing", []))


# ── Criterion 4: Depleted device cannot relay ───────────────────────────────

def test_depleted_battery_cannot_relay():
    w = _setup_world()
    _give_radio(w, "Alice", channel="alpha")
    _, bob_battery = _give_radio(w, "Bob", channel="alpha", battery_uses=0)  # Depleted!

    bob = w.player_manager.players["Bob"]
    w.broadcast_speech("Alice", "can you hear me?", area_name="Command Center")

    # Bob's radio has 0 uses on battery, so it cannot receive or relay
    assert not any(h.get("text") == "can you hear me?" for h in getattr(bob, "recent_hearing", []))


def test_missing_or_spent_device_cannot_transmit():
    w = _setup_world()
    alice_radio, _ = _give_radio(w, "Alice", channel="alpha")
    _give_radio(w, "Bob", channel="alpha")

    bob = w.player_manager.players["Bob"]

    # Mark Alice's radio spent/off
    alice_radio.properties["current_state"] = "off"

    w.broadcast_speech("Alice", "transmission with off radio", area_name="Command Center")

    # Bob receives nothing because transmitter was off
    assert not any(h.get("text") == "transmission with off radio" for h in getattr(bob, "recent_hearing", []))


# ── Directed phone calls & ongoing call condition ───────────────────────────

def test_directed_phone_call_flow():
    w = _setup_world()
    alice_phone, _ = _give_phone(w, "Alice")
    bob_phone, _ = _give_phone(w, "Bob")

    alice = w.player_manager.players["Alice"]
    bob = w.player_manager.players["Bob"]

    # Alice calls Bob
    init_res = initiate_call(w, "Alice", "Bob", alice_phone)
    assert "ringing" in init_res.lower()
    assert bob_phone.properties.get("call_state") == "ringing"
    assert bob_phone.properties.get("incoming_call_from") == "Alice"

    # Bob answers
    ans_res = answer_call(w, "Bob", bob_phone)
    assert "answer" in ans_res.lower()
    assert alice.has_condition("on_a_call")
    assert bob.has_condition("on_a_call")

    # Ongoing call does not block movement or actions
    assert not alice.has_condition("unconscious")
    assert not bob.has_condition("unconscious")
    assert alice.state != "unconscious"
    assert bob.state != "unconscious"

    # Alice speaks during the call
    w.broadcast_speech("Alice", "hello over the wire", area_name="Command Center")

    # Bob receives the call speech
    bob_call_hearing = [h for h in bob.recent_hearing if h.get("heard_via") == "call"]
    assert len(bob_call_hearing) == 1
    assert bob_call_hearing[0]["text"] == "hello over the wire"
    assert bob_call_hearing[0]["caller"] == "Alice"

    # Alice hangs up
    hangup_res = end_call(w, "Alice", alice_phone)
    assert "hang up" in hangup_res.lower()
    assert not alice.has_condition("on_a_call")
    assert not bob.has_condition("on_a_call")


# ── Carried items on_speech triggers ────────────────────────────────────────

def test_carried_items_receive_on_speech_triggers():
    w = _setup_world()
    aid = w.get_current_area_id()
    player_id = w.player_manager.get_player_node_id("Alice")

    # Carried smart recorder item
    recorder = Node(
        id="item_smart_recorder",
        type="item",
        name="Smart Recorder",
        properties={"actions": ["examine", "take", "drop"]},
    )
    w.graph.add_node(recorder)
    w.graph.add_edge(Edge(source=recorder.id, target=player_id, type=EDGE_CARRYING))

    fired = []

    def mock_trigger(node, trigger_type, target_name=None, context=None, other=None, game_state=None):
        fired.append((node.id, trigger_type, context.get("speech") if context else None))
        return []

    w.narration.speech.trigger_fn = mock_trigger

    w.broadcast_speech("Alice", "recording test 123", area_name="Command Center")

    # The carried recorder must receive on_speech
    assert any(f[0] == "item_smart_recorder" and f[1] == "on_speech" and f[2] == "recording test 123" for f in fired)


# ── ItemActions integration tests (use / use on / channel tuning) ───────────

def test_use_phone_on_target_initiates_and_answers():
    w = _setup_world()
    alice_phone, _ = _give_phone(w, "Alice")
    bob_phone, _ = _give_phone(w, "Bob")

    w.name_matcher._set_player_area(w.active_player, "Command Center")
    w.player_manager.active_player = "Alice"

    # Alice uses phone on Bob
    res = w.use_item_on(alice_phone.name, "Bob")
    assert "ringing" in res.lower()
    assert bob_phone.properties.get("call_state") == "ringing"

    # Switch to Bob, who uses phone to answer
    w.player_manager.active_player = "Bob"
    ans_res = w.use_item(bob_phone.name)
    assert "answer" in ans_res.lower()
    assert w.player_manager.players["Alice"].has_condition("on_a_call")
    assert w.player_manager.players["Bob"].has_condition("on_a_call")

    # Bob uses phone again to hang up
    hang_res = w.use_item(bob_phone.name)
    assert "hang up" in hang_res.lower()
    assert not w.player_manager.players["Alice"].has_condition("on_a_call")
    assert not w.player_manager.players["Bob"].has_condition("on_a_call")


def test_tune_radio_channel_via_use_item_on():
    w = _setup_world()
    radio, _ = _give_radio(w, "Alice", channel="alpha")
    w.player_manager.active_player = "Alice"

    # Alice tunes radio to beta
    res = w.use_item_on(radio.name, "beta")
    assert "beta" in res
    assert radio.properties.get("comms_channel") == "beta"


def test_area_placed_speakerphone_radio():
    w = _setup_world()
    # Alice has carried radio on alpha
    _give_radio(w, "Alice", channel="alpha")

    # Stationary base station radio placed in Underground Bunker on alpha with speakerphone ON
    base_radio = Node(
        id="item_base_station",
        type="item",
        name="Base Station",
        properties={
            "actions": ["examine", "use"],
            "tags": ["device", "radio", "communication", "electric"],
            "comms_channel": "alpha",
            "speakerphone": True,
            "current_state": "lit",
            "uses": -1,
        },
    )
    w.graph.add_node(base_radio)
    bunker_id = next(n.id for n in w.graph.nodes.values() if n.type == "area" and n.name == "Underground Bunker")
    w.graph.add_edge(Edge(source=base_radio.id, target=bunker_id, type=EDGE_IN))

    cara = w.player_manager.players["Cara"]  # in Underground Bunker

    w.broadcast_speech("Alice", "alert to all stations", area_name="Command Center")

    # Cara was in the bunker with the speakerphone base station, so she heard it!
    assert any(h.get("text") == "alert to all stations" for h in getattr(cara, "recent_hearing", []))
