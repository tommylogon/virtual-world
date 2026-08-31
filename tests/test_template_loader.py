"""TemplateLoader (scenario-from-text format): supporting cast + item tags/mech props."""

import pytest

from graph import EDGE_IN
from virtual_world_engine import VirtualWorld


@pytest.fixture
def world():
    return VirtualWorld()


def _template(**overrides):
    data = {
        "player": {"name": "Hero", "personality": "brave"},
        "current_area": "Kitchen",
        "areas": {
            "Kitchen": {
                "description": "A warm kitchen.",
                "environment": {"temperature": 22},
                "items": [{
                    "name": "Flame Candle",
                    "description": "A stubby candle.",
                    "actions": "examine,use",
                    "tags": "light_source, magic",
                    "light_level": "dim",
                }],
            },
            "Cellar": {
                "description": "A cold cellar.",
                "exits": {"south": {"target": "Kitchen", "state": "open"}},
            },
        },
        "characters": [
            {"name": "Pim", "description": "A small helper.", "area": "Kitchen", "tags": "animal"},
            {"name": "Hero"},  # duplicate of protagonist — must be skipped
        ],
        "world_lore": [{"category": "places", "title": "The Lodge", "content": "Hidden."}],
    }
    data.update(overrides)
    return data


def test_characters_are_created_and_placed(world):
    world.load_from_dict(_template())
    players = world.player_manager.players
    assert "Pim" in players
    assert players["Pim"].description == "A small helper."
    assert players["Pim"].tags == ["animal"]
    assert players["Pim"].current_area == "Kitchen"
    # character graph node + placement edge exist
    pim_node = world.graph.get_node("player_Pim")
    assert pim_node is not None and pim_node.type == "character"
    assert any(e.source == "player_Pim" and e.target == "area_kitchen" and e.type == EDGE_IN
               for e in world.graph.edges)


def test_protagonist_stays_active(world):
    world.load_from_dict(_template())
    assert world.player_manager.active_player == "Hero"


def test_item_tags_and_mechanical_props_persist(world):
    world.load_from_dict(_template())
    node = world.graph.get_node("item_Flame Candle")
    assert node is not None
    assert node.properties["tags"] == ["light_source", "magic"]
    assert node.properties["light_level"] == "dim"


def test_duplicate_character_names_skipped(world):
    world.load_from_dict(_template())
    assert len(world.player_manager.players) == 2  # Hero + Pim, not 3


def test_template_without_characters_still_loads(world):
    world.load_from_dict({"player": {"name": "Solo"}, "areas": {"Den": {"description": "cozy"}}})
    assert "Solo" in world.player_manager.players
    assert world.player_manager.active_player == "Solo"
