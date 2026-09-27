"""Weather, wind and daylight are narrated (task-559).

Before this task `env["weather"]` was mechanically live but perceptually
invisible: a character standing in a thunderstorm got a temperature sentence and
a light level, and not one word about the rain. The moon was worse — the block
that narrates it raised ``UnboundLocalError`` on its first line (it read a
local ``node`` assigned later in the same method) and a bare
``except Exception: pass`` swallowed the failure, so the moon has never been
narrated anywhere.

These tests pin the prose, the outdoor gate, the de-duplication, and the moon
regression.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import MagicMock

from graph import WorldGraph, Node
from player import Player
from engine.player_manager import PlayerManager
from engine.area_description import (
    AreaDescription, WIND_PROSE, WEATHER_PROSE, _is_open_sky,
    time_of_day_prose, weather_description,
)
from engine.weather_forecast import (
    WEATHER_STATES, WEATHER_TIME_DC, WIND_STATES, normalize_weather,
)


class PM(PlayerManager):
    """PlayerManager plus the node-id helpers AreaDescription expects."""

    def player_node_id(self, name):
        return self.get_player_node_id(name)

    def area_node_id(self, name):
        return f"area_{name.lower()}".replace(' ', '_')

    def apply_action(self, action_name, player=None):
        return None


def _world(tags=("outdoor", "exterior"), env=None, hour=12, moon=None):
    """A one-area world with the given tags, environment, hour and moon."""
    graph = WorldGraph()
    environment = {"light": 80, "temperature": 12, "air": "fresh",
                   "smell": "neutral", "noise": "quiet"}
    environment.update(env or {})
    graph.add_node(Node(id="area_spot", type="area", name="Spot", properties={
        "description": "A flat open place.",
        "tags": list(tags),
        "environment": environment,
    }))

    pm = PM(graph)
    hero = Player("Hero")
    hero.current_area = "Spot"
    pm.add_player(hero)
    pm.set_active_player("Hero")

    lighting = MagicMock()
    lighting.can_see_in_dark = MagicMock(return_value=True)
    lighting.get_ambient_light = MagicMock(return_value=80)
    lighting.light_to_level = MagicMock(return_value="bright")
    lighting.get_light_int = MagicMock(return_value=80)
    lighting.hour_provider = MagicMock(return_value=hour)
    lighting.moon_provider = MagicMock(
        return_value=moon if moon is not None else {"name": "new_moon", "icon": "\U0001F311", "light_bonus": 0})

    return graph, pm, AreaDescription(graph, lighting, pm, MagicMock())


class TestVocabularyStaysInSync:
    def test_every_weather_state_has_prose(self):
        """A forecast may write any value in WEATHER_STATES. A state with no
        sentence is the original bug, so the two lists are pinned together."""
        missing = [s for s in WEATHER_STATES if s not in WEATHER_PROSE]
        assert missing == [], f"weather states with no prose: {missing}"

    def test_every_wind_state_has_prose_or_is_silent(self):
        missing = [s for s in WIND_STATES if s != "none" and s not in WIND_PROSE]
        assert missing == [], f"wind states with no prose: {missing}"

    def test_time_dc_covers_every_weather_state(self):
        """The guess-time DC table moved into weather_forecast so it cannot
        drift from the vocabulary again (task-559)."""
        missing = [s for s in WEATHER_STATES if s not in WEATHER_TIME_DC]
        assert missing == [], f"weather states with no guess-time DC: {missing}"

    def test_normalize_weather_aliases(self):
        assert normalize_weather("overcast") == "cloudy"
        assert normalize_weather("sunny") == "clear"
        assert normalize_weather("  THUNDERSTORM ") == "stormy"
        # Unknown stays unknown so each reader falls through to its own default
        # rather than silently becoming "clear".
        assert normalize_weather("meteor shower") == ""
        assert normalize_weather(None) == ""


class TestOpenSkyGate:
    def test_accepts_either_spelling(self):
        assert _is_open_sky(["outdoor"]) is True
        assert _is_open_sky(["exterior"]) is True
        assert _is_open_sky(["cave", "outdoor"]) is True
        assert _is_open_sky(["cave", "underground"]) is False
        assert _is_open_sky([]) is False
        assert _is_open_sky(None) is False

    def test_comma_string_tags(self):
        assert _is_open_sky("cave, exterior") is True


class TestWeatherDescription:
    def test_rain_and_storm_speak(self):
        assert weather_description("rainy", "", "") != [""]
        lines = weather_description("stormy", "storm", "")
        joined = " ".join(lines)
        assert "rain" in joined and "wind" in joined

    def test_clear_sky_says_nothing(self):
        """A clear sky needs no announcement — it would be noise on every
        outdoor description in the game."""
        assert weather_description("clear", "none", "quiet") == []

    def test_windy_state_defers_to_the_wind_magnitude(self):
        """A gale should not produce two sentences about wind."""
        lines = weather_description("windy", "gale", "quiet")
        assert len(lines) == 1
        assert lines[0] == WIND_PROSE["gale"]

    def test_wind_magnitude_alone_still_speaks(self):
        lines = weather_description("clear", "breeze", "quiet")
        assert lines == [WIND_PROSE["breeze"]]

    def test_authored_noise_windy_is_not_doubled(self):
        """An area whose *noise* is already "windy" must not also get the
        forecast's gale sentence."""
        assert weather_description("clear", "gale", "windy") == []

    def test_unknown_weather_is_silent(self):
        assert weather_description("meteor shower", "none", "quiet") == []


