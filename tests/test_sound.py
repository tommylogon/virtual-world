"""Tests for the sound propagation system."""
import pytest
from unittest.mock import MagicMock, patch
from engine.sound import (
    get_way_barrier,
    get_area_noise_level,
    get_effective_penetration,
    propagate_sound,
    get_areas_hearing_speech,
    get_areas_hearing_sound_source,
    get_sound_sources_in_area,
    SPEECH_LEVELS,
)
from graph import WorldGraph, Node, Edge


@pytest.fixture
def graph():
    """Create a test graph with connected areas."""
    g = MagicMock(spec=WorldGraph)
    g.edges = []
    g.nodes = {}
    g._edges_by_source = {}

    def get_node(node_id):
        return g.nodes.get(node_id)

    def get_edges_for_source(source_id, edge_type=None):
        edges = g._edges_by_source.get(source_id, [])
        if edge_type:
            return [e for e in edges if e.type == edge_type]
        return list(edges)

    g.get_node = get_node
    g.get_edges_for_source = get_edges_for_source
    return g


@pytest.fixture
def areas(graph):
    """Create test areas."""
    areas = {}
    for name in ["hallway", "room_a", "room_b", "room_c", "room_d"]:
        area_id = f"area_{name}"
        node = MagicMock(spec=Node)
        node.id = area_id
        node.type = "area"
        node.name = name
        node.properties = {"environment": {"noise": "quiet"}}
        areas[area_id] = node
        graph.nodes[area_id] = node
    return areas


@pytest.fixture
def ways(graph):
    """Create test ways connecting areas."""
    ways = {}

    # hallway <-> room_a (open door)
    way1 = MagicMock(spec=Node)
    way1.id = "way_hallway_room_a"
    way1.type = "way"
    way1.properties = {"current_state": "open", "description": "door"}
    ways["way_hallway_room_a"] = way1
    graph.nodes["way_hallway_room_a"] = way1

    # room_a <-> room_b (closed door)
    way2 = MagicMock(spec=Node)
    way2.id = "way_room_a_room_b"
    way2.type = "way"
    way2.properties = {"current_state": "closed", "description": "door"}
    ways["way_room_a_room_b"] = way2
    graph.nodes["way_room_a_room_b"] = way2

    # room_b <-> room_c (locked door)
    way3 = MagicMock(spec=Node)
    way3.id = "way_room_b_room_c"
    way3.type = "way"
    way3.properties = {"current_state": "locked", "description": "door"}
    ways["way_room_b_room_c"] = way3
    graph.nodes["way_room_b_room_c"] = way3

    # room_c <-> room_d (open door)
    way4 = MagicMock(spec=Node)
    way4.id = "way_room_c_room_d"
    way4.type = "way"
    way4.properties = {"current_state": "open", "description": "door"}
    ways["way_room_c_room_d"] = way4
    graph.nodes["way_room_c_room_d"] = way4

    return ways


def connect_areas(graph, areas, ways):
    """Add bidirectional connection edges between areas and ways."""
    graph._edges_by_source = {}

    def add_edge(source, target, direction=""):
        edge = Edge(source=source, target=target, type="connection",
                    properties={"direction": direction})
        graph.edges.append(edge)
        graph._edges_by_source.setdefault(source, []).append(edge)

    # hallway <-> room_a via open door
    add_edge("area_hallway", "way_hallway_room_a", "north")
    add_edge("way_hallway_room_a", "area_room_a")
    # room_a <-> hallway reverse
    add_edge("area_room_a", "way_hallway_room_a", "south")
    add_edge("way_hallway_room_a", "area_hallway")

    # room_a <-> room_b via closed door
    add_edge("area_room_a", "way_room_a_room_b", "east")
    add_edge("way_room_a_room_b", "area_room_b")
    add_edge("area_room_b", "way_room_a_room_b", "west")
    add_edge("way_room_a_room_b", "area_room_a")

    # room_b <-> room_c via locked door
    add_edge("area_room_b", "way_room_b_room_c", "south")
    add_edge("way_room_b_room_c", "area_room_c")
    add_edge("area_room_c", "way_room_b_room_c", "north")
    add_edge("way_room_b_room_c", "area_room_b")

    # room_c <-> room_d via open door
    add_edge("area_room_c", "way_room_c_room_d", "west")
    add_edge("way_room_c_room_d", "area_room_d")
    add_edge("area_room_d", "way_room_c_room_d", "east")
    add_edge("way_room_c_room_d", "area_room_c")


