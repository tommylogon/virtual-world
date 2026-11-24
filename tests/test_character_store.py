"""Unit tests for engine/character_store.py (task-457, task-914).

Verifies character definition extraction, node property application,
graph-node-first hydration, and scenario serialization parity.
"""
from graph import Node, WorldGraph
from player import Player
from virtual_world_engine import VirtualWorld
from engine.character_store import (
    to_node_properties,
    apply_node_properties,
    hydrate_player_from_node,
    sync_player_to_node,
    AUTHORED_DEFINITION_KEYS,
)


def test_to_node_properties_extracts_authored_definition():
    player = Player(name="Kora")
    player.personality = "Fierce and observant hunter."
    player.base_description = "A tall scout in leathers."
    player.description = "A tall scout wearing a dark hooded cloak."
    player.traits = {"stealthy": {"level": 2}, "keen_eye": {"level": 1}}
    player.tags = ["scout", "agile", "alert"]
    player.interest_tags = ["tracks", "weather"]
    player.fear_tags = ["fire"]
    player.flags = {"met_elder": True}
    player.triggers = [{"trigger_type": "on_examine", "effects": []}]

    props = to_node_properties(player)

    assert props["personality"] == "Fierce and observant hunter."
    assert props["base_description"] == "A tall scout in leathers."
    assert props["description"] == "A tall scout wearing a dark hooded cloak."
    assert props["traits"] == {"stealthy": {"level": 2}, "keen_eye": {"level": 1}}
    assert props["tags"] == ["scout", "agile", "alert"]
    assert props["persona"]["personality"]["interests"] == ["tracks", "weather"]
    assert props["persona"]["personality"]["fears"] == ["fire"]
    assert "interest_tags" not in props
    assert "fear_tags" not in props
    assert props["flags"] == {"met_elder": True}
    assert props["triggers"] == [{"trigger_type": "on_examine", "effects": []}]

    # Transient runtime state must NOT leak into node properties
    assert "vitals" not in props
    assert "memories" not in props
    assert "lived_log" not in props
    assert "action_points" not in props


def test_apply_node_properties_hydrates_player_definition():
    player = Player(name="Miki")
    props = {
        "personality": "Quiet scholar.",
        "base_description": "A pale wanderer.",
        "traits": {"bookish": {"level": 1}},
        "tags": ["scholar"],
        "interest_tags": ["ancient_tomes"],
        "fear_tags": ["spiders"],
    }
    pdata_fallback = {
        "personality": "Old fallback",
        "tags": ["fallback_tag"],
    }

    apply_node_properties(player, props, pdata_fallback)

    # Node properties must win over legacy pdata fallback
    assert player.personality == "Quiet scholar."
    assert player.base_description == "A pale wanderer."
    assert "bookish" in player.traits
    assert player.tags == ["scholar"]
    assert player.interest_tags == ["ancient_tomes"]
    assert player.fear_tags == ["spiders"]


def test_hydrate_player_from_node_creates_functional_player():
    node = Node(
        id="player_Bram",
        type="character",
        name="Bram",
        properties={
            "personality": "Stalwart guard.",
            "base_description": "A heavy-set sentry.",
            "tags": ["guard", "stout"],
            "traits": {"vigilant": {"level": 1}},
        },
    )

    player = hydrate_player_from_node(node)

    assert player.name == "Bram"
    assert player.personality == "Stalwart guard."
    assert player.base_description == "A heavy-set sentry."
    assert "guard" in player.tags
    assert "vigilant" in player.traits


def test_sync_player_to_node_updates_node_in_place():
    node = Node(id="player_Tess", type="character", name="Tess", properties={"x": 100, "y": 200})
    player = Player(name="Tess")
    player.personality = "Curious alchemist."
    player.tags = ["alchemist"]

    sync_player_to_node(player, node)

    # Authored definition is synced
    assert node.properties["personality"] == "Curious alchemist."
    assert node.properties["tags"] == ["alchemist"]
    # Existing layout properties are preserved
    assert node.properties["x"] == 100
    assert node.properties["y"] == 200


