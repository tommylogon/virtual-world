"""Unit tests for task-734: Knowledge is memory: unified prose+data records and distinct lifecycles."""

import pytest
from app import create_app
from player import Player
from engine.memory_dynamics import apply_decay, ensure_dynamics, category_for, SEMANTIC, EPISODIC


def test_unified_knowledge_records_shape():
    player = Player("Arix")
    player.crafting_known = ["iron_dagger", "torch"]
    player.known = ["The north pass is blocked during winter", "Lord Vane fears fire"]
    player.learn_way_aspect("area_hall", "north", "locked")
    player.known_areas = {"area_hall", "area_courtyard"}

    records = player.get_knowledge_records()

    assert len(records) == 7

    # Verify every record conforms to the unified prose+data memory record shape
    for r in records:
        assert "id" in r
        assert "text" in r
        assert "type" in r
        assert "category" in r
        assert "kind" in r
        assert "source" in r
        assert "data" in r
        assert "importance" in r
        assert r["kind"] in ("semantic", "procedural")

    # Verify recipes are procedural kind
    recipes = [r for r in records if r["type"] == "recipe"]
    assert len(recipes) == 2
    for rec in recipes:
        assert rec["kind"] == "procedural"
        assert rec["category"] == "procedural"
        assert rec["source"] == "crafting"
        assert "Knows recipe:" in rec["text"]

    # Verify facts are semantic kind
    facts = [r for r in records if r["type"] == "fact"]
    assert len(facts) == 2
    for f in facts:
        assert f["kind"] == "semantic"
        assert f["category"] == "semantic"

    # Verify way aspects are semantic kind
    ways = [r for r in records if r["type"] == "way_aspect"]
    assert len(ways) == 1
    assert ways[0]["kind"] == "semantic"
    assert ways[0]["text"] == "area_hall north: locked"
    assert ways[0]["data"] == {"area": "area_hall", "direction": "north", "aspect": "locked"}

    # Verify known locations are semantic kind
    locs = [r for r in records if r["type"] == "location"]
    assert len(locs) == 2
    for loc in locs:
        assert loc["kind"] == "semantic"
        assert "Known location:" in loc["text"]


def test_semantic_knowledge_does_not_decay_on_episodic_curve():
    player = Player("Lyra")

    # Add an episodic memory that was earned on-screen
    ep_mem = player.add_memory(
        "I tripped over a loose cobblestone in the town square",
        tick=100,
        importance=4,
        memory_type="observation",
        source="auto",
        category="episodic",
    )
    ep_mem["activation"] = 1.0

    # Add a semantic knowledge memory
    sem_mem = player.add_memory(
        "The ancient vault requires three silver keys to open",
        tick=100,
        importance=6,
        memory_type="fact",
        source="knowledge",
        category="semantic",
        kind="semantic",
    )
    sem_mem["activation"] = 1.0

    # Also add a procedural recipe memory
    proc_mem = player.add_memory(
        "Knows recipe: healing_poultice",
        tick=100,
        importance=7,
        memory_type="recipe",
        source="crafting",
        category="procedural",
        kind="procedural",
    )
    proc_mem["activation"] = 1.0

    # Run multiple decay steps
    apply_decay(player, rate=0.2)
    apply_decay(player, rate=0.2)

    # Episodic activation must decay
    assert ep_mem["activation"] < 1.0, f"Expected episodic activation to decay, got {ep_mem['activation']}"

    # Semantic knowledge must NOT decay on the episodic curve
    assert sem_mem["activation"] == 1.0, f"Expected semantic activation to remain 1.0, got {sem_mem['activation']}"


def test_derived_indexes_remain_derived_not_persisted():
    app = create_app({"TESTING": True})
    player = Player("Kaelen")
    player.discovered_items = {"item_key", "item_chest"}
    player.visited_areas = {"area_square"}
    app.world.players["Kaelen"] = player

    # Serialize world to scenario dict
    data = app.world.to_dict()
    player_data = data.get("players", {}).get("Kaelen", {})

    # visited_areas and discovered_items must not be persisted as separate stores
    assert "visited_areas" not in player_data
    assert "discovered_items" not in player_data

    # Scenario round-trips cleanly
    app.world.load_from_dict(data)
    assert "Kaelen" in app.world.players


def test_api_knowledge_endpoint():
    app = create_app({"TESTING": True})
    client = app.test_client()

    player = Player("Corin")
    player.crafting_known = ["iron_shield"]
    player.known = ["Bandits camp near the stone bridge"]
    player.learn_way_aspect("area_bridge", "east", "blocked")
    app.world.players["Corin"] = player

    resp = client.get("/api/players/Corin/knowledge")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert "knowledge" in payload
    records = payload["knowledge"]
    assert len(records) == 3

    types = {r["type"] for r in records}
    assert types == {"recipe", "fact", "way_aspect"}
    for r in records:
        assert r["kind"] in ("semantic", "procedural")
