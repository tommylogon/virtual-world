"""Tests for spoken-name learning (task-339 design).

The decided mechanic: a name spoken aloud in earshot teaches that name
(self-intros, direct address, third-party mentions — all one mechanism).
Sight is recognition only and NEVER reveals a name. Examine masks an
unmet character's name unless they wear a 'nametag'-tagged item.
"""
import pytest
from collections import deque
from unittest.mock import MagicMock

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_EQUIPPED
from player import Player
from engine.speech import SpeechBroadcaster
from engine.scene_snapshot import build_scene


def make_world():
    """jake + rosa + tyler in one area; jake knows nobody's name."""
    jake = Player("jake halloway")
    rosa = Player("rosa")
    tyler = Player("tyler")
    for p in (jake, rosa, tyler):
        p.current_area = "Dining Room"
        p.vitals = {"Social": 50}

    pm = MagicMock()
    pm.players = {"jake halloway": jake, "rosa": rosa, "tyler": tyler}
    pm.get_player = lambda name: pm.players.get(name)
    pm.current_area = MagicMock()
    pm.current_area.name = "Dining Room"
    pm._player_node_id = lambda name: f"player_{name.replace(' ', '_')}"

    logs = MagicMock()
    logs.speech_log = deque()
    logs.add_log_entry = MagicMock()
    logs.record_turn_event = MagicMock()

    broadcaster = SpeechBroadcaster(
        graph=None, player_manager=pm,
        logging_events=logs, npc_behaviors=None, name_matcher=None,
    )
    return jake, rosa, tyler, pm, broadcaster


def test_self_introduction_teaches_the_name():
    jake, rosa, tyler, pm, broadcaster = make_world()
    broadcaster.broadcast_speech("rosa", "hi, I'm rosa — what can I get you?")
    assert jake.knows_name("rosa") is True
    assert jake.has_met("rosa") is True


def test_third_party_mention_teaches_the_name():
    jake, rosa, tyler, pm, broadcaster = make_world()
    broadcaster.broadcast_speech("tyler", "order up for rosa!")
    assert jake.knows_name("rosa") is True


def test_speech_without_names_teaches_nothing():
    jake, rosa, tyler, pm, broadcaster = make_world()
    broadcaster.broadcast_speech("rosa", "the drive-thru is closed, sorry.")
    assert jake.knows_name("rosa") is False
    assert jake.knows_name("tyler") is False


def test_learning_is_logged_once_and_idempotent():
    jake, rosa, tyler, pm, broadcaster = make_world()
    broadcaster.broadcast_speech("rosa", "hi, I'm rosa.")
    broadcaster.broadcast_speech("rosa", "rosa again — anything else?")
    # second mention must not re-teach: only one learning log for jake
    learned_logs = [c for c in broadcaster.logging_events.add_log_entry.call_args_list
                    if "learns" in str(c) and "[jake halloway]" in str(c)]
    assert len(learned_logs) == 1
    assert jake.knows_name("rosa") is True


def test_speaker_does_not_learn_own_name():
    jake, rosa, tyler, pm, broadcaster = make_world()
    broadcaster.broadcast_speech("rosa", "rosa here, folks.")
    assert rosa.knows_name("rosa") is False


def test_scene_never_reveals_name_by_re_sighting():
    jake, rosa, tyler, pm, broadcaster = make_world()
    w = MagicMock()
    w.graph = WorldGraph()
    area = Node(id="area_dining_room", type="area", name="Dining Room",
                properties={"environment": {"light": 80}})
    w.graph.add_node(area)
    rosa_node = Node(id="player_rosa", type="character", name="rosa",
                     properties={"description": "Visor fringe, pen behind one ear.",
                                 "tags": ["female"]})
    w.graph.add_node(rosa_node)
    w.graph.add_edge(Edge(source="player_rosa", target="area_dining_room", type=EDGE_IN))
    w.player_manager = pm
    w.player_manager.area_node_id = lambda n: f"area_{n.lower().replace(' ', '_')}"
    w.lighting.get_ambient_light = MagicMock(return_value=90)
    ad = MagicMock()
    ad._render_node = MagicMock(side_effect=lambda n: n.properties.get("description", ""))
    w.area_description = ad
    w._get_available_actions = MagicMock(return_value=[])

    jake.current_area = "Dining Room"
    scene1 = build_scene(w, "jake halloway")
    scene2 = build_scene(w, "jake halloway")  # re-sight changes nothing
    person1 = next(p for p in scene1["people"] if p["id"] == "player_rosa")
    person2 = next(p for p in scene2["people"] if p["id"] == "player_rosa")
    assert person1["name"] is None
    assert person2["name"] is None
    assert person2["met"] is True  # recognized, still unnamed

    # hearing the name flips it
    broadcaster.broadcast_speech("tyler", "rosa! order up!")
    scene3 = build_scene(w, "jake halloway")
    person3 = next(p for p in scene3["people"] if p["id"] == "player_rosa")
    assert person3["name"] == "rosa"
    assert person3["display_name"] == "rosa"


