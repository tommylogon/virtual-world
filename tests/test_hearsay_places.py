"""Spoken directions teach places (task-467).

Hearsay is the dialogue twin of a charted map: a place named as a direction
enters the listener's ``known`` store, so a belief can become a route. Merely
naming the place is not enough - the line has to say where it is.
"""
from collections import deque
from unittest.mock import MagicMock

from graph import Node, WorldGraph
from player import Player
from engine.speech import SpeechBroadcaster


def _world():
    jake = Player("jake")
    rosa = Player("rosa")
    for player in (jake, rosa):
        player.current_area = "Dining Room"
        player.vitals = {"Social": 50}
        player.known = []

    pm = MagicMock()
    pm.players = {"jake": jake, "rosa": rosa}
    pm.get_player = lambda name: pm.players.get(name)
    pm.current_area = MagicMock()
    pm.current_area.name = "Dining Room"
    pm._player_node_id = lambda name: f"player_{name}"

    logs = MagicMock()
    logs.speech_log = deque()
    logs.add_log_entry = MagicMock()
    logs.record_turn_event = MagicMock()

    graph = WorldGraph()
    graph.add_node(Node(id="area_dining_room", type="area", name="Dining Room",
                        properties={}))
    graph.add_node(Node(id="area_old_mill", type="area", name="Old Mill",
                        properties={}))

    broadcaster = SpeechBroadcaster(
        graph=graph, player_manager=pm,
        logging_events=logs, npc_behaviors=None, name_matcher=None,
    )
    return jake, rosa, broadcaster


def test_a_spoken_direction_teaches_the_named_place():
    jake, rosa, broadcaster = _world()

    broadcaster.broadcast_speech("rosa", "go west to the Old Mill")

    assert "Old Mill" in jake.known
    assert "area_old_mill" in jake.known, "the id the perception gate matches"


def test_an_idle_mention_does_not_teach_the_place():
    jake, rosa, broadcaster = _world()

    broadcaster.broadcast_speech("rosa", "I like the Old Mill")

    assert "Old Mill" not in jake.known, (
        "hearsay teaches a direction, not every place a conversation names"
    )


def test_the_speaker_is_not_taught_by_their_own_direction():
    jake, rosa, broadcaster = _world()

    broadcaster.broadcast_speech("rosa", "go west to the Old Mill")

    assert "Old Mill" not in rosa.known


def test_directed_whisper_teaches_only_the_whisper_recipient():
    jake, rosa, broadcaster = _world()
    bystander = Player("terry")
    bystander.current_area = "Dining Room"
    bystander.vitals = {"Social": 50}
    bystander.known = []
    broadcaster.player_manager.players["terry"] = bystander

    broadcaster.broadcast_speech(
        "rosa", "go west to the Old Mill",
        speech_level="whisper", whisper_target="jake",
    )

    assert "Old Mill" in jake.known
    assert "area_old_mill" in jake.known
    assert "Old Mill" not in bystander.known, (
        "a stranger bystander does not hear a directed whisper or learn its place"
    )


def test_map_and_reveal_upgrade_only_matching_place_beliefs():
    from engine.fog import Known, teach_from_map

    jake, _rosa, broadcaster = _world()
    broadcaster.graph.add_node(
        Node(id="area_south_gate", type="area", name="South Gate", properties={})
    )
    jake.memories = [
        {"type": "belief", "text": "The Old Mill lies west of the camp.", "confidence": 0.5},
        {"type": "belief", "text": "The South Gate is guarded at night.", "confidence": 0.4},
    ]

    map_node = Node(
        id="item_map", type="item", name="Rough Map",
        properties={"charted_areas": ["Old Mill"]},
    )
    taught = teach_from_map(jake, map_node, graph=broadcaster.graph)

    assert "Old Mill" in taught["taught"]
    assert "area_old_mill" in taught["taught"]
    assert "South Gate" not in taught["taught"]
    assert jake.memories[0].get("upgraded_to_known") == "Old Mill"
    assert jake.memories[0]["confidence"] == 1.0
    assert jake.memories[1].get("upgraded_to_known") is None
    assert jake.memories[1]["confidence"] == 0.4

    Known(jake).reveal("area_south_gate", "South Gate")
    assert jake.memories[1].get("upgraded_to_known") == "South Gate"
    assert jake.memories[1]["confidence"] == 1.0


