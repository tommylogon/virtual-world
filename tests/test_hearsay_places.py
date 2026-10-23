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