def _examine_mixin_with(graph, pm):
    from engine.items.examine_actions import ExamineActionsMixin
    mixin = ExamineActionsMixin.__new__(ExamineActionsMixin)
    mixin.graph = graph
    mixin.matching = MagicMock()
    mixin.matching._match_item_name = MagicMock(return_value=None)
    mixin.matching._match_character_name = MagicMock(return_value=(None, []))
    mixin.matching.resolve_exit = MagicMock(return_value=(None, None, ""))
    mixin.trigger_system = MagicMock()
    mixin.trigger_system._execute_triggers = MagicMock(return_value=[])
    mixin._exec_triggers = MagicMock(return_value=[])
    mixin.equipment = MagicMock()
    mixin.equipment.get_equipment_narrative = MagicMock(return_value="")
    mixin.lighting = None
    return mixin


def test_examine_masks_unmet_name():
    g = WorldGraph()
    area = Node(id="area_dining", type="area", name="Dining Room", properties={})
    g.add_node(area)

    jake = Player("jake halloway")
    rosa = Player("rosa")
    rosa.description = "rosa smiles shyly."
    pm = MagicMock()
    pm.players = {"jake halloway": jake, "rosa": rosa}
    pm.active_player = "jake halloway"
    pm.lighting = MagicMock()
    pm.lighting.can_see_in_dark = MagicMock(return_value=True)
    pm.lighting.get_ambient_light = MagicMock(return_value=80)
    pm._get_current_area_id = lambda: "area_dining"
    pm._player_node_id = lambda name: f"player_{name.replace(' ', '_')}"
    pm.current_area = MagicMock()
    pm.current_area.name = "Dining Room"

    mixin = _examine_mixin_with(g, pm)
    # resolve via description tier: mock matcher returns rosa
    mixin.matching._match_character_name = MagicMock(return_value=("rosa", []))
    desc = mixin.get_item_desc(pm, "the woman behind the counter")
    assert "rosa" not in desc.lower()
    assert "smiles shyly" in desc


def test_examine_nametag_reveals_name():
    g = WorldGraph()
    area = Node(id="area_dining", type="area", name="Dining Room", properties={})
    g.add_node(area)
    tag = Node(id="item_nametag", type="item", name="Name Tag",
               properties={"tags": ["nametag"], "current_state": "normal"})
    g.add_node(tag)
    g.add_edge(Edge(source="item_nametag", target="player_rosa", type=EDGE_EQUIPPED,
                    properties={"slot": "chest"}))

    jake = Player("jake halloway")
    rosa = Player("rosa")
    rosa.description = "She smiles shyly."
    pm = MagicMock()
    pm.players = {"jake halloway": jake, "rosa": rosa}
    pm.active_player = "jake halloway"
    pm.lighting = MagicMock()
    pm.lighting.can_see_in_dark = MagicMock(return_value=True)
    pm.lighting.get_ambient_light = MagicMock(return_value=80)
    pm._get_current_area_id = lambda: "area_dining"
    pm._player_node_id = lambda name: f"player_{name.replace(' ', '_')}"
    pm.current_area = MagicMock()
    pm.current_area.name = "Dining Room"

    mixin = _examine_mixin_with(g, pm)
    mixin.matching._match_character_name = MagicMock(return_value=("rosa", []))
    desc = mixin.get_item_desc(pm, "the woman behind the counter")
    assert 'A name tag reads "rosa"' in desc