class TestTimeOfDay:
    def test_bands_respect_the_shared_day_boundary(self):
        """The day/night split must stay 05:00 / 19:00 — the same boundary the
        moon text and the guess-time action use."""
        assert "First light" in time_of_day_prose(5)
        assert "sun is down" in time_of_day_prose(19)
        assert "night" in time_of_day_prose(3).lower()
        assert "sun stands high" in time_of_day_prose(12)

    def test_unknown_hour_is_silent(self):
        assert time_of_day_prose(None) == ""
        assert time_of_day_prose("noon") == ""
        assert time_of_day_prose(99) == ""


class TestDescriptionOutput:
    def test_storm_narrated_outdoors(self):
        _, _, desc = _world(env={"weather": "stormy", "wind": "gale"}, hour=15)
        out = desc.get_area_description()
        assert "storm is breaking" in out
        assert WIND_PROSE["gale"] in out

    def test_weather_not_narrated_indoors(self):
        """A storm is not something you hear through a stone wall."""
        _, _, desc = _world(tags=("underground",), env={"weather": "stormy", "wind": "gale"}, hour=15)
        out = desc.get_area_description()
        assert "storm is breaking" not in out
        assert "sun stands high" not in out

    def test_exterior_spelling_also_gets_the_sky(self):
        _, _, desc = _world(tags=("exterior",), env={"weather": "foggy"}, hour=15)
        assert "Fog has swallowed" in desc.get_area_description()

    def test_time_of_day_appears_outdoors(self):
        _, _, desc = _world(hour=6)
        assert "First light" in desc.get_area_description()

    def test_overcast_alias_is_narrated(self):
        _, _, desc = _world(env={"weather": "overcast"}, hour=12)
        assert "flat grey lid" in desc.get_area_description()


class TestMoonRegression:
    """The moon block read an undefined local `node` and the resulting
    UnboundLocalError was swallowed by a bare except, so it never ran."""

    def test_full_moon_narrated_at_night(self):
        _, _, desc = _world(
            hour=22,
            moon={"name": "full_moon", "icon": "\U0001F315", "light_bonus": 25},
        )
        out = desc.get_area_description()
        assert "full moon hangs bright overhead" in out

    def test_blood_moon_narrated(self):
        _, _, desc = _world(
            hour=20,
            moon={"name": "blood_moon", "icon": "\U0001F15D", "light_bonus": 10},
        )
        assert "red moon stains the sky" in desc.get_area_description()

    def test_moon_via_exterior_spelling(self):
        _, _, desc = _world(
            tags=("exterior",), hour=22,
            moon={"name": "full_moon", "icon": "\U0001F315", "light_bonus": 25},
        )
        assert "full moon hangs bright overhead" in desc.get_area_description()

    def test_no_moon_in_daylight(self):
        _, _, desc = _world(
            hour=12,
            moon={"name": "full_moon", "icon": "\U0001F315", "light_bonus": 25},
        )
        assert "moon" not in desc.get_area_description().lower()

    def test_no_moon_indoors(self):
        _, _, desc = _world(
            tags=("underground",), hour=22,
            moon={"name": "full_moon", "icon": "\U0001F315", "light_bonus": 25},
        )
        assert "moon" not in desc.get_area_description().lower()

    def test_broken_moon_provider_does_not_break_the_description(self):
        """The except is narrowed to provider errors; a malformed provider
        must not take the whole description down with it."""
        graph, pm, desc = _world(hour=22)
        desc.lighting.moon_provider = MagicMock(side_effect=RuntimeError("provider down"))
        # RuntimeError is not in the narrowed tuple, so it propagates — which
        # is the point: it is no longer hidden.
        try:
            desc.get_area_description()
        except RuntimeError:
            pass
        else:
            raise AssertionError("provider failure should not be swallowed silently")

    def test_malformed_moon_provider_is_tolerated(self):
        _, _, desc = _world(hour=22)
        desc.lighting.moon_provider = MagicMock(side_effect=TypeError("bad provider"))
        out = desc.get_area_description()
        assert "A flat open place." in out
