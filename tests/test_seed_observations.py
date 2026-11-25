"""End-to-end tests for task-1014: batch Past Observation & Event Seeder."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph import Node, Edge, EDGE_CONNECTION, EDGE_CONTAINS
from player import Player
from virtual_world_engine import VirtualWorld


def _make_mansion_and_camp_app():
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    world = VirtualWorld()

    # Mansion areas
    foyer = Node("area_foyer", "area", "foyer", {"scope": "mansion", "description": "Dim oak foyer."})
    library = Node("area_library", "area", "library", {"scope": "mansion", "description": "Dusty library."})
    front_door = Node("way_front_door", "way", "front door", {"locked": True, "description": "Heavy door with a skull keyhole."})
    secret_panel = Node("way_secret_panel", "way", "secret panel", {"hidden": True, "locked": True})
    coat_rack = Node("item_coat_rack", "item", "coat rack", {"tags": ["furniture", "wood"], "description": "Tall oak coat rack."})

    # Goblin camp areas
    camp_gate = Node("area_camp_gate", "area", "camp gate", {"scope": "goblin_camp", "description": "Spiked palisade gate."})
    cook_pit = Node("area_cook_pit", "area", "cook pit", {"scope": "goblin_camp", "description": "Smoky cook pit."})
    watch_post = Node("area_watch_post", "area", "watch post", {"scope": "goblin_camp", "description": "Rickety watch tower."})
    jerky = Node("item_jerky", "item", "dried jerky", {"tags": ["food", "edible"]})
    gate_way = Node("way_camp_gate", "way", "palisade gate", {"blocked": True})

    for n in (foyer, library, front_door, secret_panel, coat_rack, camp_gate, cook_pit, watch_post, jerky, gate_way):
        world.graph.add_node(n)

    world.graph.add_edge(Edge(coat_rack.id, foyer.id, EDGE_CONTAINS))
    world.graph.add_edge(Edge(foyer.id, front_door.id, EDGE_CONNECTION, {"direction": "south"}))
    world.graph.add_edge(Edge(foyer.id, secret_panel.id, EDGE_CONNECTION, {"direction": "east"}))

    world.graph.add_edge(Edge(jerky.id, cook_pit.id, EDGE_CONTAINS))
    world.graph.add_edge(Edge(camp_gate.id, gate_way.id, EDGE_CONNECTION, {"direction": "north"}))

    for pname, area_name in (("miki", "library"), ("elena", "library"), ("goblin_a", "camp gate"), ("goblin_b", "cook pit")):
        p = Player(pname)
        p.current_area = area_name
        world.add_player(p)
    world.time_ticks = 1000

    app.world = world
    return app, world


def test_mansion_foyer_seed_areas_items_ways_and_note():
    app, world = _make_mansion_and_camp_app()
    client = app.test_client()

    resp = client.post("/api/world/seed-observations", json={
        "players": ["miki", "elena"],
        "areas": ["foyer"],
        "offset_minutes": 15,
        "observe_items": True,
        "observe_ways": True,
        "include_hidden_ways": False,
        "note": "The front door slammed shut behind us with a skull lock.",
        "add_timeline_milestone": True,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["players_seeded"] == 2
    assert data["areas_seeded"] == 1
    assert data["items_seeded"] == 2  # coat rack x 2 players
    assert data["ways_seeded"] == 2   # front door x 2 players (secret panel skipped)
    assert data["notes_added"] == 2
    assert data["base_tick"] == 997   # 1000 - (15 / 5)

    for pname in ("miki", "elena"):
        p = world.players[pname]
        assert "foyer" in p.visited_area_names(world.graph)
        # Locked aspect on front door was learned
        assert p.knows_way_aspect("foyer", "south", "locked") is True
        # Hidden secret panel was NOT learned
        assert p.knows_way_aspect("foyer", "east", "locked") is False
        # Item observation carries item tags and world_datetime
        item_obs = p.observation_memory("item_coat_rack")
        assert item_obs is not None
        assert "furniture" in item_obs.get("tags", [])
        assert item_obs["tick"] == 997
        assert item_obs.get("world_datetime")
        # Shared backstory note attached with entity_ids
        notes = [m for m in p.memories if "skull lock" in m.get("text", "")]
        assert len(notes) == 1
        assert "way_front_door" in notes[0].get("entity_ids", [])


def test_goblin_camp_scope_batch_seed_staggered_over_days():
    app, world = _make_mansion_and_camp_app()
    client = app.test_client()

    resp = client.post("/api/world/seed-observations", json={
        "players": "all_in_scope",
        "scope": "goblin_camp",
        "spread_days": 3,
        "observe_items": True,
        "observe_ways": True,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["players_seeded"] == 2  # goblin_a and goblin_b only (not miki/elena)
    assert data["areas_seeded"] == 3    # camp gate, cook pit, watch post

    for gname in ("goblin_a", "goblin_b"):
        g = world.players[gname]
        visited = g.visited_area_names(world.graph)
        assert {"camp gate", "cook pit", "watch post"}.issubset(visited)
        assert "foyer" not in visited
        # Blocked aspect on palisade gate learned
        assert g.knows_way_aspect("camp gate", "north", "blocked") is True
        # Jerky observation carries "food" tag
        jerky_obs = g.observation_memory("item_jerky")
        assert jerky_obs is not None
        assert "food" in jerky_obs.get("tags", [])
        # Timestamps are staggered in the past (strictly < 1000 and >= 1000 - 3*288)
        ticks = [
            g.observation_memory(aid)["tick"]
            for aid in ("area_camp_gate", "area_cook_pit", "area_watch_post")
        ]
        assert all(1000 - 3 * 288 <= t < 1000 for t in ticks)
        assert len(set(ticks)) >= 2  # staggered across different ticks

    # Miki & Elena were untouched
    assert "camp gate" not in world.players["miki"].visited_area_names(world.graph)


def test_per_player_woven_notes_override_shared_note():
    app, world = _make_mansion_and_camp_app()
    client = app.test_client()

    resp = client.post("/api/world/seed-observations", json={
        "players": ["miki", "elena"],
        "areas": ["foyer"],
        "offset_minutes": 10,
        "note": "generic fallback",
        "per_player_notes": {
            "miki": {"text": "Omg the skull door locked behind us and I am NOT staying in that foyer!", "importance": 8, "tags": ["fear"]},
            "elena": {"text": "The foyer door bolted shut via a skull-shaped mechanism; we retreated to the library.", "importance": 7, "tags": ["investigation"]},
        },
    })
    assert resp.status_code == 200
    miki_texts = [m["text"] for m in world.players["miki"].memories]
    elena_texts = [m["text"] for m in world.players["elena"].memories]
    assert any("Omg the skull door" in t for t in miki_texts)
    assert any("skull-shaped mechanism" in t for t in elena_texts)
    assert not any("generic fallback" in t for t in miki_texts)