def test_deserialize_world_hydrates_character_nodes_omitted_from_players_dict():
    # Scenario has character nodes in graph.nodes, but empty players dict
    payload = {
        "graph": {
            "nodes": {
                "area_courtyard": {
                    "id": "area_courtyard",
                    "type": "area",
                    "name": "Courtyard",
                    "properties": {},
                },
                "player_Orin": {
                    "id": "player_Orin",
                    "type": "character",
                    "name": "Orin",
                    "properties": {
                        "personality": "Stoic archer.",
                        "base_description": "A lean marksman.",
                        "tags": ["archer"],
                        "traits": {"marksman": {"level": 2}},
                    },
                },
            },
            "edges": [
                {"source": "player_Orin", "target": "area_courtyard", "type": "in"}
            ],
        },
        "players": {},
        "active_player": "Orin",
    }

    world = VirtualWorld()
    world.load_from_dict(payload)

    orin = world.player_manager.get_player("Orin")
    assert orin is not None, "Player model was hydrated from graph node"
    assert orin.name == "Orin"
    assert orin.personality == "Stoic archer."
    assert orin.base_description == "A lean marksman."
    assert "archer" in orin.tags
    assert "marksman" in orin.traits
    assert orin.current_area == "Courtyard"


def test_to_scenario_dict_preserves_character_node_definition_and_strips_players_block():
    world = VirtualWorld()
    world.load_from_dict({
        "graph": {
            "nodes": {
                "area_hall": {"id": "area_hall", "type": "area", "name": "Hall", "properties": {}},
                "player_Dara": {"id": "player_Dara", "type": "character", "name": "Dara", "properties": {}},
            },
            "edges": [{"source": "player_Dara", "target": "area_hall", "type": "in"}],
        },
        "players": {"Dara": {"name": "Dara"}},
        "active_player": "Dara",
    })

    dara = world.player_manager.get_player("Dara")
    dara.personality = "Cunning diplomat."
    dara.base_description = "A sharp-eyed emissary."
    dara.tags = ["diplomat", "silver_tongue"]

    scenario = world.to_scenario_dict()

    # Character node in graph.nodes has definition
    dara_node = scenario["graph"]["nodes"]["player_Dara"]
    assert dara_node["properties"]["personality"] == "Cunning diplomat."
    assert dara_node["properties"]["base_description"] == "A sharp-eyed emissary."
    assert dara_node["properties"]["tags"] == ["diplomat", "silver_tongue"]

    # Players block is stripped of duplicate authored definition
    pdata = scenario["players"]["Dara"]
    for stripped_key in ("personality", "base_description", "description", "tags", "traits", "languages"):
        assert stripped_key not in pdata, f"{stripped_key} must be stripped from players block in scenario"


def test_languages_store_and_scenario_roundtrip():
    world = VirtualWorld()
    world.load_from_dict({
        "graph": {
            "nodes": {
                "area_hall": {"id": "area_hall", "type": "area", "name": "Hall", "properties": {}},
                "player_Aoi": {"id": "player_Aoi", "type": "character", "name": "Aoi", "properties": {}},
            },
            "edges": [{"source": "player_Aoi", "target": "area_hall", "type": "in"}],
        },
        "players": {"Aoi": {"name": "Aoi"}},
        "active_player": "Aoi",
    })

    aoi = world.player_manager.get_player("Aoi")
    aoi.languages = [
        {"language": "japanese", "fluency": "native", "known_words": [], "literate": True},
        {
            "language": "english",
            "fluency": "broken",
            "known_words": ["bathroom", "wait", "hungry"],
            "literate": False,
        },
    ]

    props = to_node_properties(aoi)
    assert props["languages"] == aoi.languages
    assert "languages" in AUTHORED_DEFINITION_KEYS

    scenario = world.to_scenario_dict()
    aoi_node = scenario["graph"]["nodes"]["player_Aoi"]
    assert aoi_node["properties"]["languages"] == aoi.languages
    assert "languages" not in scenario["players"]["Aoi"]

    reloaded = VirtualWorld()
    reloaded.load_from_dict(scenario)
    aoi2 = reloaded.player_manager.get_player("Aoi")
    assert aoi2.languages == aoi.languages
