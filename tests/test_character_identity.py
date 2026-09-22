"""One character, one graph node (task-463).

The central case is the kraktooth camp, which ships an authored
``character_<slug>`` node per person next to the runtime ``player_<Name>``
anchor. The loader must collapse them into 23 character nodes, keep the retired
ids resolvable, and round-trip cleanly.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.character_identity import (  # noqa: E402
    collapse_character_identity,
    normalize_known_lists,
    rewrite_known,
)

ROOT = Path(__file__).parent.parent
CAMP = ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"


def _camp_payload():
    with open(CAMP, encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_camp():
    from virtual_world_engine import VirtualWorld

    world = VirtualWorld()
    world.load_from_dict(_camp_payload())
    return world


def test_collapse_merges_the_authored_node_into_the_anchor():
    graph = {
        "nodes": {
            "character_miki": {
                "id": "Miki", "type": "character", "name": "Miki",
                "properties": {"description": "A wanderer."},
            },
            "player_Miki": {
                "id": "player_Miki", "type": "character", "name": "Miki",
                "properties": {"x": 1, "y": 2},
            },
            "area_room": {"id": "area_room", "type": "area", "name": "Room", "properties": {}},
        },
        "edges": [
            {"source": "character_miki", "target": "area_room", "type": "in", "properties": {}},
            {"source": "player_Miki", "target": "area_room", "type": "in", "properties": {}},
            {"source": "item_hat", "target": "character_miki", "type": "carrying", "properties": {}},
        ],
    }
    players = {"Miki": {"name": "Miki", "id": "abcd1234", "known": ["character_miki"]}}

    report = collapse_character_identity(graph, players)

    assert report["collapsed"] == [("character_miki", "player_Miki")]
    assert "character_miki" not in graph["nodes"]
    # Runtime props survive; authored prose wins for description.
    assert graph["nodes"]["player_Miki"]["properties"] == {
        "x": 1, "y": 2, "description": "A wanderer.",
    }
    assert report["aliases"]["character_miki"] == "player_Miki"
    # The authored and runtime location edges collapse into one.
    ins = [edge for edge in graph["edges"] if edge["type"] == "in"]
    assert len(ins) == 1
    assert ins[0]["source"] == "player_Miki"
    carrying = [edge for edge in graph["edges"] if edge["type"] == "carrying"]
    assert carrying[0]["target"] == "player_Miki"


def test_collapse_does_not_mutate_shared_node_properties():
    live_props = {"x": 1, "y": 2}
    graph = {
        "nodes": {
            "character_miki": {
                "id": "character_miki", "type": "character", "name": "Miki",
                "properties": {"description": "A wanderer."},
            },
            "player_Miki": {
                "id": "player_Miki", "type": "character", "name": "Miki",
                "properties": live_props,
            },
        },
        "edges": [],
    }

    collapse_character_identity(graph, {"Miki": {"name": "Miki", "id": "abcd1234"}})

    assert live_props == {"x": 1, "y": 2}


def test_collapse_is_idempotent():
    payload = _camp_payload()
    first = collapse_character_identity(payload["graph"], payload["players"])
    second = collapse_character_identity(payload["graph"], payload["players"])

    assert len(first["collapsed"]) == 23
    assert second["collapsed"] == []


def test_collapse_leaves_duplicate_display_names_alone():
    graph = {
        "nodes": {
            "character_jon": {"id": "character_jon", "type": "character", "name": "Jon", "properties": {}},
            "player_Jon": {"id": "player_Jon", "type": "character", "name": "Jon", "properties": {}},
            "player_Jon__bbbb22": {"id": "player_Jon__bbbb22", "type": "character", "name": "Jon", "properties": {}},
        },
        "edges": [],
    }
    players = {
        "Jon": {"name": "Jon", "id": "aaaa1111"},
        "Jon__bbbb2222": {"name": "Jon", "id": "bbbb2222"},
    }

    report = collapse_character_identity(graph, players)

    assert report["collapsed"] == []
    assert "character_jon" in graph["nodes"]


def test_rewrite_known_moves_retired_id_onto_survivor():
    aliases = {"character_miki": "player_Miki"}
    known, changed = rewrite_known(["character_miki", "area_room", "Miki"], aliases)
    assert known == ["player_Miki", "area_room", "Miki"]
    assert changed == 1


def test_normalize_known_lists_rewrites_raw_player_dicts():
    players = {"Miki": {"known": ["character_miki"]}, "Solo": {}}
    changed = normalize_known_lists(players, {"character_miki": "player_Miki"})
    assert changed == 1
    assert players["Miki"]["known"] == ["player_Miki"]


def test_kraktooth_loads_as_one_node_per_character():
    world = _load_camp()
    graph = world.graph

    character_nodes = [node for node in graph.nodes.values() if node.type == "character"]
    assert len(character_nodes) == 23
    assert not [key for key in graph.nodes if key.startswith("character_")]

    alias = graph.get_node("character_arix")
    assert alias is not None and alias.id == "player_Arix"

    player_id = world.player_manager.get_player_node_id("Arix")
    location_edges = graph.get_edges_for_source(player_id, "in")
    assert [edge.target for edge in location_edges] == ["area_chiefs_pit"]

    # No edge of any type still mentions a retired character id.
    retired = [key for key in graph.nodes if key.startswith("character_")]
    assert retired == []
    for edge in graph.edges:
        assert not str(edge.source).startswith("character_")
        assert not str(edge.target).startswith("character_")


def test_kraktooth_save_round_trips_single_identity():
    world = _load_camp()
    scenario = world.to_scenario_dict()

    character_nodes = [
        node for node in scenario["graph"]["nodes"].values() if node.get("type") == "character"
    ]
    assert len(character_nodes) == 23
    assert not [key for key in scenario["graph"]["nodes"] if key.startswith("character_")]

    reloaded = _load_camp()
    reloaded.load_from_dict(scenario)
    assert len(
        [node for node in reloaded.graph.nodes.values() if node.type == "character"]
    ) == 23


def test_location_and_possession_resolve_after_collapse():
    world = _load_camp()
    arix = world.player_manager.get_player("Arix")

    assert arix.current_area == "Chief's Pit"
    assert world.graph.get_node(world.player_manager.get_player_node_id("Arix")) is not None

    equipped = [
        edge for edge in world.graph.get_edges_for_target(
            world.player_manager.get_player_node_id("Arix"), "equipped"
        )
    ]
    assert equipped, "runtime equipped edges still target the canonical anchor"
