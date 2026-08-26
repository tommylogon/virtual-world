"""Tests for the LightingSystem: light level conversion, dark vision, and ambient light."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import WorldGraph, Node, Edge, EDGE_CONNECTION, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
from engine.lighting import LightingSystem


class FakePlayerManager:
    """Duck-typed PlayerManager for LightingSystem.can_see_in_dark tests."""
    def __init__(self):
        self.players = {}
        self.active_player = None
        self.ghost_mode = False

    def is_slasher(self, player_name):
        player_obj = self.players.get(player_name)
        if not player_obj:
            return False
        return player_obj.traits.get("slasher", False) or player_obj.traits.get("is_slasher", False)


# ─────────────────── Fixtures ───────────────────


@pytest.fixture
def graph():
    """Create a bare WorldGraph."""
    return WorldGraph()


@pytest.fixture
def lighting(graph):
    """Create a LightingSystem with the graph."""
    return LightingSystem(graph)


# ─────────────────── TestLightToLevel ───────────────────


class TestLightToLevel:
    """Conversion of numeric light values to level strings."""

    def test_pitch_black_boundary(self, lighting):
        """Values 0-20 map to pitch_black."""
        assert lighting.light_to_level(0) == "pitch_black"
        assert lighting.light_to_level(10) == "pitch_black"
        assert lighting.light_to_level(20) == "pitch_black"

    def test_dim_boundary(self, lighting):
        """Values 21-40 map to dim."""
        assert lighting.light_to_level(21) == "dim"
        assert lighting.light_to_level(30) == "dim"
        assert lighting.light_to_level(40) == "dim"

    def test_normal_boundary(self, lighting):
        """Values 41-70 map to normal."""
        assert lighting.light_to_level(41) == "normal"
        assert lighting.light_to_level(55) == "normal"
        assert lighting.light_to_level(70) == "normal"

    def test_bright_boundary(self, lighting):
        """Values 71-90 map to bright."""
        assert lighting.light_to_level(71) == "bright"
        assert lighting.light_to_level(80) == "bright"
        assert lighting.light_to_level(90) == "bright"

    def test_blinding_boundary(self, lighting):
        """Values 91+ map to blinding."""
        assert lighting.light_to_level(91) == "blinding"
        assert lighting.light_to_level(100) == "blinding"

    def test_string_enum_passthrough(self, lighting):
        """String enum values are passed through unchanged."""
        for level in ("pitch_black", "dim", "normal", "bright", "blinding"):
            assert lighting.light_to_level(level) == level

    def test_invalid_string_returns_normal(self, lighting):
        """Unrecognized string values default to normal."""
        assert lighting.light_to_level("garbage") == "normal"

    def test_none_returns_normal(self, lighting):
        """None input defaults to normal."""
        assert lighting.light_to_level(None) == "normal"

    def test_edge_transition_points(self, lighting):
        """Verifies specific transition points between levels."""
        assert lighting.light_to_level(20) == "pitch_black"
        assert lighting.light_to_level(21) == "dim"
        assert lighting.light_to_level(40) == "dim"
        assert lighting.light_to_level(41) == "normal"
        assert lighting.light_to_level(70) == "normal"
        assert lighting.light_to_level(71) == "bright"
        assert lighting.light_to_level(90) == "bright"
        assert lighting.light_to_level(91) == "blinding"


# ─────────────────── TestGetLightInt ───────────────────


class TestGetLightInt:
    """Conversion of environment light values to integers."""

    def test_int_value_from_env(self, lighting):
        """Integer light value is returned directly."""
        assert lighting.get_light_int({"light": 50}) == 50

    def test_string_level_dim(self, lighting):
        """'dim' string maps to 30."""
        assert lighting.get_light_int({"light": "dim"}) == 30

    def test_string_level_pitch_black(self, lighting):
        """'pitch_black' string maps to 10."""
        assert lighting.get_light_int({"light": "pitch_black"}) == 10

    def test_string_level_normal(self, lighting):
        """'normal' string maps to 55."""
        assert lighting.get_light_int({"light": "normal"}) == 55

    def test_string_level_bright(self, lighting):
        """'bright' string maps to 80."""
        assert lighting.get_light_int({"light": "bright"}) == 80

    def test_string_level_blinding(self, lighting):
        """'blinding' string maps to 95."""
        assert lighting.get_light_int({"light": "blinding"}) == 95

    def test_missing_key_uses_default(self, lighting):
        """Missing 'light' key returns the provided default."""
        assert lighting.get_light_int({}, default=50) == 50

    def test_empty_env_returns_default(self, lighting):
        """Empty environment dict returns the default value."""
        assert lighting.get_light_int({}) == 80

    def test_unrecognized_string_uses_default(self, lighting):
        """Unknown string value returns the default."""
        result = lighting.get_light_int({"light": "unknown"}, default=42)
        assert result == 42


# ─────────────────── TestCanSeeInDark ───────────────────


class TestCanSeeInDark:
    """Dark vision checks for players."""

    def test_no_active_player_returns_false(self, lighting):
        """Without any active player, can_see_in_dark returns False."""
        pm = FakePlayerManager()
        assert lighting.can_see_in_dark(pm) is False

    def test_alive_player_without_traits(self, lighting):
        """A living player with no dark vision cannot see in the dark."""
        pm = FakePlayerManager()
        from player import Player
        hero = Player("TestHero")
        pm.players["TestHero"] = hero
        pm.active_player = "TestHero"
        assert lighting.can_see_in_dark(pm) is False

    def test_dead_player_can_see(self, lighting):
        """Dead (ghost) players can always see in the dark."""
        pm = FakePlayerManager()
        from player import Player
        ghost = Player("GhostHero")
        ghost.state = "dead"
        pm.players["GhostHero"] = ghost
        pm.active_player = "GhostHero"
        assert lighting.can_see_in_dark(pm) is True

    def test_dark_vision_trait(self, lighting):
        """Player with 'dark_vision' trait can see in the dark."""
        pm = FakePlayerManager()
        from player import Player
        dwarf = Player("DwarfHero")
        dwarf.traits = {"dark_vision": True}
        pm.players["DwarfHero"] = dwarf
        pm.active_player = "DwarfHero"
        assert lighting.can_see_in_dark(pm) is True

    def test_darkvision_alternate_spelling(self, lighting):
        """Player with 'darkvision' (no underscore) trait can see."""
        pm = FakePlayerManager()
        from player import Player
        elf = Player("ElfHero")
        elf.traits = {"darkvision": True}
        pm.players["ElfHero"] = elf
        pm.active_player = "ElfHero"
        assert lighting.can_see_in_dark(pm) is True

    def test_slasher_trait(self, lighting):
        """Player with 'slasher' trait can see in the dark."""
        pm = FakePlayerManager()
        from player import Player
        slasher = Player("SlasherHero")
        slasher.traits = {"slasher": True}
        pm.players["SlasherHero"] = slasher
        pm.active_player = "SlasherHero"
        assert lighting.can_see_in_dark(pm) is True

    def test_unknown_player_returns_false(self, lighting):
        """If active_player name is not in the players dict, return False."""
        pm = FakePlayerManager()
        pm.active_player = "Nobody"
        assert lighting.can_see_in_dark(pm) is False

    def test_player_name_arg_overrides_active(self, lighting):
        """can_see_in_dark accepts optional player_name parameter."""
        pm = FakePlayerManager()
        from player import Player
        specific = Player("SpecificHero")
        specific.state = "dead"
        pm.players["SpecificHero"] = specific
        # Don't set active_player, use named argument
        assert lighting.can_see_in_dark(pm, player_name="SpecificHero") is True

    def test_is_slasher_via_named_player(self, lighting):
        """Named player with is_slasher trait can see."""
        pm = FakePlayerManager()
        from player import Player
        slasher = Player("BigBad")
        slasher.traits = {"is_slasher": True}
        pm.players["BigBad"] = slasher
        assert lighting.can_see_in_dark(pm, player_name="BigBad") is True


# ─────────────────── TestGetAmbientLight ───────────────────


class TestGetAmbientLight:
    """Ambient light calculations with spill through ways."""

    def test_bare_area_returns_default(self, lighting, graph):
        """A area with no environment gets the default light level (80)."""
        area = Node(id="area_Test", type="area", name="Test",
                    properties={})
        graph.add_node(area)
        assert lighting.get_ambient_light("area_Test") == 80

    def test_area_with_own_light_source(self, lighting, graph):
        """A area with its own light setting returns that value."""
        area = Node(id="area_Lit", type="area", name="Lit",
                    properties={"environment": {"light": 60}})
        graph.add_node(area)
        assert lighting.get_ambient_light("area_Lit") == 60

    def test_nonexistent_area_default(self, lighting):
        """Requesting light for a missing area node returns 80."""
        assert lighting.get_ambient_light("area_Nope") == 80

    def test_light_spills_through_open_way(self, lighting, graph):
        """Light from a bright area spills into a dark area through an open door (spill = 50%)."""
        # Dark area
        dark_area = Node(id="area_Dark", type="area", name="Dark",
                         properties={"environment": {"light": 10}})
        graph.add_node(dark_area)

        # Bright area
        bright_area = Node(id="area_Bright", type="area", name="Bright",
                           properties={"environment": {"light": 80}})
        graph.add_node(bright_area)

        # Open door connecting them
        door = Node(id="way_Dark_east", type="way", name="Dark-east",
                    properties={"current_state": "open"})
        graph.add_node(door)

        # Dark area -> door
        graph.add_edge(Edge(
            source="area_Dark", target="way_Dark_east",
            type=EDGE_CONNECTION,
            properties={"direction": "east", "target": "area_Bright"}
        ))
        # door -> Bright area
        graph.add_edge(Edge(
            source="way_Dark_east", target="area_Bright",
            type=EDGE_CONNECTION,
            properties={"direction": "west", "target": "area_Dark"}
        ))

        light = lighting.get_ambient_light("area_Dark")
        # Spill = max(0, 80 * 0.5) = 40, own = 10, max = 40
        assert light == 40

    def test_no_spill_through_closed_way(self, lighting, graph):
        """Light does NOT spill through a closed door."""
        dark_area = Node(id="area_Dark", type="area", name="Dark",
                         properties={"environment": {"light": 10}})
        graph.add_node(dark_area)

        bright_area = Node(id="area_Bright", type="area", name="Bright",
                           properties={"environment": {"light": 80}})
        graph.add_node(bright_area)

        closed_way = Node(id="way_Dark_east", type="way", name="Dark-east",
                           properties={"current_state": "closed"})
        graph.add_node(closed_way)

        graph.add_edge(Edge(
            source="area_Dark", target="way_Dark_east",
            type=EDGE_CONNECTION,
            properties={"direction": "east", "target": "area_Bright"}
        ))
        graph.add_edge(Edge(
            source="way_Dark_east", target="area_Bright",
            type=EDGE_CONNECTION,
            properties={"direction": "west", "target": "area_Dark"}
        ))

        light = lighting.get_ambient_light("area_Dark")
        # No spill via closed door, own = 10
        assert light == 10

    def test_own_light_beats_spill(self, lighting, graph):
        """When a area's own light is brighter than spill, own light wins."""
        semi_lit = Node(id="area_Semi", type="area", name="Semi",
                        properties={"environment": {"light": 50}})
        graph.add_node(semi_lit)

        dim_area = Node(id="area_Dim", type="area", name="Dim",
                        properties={"environment": {"light": 10}})
        graph.add_node(dim_area)

        open_way = Node(id="way_Semi_east", type="way", name="Semi-east",
                         properties={"current_state": "open"})
        graph.add_node(open_way)

        graph.add_edge(Edge(
            source="area_Semi", target="way_Semi_east",
            type=EDGE_CONNECTION,
            properties={"direction": "east", "target": "area_Dim"}
        ))
        graph.add_edge(Edge(
            source="way_Semi_east", target="area_Dim",
            type=EDGE_CONNECTION,
            properties={"direction": "west", "target": "area_Semi"}
        ))

        light = lighting.get_ambient_light("area_Semi")
        # Spill from dim = 10 * 0.5 = 5, own = 50 -> max = 50
        assert light == 50

    def test_area_with_locked_way_no_spill(self, lighting, graph):
        """A locked door also blocks light spill."""
        dark = Node(id="area_Dark", type="area", name="Dark",
                    properties={"environment": {"light": 10}})
        graph.add_node(dark)

        bright = Node(id="area_Bright", type="area", name="Bright",
                      properties={"environment": {"light": 80}})
        graph.add_node(bright)

        locked_way = Node(id="way_Dark_north", type="way", name="Dark-north",
                           properties={"current_state": "locked"})
        graph.add_node(locked_way)

        graph.add_edge(Edge(
            source="area_Dark", target="way_Dark_north",
            type=EDGE_CONNECTION,
            properties={"direction": "north", "target": "area_Bright"}
        ))
        graph.add_edge(Edge(
            source="way_Dark_north", target="area_Bright",
            type=EDGE_CONNECTION,
            properties={"direction": "south", "target": "area_Dark"}
        ))

        light = lighting.get_ambient_light("area_Dark")
        # No spill through locked door
        assert light == 10

    def test_custom_env_dict_parameter(self, lighting):
        """When env dict is provided directly, area graph is bypassed."""
        light = lighting.get_ambient_light("ignored_area", env={"light": 35})
        assert light == 35