def test_belief_travel_follows_believed_heading_and_records_arrival_outcome():
    from engine.timeskip import resolve_belief_destination, _record_belief_arrival

    jake, _rosa, broadcaster = _world()
    jake.memories = [
        {"type": "belief", "text": "I heard the Old Mill is west along the trail."},
        {"type": "belief", "text": "People say Phantom Keep lies east past the ridge."},
    ]

    gs = MagicMock()
    gs.graph = broadcaster.graph
    gs.time_ticks = 12

    info_mill = resolve_belief_destination(gs, jake, "Old Mill")
    assert info_mill["target"] == "Old Mill"
    assert info_mill["heading"] == "west"
    assert info_mill["known"] is False

    # Arrive at Old Mill -> records "found" under BELIEF
    jake.current_area = "Old Mill"
    outcome = _record_belief_arrival(gs, jake, "Old Mill", info_mill)
    assert outcome == "found"
    found_mem = [m for m in jake.memories if m.get("outcome") == "found"]
    assert len(found_mem) == 1
    assert found_mem[0]["type"] == "belief"
    assert "Belief confirmed (found)" in found_mem[0]["text"]
    assert info_mill["belief"]["validated"] == "found"
    assert info_mill["belief"]["confidence"] == 1.0

    # Fail to find Phantom Keep -> records "found-not-there" under BELIEF
    info_keep = resolve_belief_destination(gs, jake, "Phantom Keep")
    assert info_keep["target"] == "Phantom Keep"
    assert info_keep["heading"] == "east"

    outcome_keep = _record_belief_arrival(gs, jake, "Phantom Keep", info_keep)
    assert outcome_keep == "found-not-there"
    missing_mem = [m for m in jake.memories if m.get("outcome") == "found-not-there"]
    assert len(missing_mem) == 1
    assert missing_mem[0]["type"] == "belief"
    assert "not there" in missing_mem[0]["text"]
    assert info_keep["belief"]["validated"] == "found-not-there"
    assert info_keep["belief"]["confidence"] == 0.1


def test_frontier_discovery_generates_content_and_reveals_for_discoverer_only():
    from engine.fog import materialize_frontier

    jake, rosa, broadcaster = _world()
    gs = MagicMock()
    gs.graph = broadcaster.graph
    gs.time_ticks = 5
    gs.world_scopes = {
        "apt_3b": {
            "id": "apt_3b",
            "name": "Apartment 3B",
            "kind": "scope",
            "state": "unmade",
            "recipe": "apartment.v1",
            "seed": "frontier-seed-3b",
            "entry_area_id": "area_dining_room",
            "area_ids": [],
        }
    }

    created = materialize_frontier(gs, jake, "Dining Room")
    assert "area_apt_3b_living" in created
    assert gs.world_scopes["apt_3b"]["state"] == "materialized"
    assert gs.graph.get_node("area_apt_3b_living") is not None
    assert gs.graph.get_node("way_apt_3b_front_door") is not None

    # Revealed for Jake (the discoverer), not for Rosa
    assert "area_apt_3b_living" in jake.known
    assert "area_apt_3b_living" not in rosa.known


def test_timeskip_http_route_supports_belief_travel_without_explicit_minutes():
    from app import create_app

    app = create_app({"TESTING": True})
    w = app.world
    w.time_per_tick_minutes = 1
    p = w.get_active_player_obj() or next(iter(w.players.values()))
    for other in w.players.values():
        if other is not p:
            other.autonomy = True
    p.vitals.update({
        "HP": 100, "Thirst": 0, "Hunger": 0, "Bladder": 0,
        "Energy": 100, "Hygiene": 100, "Sanity": 100,
        "Social": 100, "Entertainment": 100,
    })
    p.conditions.clear()
    p.state = "idle"
    bearing = "east"
    for name in sorted(getattr(w, "areas", {}) or {}):
        exits = w.build_exits_for_area(name) or {}
        found = False
        for b in ("west", "east", "north", "south"):
            if any(b in str(k).lower() for k in exits):
                w.set_player_area(p.name, name)
                p.current_area = name
                bearing = b
                found = True
                break
        if found:
            break
    p.memories.append({
        "type": "belief",
        "place": "Phantom Keep",
        "direction": bearing,
        "text": f"Heard: Phantom Keep lies {bearing}",
        "confidence": 0.6,
    })

    client = app.test_client()
    res = client.post("/api/world/timeskip", json={
        "intent": "travel",
        "target": "Phantom Keep",
    })
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert body["ok"] is True
    assert body["elapsed_minutes"] >= 1
    assert any(m.get("outcome") in ("found", "found-not-there") for m in p.memories)