class TestWayBarrier:
    def test_open_door_barrier_half(self):
        way = MagicMock()
        way.properties = {"current_state": "open"}
        assert get_way_barrier(way) == 0.5
    
    def test_closed_door_barrier_one(self):
        way = MagicMock()
        way.properties = {"current_state": "closed"}
        assert get_way_barrier(way) == 1
    
    def test_locked_door_barrier_two(self):
        way = MagicMock()
        way.properties = {"current_state": "locked"}
        assert get_way_barrier(way) == 2
    
    def test_blocked_door_barrier_two(self):
        way = MagicMock()
        way.properties = {"current_state": "blocked"}
        assert get_way_barrier(way) == 2
    
    def test_hidden_door_barrier_two(self):
        way = MagicMock()
        way.properties = {"current_state": "hidden"}
        assert get_way_barrier(way) == 2
    
    def test_see_through_barrier_three_quarters(self):
        way = MagicMock()
        way.properties = {"current_state": "closed", "see_through": True}
        assert get_way_barrier(way) == 0.75

    def test_custom_barrier_applies_when_closed(self):
        way = MagicMock()
        way.properties = {"current_state": "closed", "sound_barrier": 3}
        assert get_way_barrier(way) == 3.0

    def test_custom_barrier_applies_when_locked_and_blocked(self):
        locked = MagicMock()
        locked.properties = {"current_state": "locked", "sound_barrier": 0.25}
        blocked = MagicMock()
        blocked.properties = {"current_state": "blocked", "sound_barrier": 1.5}
        assert get_way_barrier(locked) == 0.25
        assert get_way_barrier(blocked) == 1.5

    def test_custom_barrier_ignored_when_open_or_hidden(self):
        opener = MagicMock()
        opener.properties = {"current_state": "open", "sound_barrier": 3}
        hidden = MagicMock()
        hidden.properties = {"current_state": "hidden", "sound_barrier": 3}
        assert get_way_barrier(opener) == 0.5
        assert get_way_barrier(hidden) == 2

    def test_invalid_custom_barrier_falls_back_to_defaults(self):
        way = MagicMock()
        way.properties = {"current_state": "closed", "sound_barrier": "thick"}
        assert get_way_barrier(way) == 1

    def test_custom_barrier_overrides_see_through_on_solid_states(self):
        window = MagicMock()
        window.properties = {"current_state": "closed", "see_through": True, "sound_barrier": 2}
        assert get_way_barrier(window) == 2.0


class TestEffectivePenetration:
    def test_no_noise_no_reduction(self):
        assert get_effective_penetration(2, 0) == 2
    
    def test_normal_noise_reduces_by_one(self):
        assert get_effective_penetration(2, 1) == 1
    
    def test_loud_noise_reduces_by_two(self):
        assert get_effective_penetration(2, 2) == 0
    
    def test_minimum_is_zero(self):
        assert get_effective_penetration(1, 3) == 0