# ─────────────────── TestGetItemLightContribution ───────────────────


class TestGetItemLightContribution:
    """Graph-scan light from lit items in an area (including carried/equipped)."""

    @staticmethod
    def make_item(graph, name, current_state="unlit", light_level="dim", tags=None):
        node = Node(id=f"item_{name}", type="item", name=name, properties={
            "current_state": current_state,
            "light_level": light_level,
            "tags": tags or [],
        })
        graph.add_node(node)
        return node

    def _area_with_character(self, graph):
        area = Node(id="area_Test", type="area", name="Test",
                    properties={"environment": {"light": 0}})
        graph.add_node(area)
        char = Node(id="player_Test", type="character", name="Test Character",
                    properties={})
        graph.add_node(char)
        graph.add_edge(Edge(source=char.id, target=area.id, type=EDGE_IN))
        return "area_Test", "player_Test"

    def test_lit_item_in_area_contributes(self, lighting, graph):
        area_id, _ = self._area_with_character(graph)
        item = self.make_item(graph, "candle", current_state="lit",
                              light_level="dim", tags=["light_source"])
        graph.add_edge(Edge(source=item.id, target=area_id, type=EDGE_IN))
        assert lighting.get_item_light_contribution(area_id) == 30

    def test_lit_item_in_inventory_contributes(self, lighting, graph):
        area_id, player_id = self._area_with_character(graph)
        item = self.make_item(graph, "flashlight", current_state="lit",
                              light_level="normal", tags=["light_source"])
        graph.add_edge(Edge(source=item.id, target=player_id, type=EDGE_CARRYING))
        assert lighting.get_item_light_contribution(area_id) == 55

    def test_lit_item_equipped_contributes(self, lighting, graph):
        area_id, player_id = self._area_with_character(graph)
        item = self.make_item(graph, "lantern", current_state="lit",
                              light_level="bright", tags=["light_source"])
        graph.add_edge(Edge(source=item.id, target=player_id, type=EDGE_EQUIPPED))
        assert lighting.get_item_light_contribution(area_id) == 80

    def test_unlit_item_does_not_contribute(self, lighting, graph):
        area_id, _ = self._area_with_character(graph)
        item = self.make_item(graph, "candle", current_state="unlit",
                              light_level="dim", tags=["light_source"])
        graph.add_edge(Edge(source=item.id, target=area_id, type=EDGE_IN))
        assert lighting.get_item_light_contribution(area_id) == 0

    def test_item_without_light_source_tag_does_not_contribute(self, lighting, graph):
        area_id, _ = self._area_with_character(graph)
        item = self.make_item(graph, "box", current_state="lit",
                              light_level="blinding", tags=["container"])
        graph.add_edge(Edge(source=item.id, target=area_id, type=EDGE_IN))
        assert lighting.get_item_light_contribution(area_id) == 0

    def test_stacking_multiple_lit_items(self, lighting, graph):
        area_id, _ = self._area_with_character(graph)
        for name in ["candle_1", "candle_2", "candle_3"]:
            item = self.make_item(graph, name, current_state="lit",
                                  light_level="dim", tags=["light_source"])
            graph.add_edge(Edge(source=item.id, target=area_id, type=EDGE_IN))
        # 30 + 30 + 30 = 90
        assert lighting.get_item_light_contribution(area_id) == 90

    def test_contribution_clamps_at_100(self, lighting, graph):
        area_id, _ = self._area_with_character(graph)
        for i in range(5):
            item = self.make_item(graph, f"bright_{i}", current_state="lit",
                                  light_level="blinding", tags=["light_source"])
            graph.add_edge(Edge(source=item.id, target=area_id, type=EDGE_IN))
        assert lighting.get_item_light_contribution(area_id) == 100
