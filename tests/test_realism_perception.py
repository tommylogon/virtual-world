"""Tests for realism/perception work: time-of-day outdoor lighting (task-230),
light-flavored descriptions (task-133), directed whispers (task-248), and
closeness behavioral hooks (task-94)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import WorldGraph, Node, Edge, EDGE_IN
from engine.lighting import LightingSystem, outdoor_light_for_hour
from virtual_world_engine import VirtualWorld
from player import Player


# ─────────────────── task-230: outdoor light curve ───────────────────


class TestOutdoorLightCurve:
    """The time-of-day interpolation curve."""

    def test_deep_night_is_dark(self):
        assert outdoor_light_for_hour(0) <= 10
        assert outdoor_light_for_hour(2) <= 10
        assert outdoor_light_for_hour(23) <= 10

    def test_full_day_is_bright(self):
        assert outdoor_light_for_hour(12) >= 80
        assert outdoor_light_for_hour(15) >= 80

    def test_dawn_ramps_up(self):
        """Light at 8am is between night and full day."""
        assert 30 <= outdoor_light_for_hour(8) <= 85
        assert outdoor_light_for_hour(8) < outdoor_light_for_hour(12)

    def test_dusk_ramps_down(self):
        """Evening dims monotonically toward night."""
        assert outdoor_light_for_hour(18) > outdoor_light_for_hour(20)
        assert outdoor_light_for_hour(20) > outdoor_light_for_hour(22)

    def test_hour_clamping(self):
        assert outdoor_light_for_hour(-5) == outdoor_light_for_hour(0)
        assert outdoor_light_for_hour(99) == outdoor_light_for_hour(23)


class TestTimeOfDayOutdoorLighting:
    """Outdoor areas follow the clock; indoor areas do not."""

    def _graph_with(self, tags, env=None):
        graph = WorldGraph()
        properties = {"tags": tags}
        if env is not None:
            properties["environment"] = env
        graph.add_node(Node(id="area_A", type="area", name="A", properties=properties))
        return graph

    def test_outdoor_area_darkens_at_night(self):
        graph = self._graph_with(["outdoor"])
        lighting = LightingSystem(graph)
        lighting.hour_provider = lambda: 0
        assert lighting.get_ambient_light("area_A") <= 15

    def test_outdoor_area_bright_at_noon(self):
        graph = self._graph_with(["outdoor"])
        lighting = LightingSystem(graph)
        lighting.hour_provider = lambda: 12
        assert lighting.get_ambient_light("area_A") >= 80

    def test_indoor_area_ignores_clock(self):
        graph = self._graph_with([])
        lighting = LightingSystem(graph)
        lighting.hour_provider = lambda: 0
        assert lighting.get_ambient_light("area_A") == 80

    def test_no_hour_provider_keeps_static_behavior(self):
        graph = self._graph_with(["outdoor"])
        lighting = LightingSystem(graph)
        assert lighting.get_ambient_light("area_A") == 80

    def test_explicit_light_is_floor_not_ceiling(self):
        """A magically lit outdoor glade stays bright at midnight."""
        graph = self._graph_with(["outdoor"], env={"light": 70})
        lighting = LightingSystem(graph)
        lighting.hour_provider = lambda: 0
        assert lighting.get_ambient_light("area_A") == 70

    def test_engine_current_game_hour(self):
        """The facade computes hour from ticks + clock start."""
        world = VirtualWorld()
        world.time_ticks = 0
        world.clock_start_hour = 23
        world.clock_start_minute = 30
        world.time_per_tick_minutes = 60
        assert world.current_game_hour() == 23
        world.time_ticks = 1
        assert world.current_game_hour() == 0


# ─────────────────── task-248: directed whispers ───────────────────


class TestDirectedWhisper:
    """A whisper with a target reaches only that target; the room sees a gesture."""

    def _world_with_three(self):
        world = VirtualWorld()
        speaker = world.player_manager.get_player(world.active_player)
        world.set_player_area(speaker.name, "foyer")
        listener = Player("Listener")
        world.add_player(listener)
        world.set_player_area("Listener", "foyer")
        bystander = Player("Bystander")
        world.add_player(bystander)
        world.set_player_area("Bystander", "foyer")
        return world, speaker, listener, bystander

    def test_only_target_hears_content(self):
        world, speaker, listener, bystander = self._world_with_three()
        world.broadcast_speech(speaker.name, "the password is bread",
                               speech_level="whisper", whisper_target="Listener")
        heard = [h["text"] for h in listener.recent_hearing]
        assert any("bread" in text for text in heard)
        bystander_heard = [h["text"] for h in bystander.recent_hearing]
        assert not any("bread" in text for text in bystander_heard)

    def test_bystanders_see_gesture_turn_event(self):
        world, speaker, listener, bystander = self._world_with_three()
        world.broadcast_speech(speaker.name, "the password is bread",
                               speech_level="whisper", whisper_target="Listener")
        gestures = [evt for evt in world.turn_events
                    if evt.get("actor") == speaker.name and "whispers something to" in evt.get("description", "")]
        assert gestures, "Expected a content-free gesture turn event"
        # The gesture event must NOT carry the words
        assert "bread" not in gestures[0]["description"]

    def test_undirected_whisper_still_room_wide(self):
        world, speaker, listener, bystander = self._world_with_three()
        world.broadcast_speech(speaker.name, "nice weather", speech_level="whisper")
        assert any("nice weather" in h["text"] for h in listener.recent_hearing)
        assert any("nice weather" in h["text"] for h in bystander.recent_hearing)

    def test_whisper_to_absent_target_is_room_wide(self):
        """A whisper naming nobody present falls back to normal room whisper."""
        world, speaker, listener, bystander = self._world_with_three()
        world.broadcast_speech(speaker.name, "anyone there?",
                               speech_level="whisper", whisper_target="Nobody Here")
        assert any("anyone there?" in h["text"] for h in listener.recent_hearing)
        assert any("anyone there?" in h["text"] for h in bystander.recent_hearing)


# ─────────────────── task-94: closeness hooks ───────────────────


class TestClosenessHooks:
    """Interactions move closeness, not just decorate it."""

    def _two_in_area(self):
        world = VirtualWorld()
        speaker = world.player_manager.get_player(world.active_player)
        world.set_player_area(speaker.name, "foyer")
        listener = Player("Listener")
        world.add_player(listener)
        world.set_player_area("Listener", "foyer")
        return world, speaker, listener

    def test_directed_whisper_warms_both_parties(self):
        world, speaker, listener = self._two_in_area()
        world.broadcast_speech(speaker.name, "psst, over here",
                               speech_level="whisper", whisper_target="Listener")
        assert speaker.relationships["Listener"]["closeness"] == 2
        assert listener.relationships[speaker.name]["closeness"] == 2

    def test_room_whisper_does_not_move_closeness(self):
        world, speaker, listener = self._two_in_area()
        world.broadcast_speech(speaker.name, "nice weather", speech_level="whisper")
        assert "Listener" not in speaker.relationships
        assert speaker.name not in listener.relationships