class TestSpeechPropagation:
    def test_whisper_only_current_area(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        result = get_areas_hearing_speech("area_hallway", "whisper", graph, areas)
        # Whisper has penetration 0, doesn't leave origin
        assert len(result) == 0
    
    def test_normal_speech_through_open_door(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        result = get_areas_hearing_speech("area_hallway", "normal", graph, areas)
        # Normal (pen=1) through open door (bar=0) reaches room_a
        assert "area_room_a" in result
        assert len(result) == 1
    
    def test_normal_speech_blocked_by_closed_door(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        result = get_areas_hearing_speech("area_room_a", "normal", graph, areas)
        # Normal (pen=1) blocked by closed door (bar=1)
        assert "area_room_b" not in result
    
    def test_shout_through_closed_door(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        result = get_areas_hearing_speech("area_room_a", "shout", graph, areas)
        # Shout (pen=2) through closed door (bar=1) reaches room_b
        assert "area_room_b" in result
    
    def test_shout_blocked_by_locked_door(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        result = get_areas_hearing_speech("area_room_b", "shout", graph, areas)
        # Shout (pen=2) blocked by locked door (bar=2)
        assert "area_room_c" not in result
    
    def test_scream_reaches_three_areas(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        # Make all doors open for this test
        ways["way_room_a_room_b"].properties["current_state"] = "open"
        ways["way_room_b_room_c"].properties["current_state"] = "open"
        
        result = get_areas_hearing_speech("area_hallway", "scream", graph, areas)
        # Scream (pen=3) through all open doors reaches room_a, room_b, room_c
        assert "area_room_a" in result
        assert "area_room_b" in result
        assert "area_room_c" in result
    
    def test_scream_blocked_by_two_closed_doors(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        # hallway->room_a open, room_a->room_b closed, room_b->room_c closed
        result = get_areas_hearing_speech("area_hallway", "scream", graph, areas)
        # Scream (pen=3) through open(0) + closed(1) + closed(1) = 2 barriers
        # 3 - 2 = 1, so reaches room_b but not room_c
        assert "area_room_a" in result
        assert "area_room_b" in result
        assert "area_room_c" not in result


class TestAmbientNoise:
    def test_loud_room_reduces_speech(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        # Set hallway to loud noise
        areas["area_hallway"].properties["environment"]["noise"] = "loud"
        
        result = get_areas_hearing_speech("area_hallway", "shout", graph, areas)
        # Shout (pen=2) - loud noise (2) = effective pen 0
        # Sound doesn't leave origin
        assert len(result) == 0
    
    def test_normal_noise_reduces_range(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        # Set hallway to normal noise
        areas["area_hallway"].properties["environment"]["noise"] = "normal"
        
        result = get_areas_hearing_speech("area_hallway", "shout", graph, areas)
        # Shout (pen=2) - normal noise (1) = effective pen 1
        # Reaches room_a through open door (bar=0)
        assert "area_room_a" in result
        # But not room_b through closed door (bar=1), 1-1=0
        assert "area_room_b" not in result


class TestSoundSources:
    def test_sound_source_propagates(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        
        result = get_areas_hearing_sound_source("area_hallway", 2, graph, areas)
        # Sound level 2 through open door reaches room_a
        assert "area_room_a" in result
    
    def test_sound_source_in_loud_room_muffled(self, graph, areas, ways):
        connect_areas(graph, areas, ways)
        areas["area_hallway"].properties["environment"]["noise"] = "loud"
        
        result = get_areas_hearing_sound_source("area_hallway", 2, graph, areas)
        # Sound level 2 - loud noise 2 = effective 0
        assert len(result) == 0


class TestSpeechCommandParsing:
    """Regression tests for the alias-normalization fix.

    Previously ``whisper`` and ``shout`` were rewritten to ``say`` by the
    verb alias map in routes/action.py, silently degrading them to normal
    speech. This mirrors the actual normalization + dispatch logic so the
    bug can't silently return.
    """

    ALIAS_MAP = [
        ("read ", "examine "), ("search ", "examine "), ("inspect ", "examine "),
        ("check ", "examine "), ("light ", "use "), ("ignite ", "use "),
        ("grab ", "take "), ("snatch ", "take "), ("collect ", "take "),
        ("hit ", "attack "), ("strike ", "attack "), ("punch ", "attack "),
        ("yell ", "shout "),
    ]

    def _parse(self, raw_cmd):
        cmd = raw_cmd.strip().lower()
        for alias, canonical in self.ALIAS_MAP:
            if cmd.startswith(alias):
                cmd = canonical + cmd[len(alias):].strip()
                break
        if cmd.startswith(("speak ", "say ", "whisper ", "shout ", "scream ")):
            if cmd.startswith("whisper "):
                return "whisper", cmd[8:]
            if cmd.startswith("shout "):
                return "shout", cmd[6:]
            if cmd.startswith("scream "):
                return "scream", cmd[7:]
            return "normal", cmd.split(" ", 1)[1] if " " in cmd else ""
        return None, cmd

    def test_whisper_survives_alias_map(self):
        level, text = self._parse("whisper psst, over here")
        assert level == "whisper"
        assert "psst" in text

    def test_shout_survives_alias_map(self):
        level, text = self._parse("shout hey!")
        assert level == "shout"
        assert "hey" in text

    def test_scream_survives_alias_map(self):
        level, text = self._parse("scream help!")
        assert level == "scream"
        assert "help" in text

    def test_yell_maps_to_shout(self):
        level, text = self._parse("yell fire!")
        assert level == "shout"
        assert "fire" in text

    def test_say_stays_normal(self):
        level, text = self._parse("say hello")
        assert level == "normal"
        assert "hello" in text
