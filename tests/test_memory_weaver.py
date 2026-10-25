"""Tests for the Memory Weaver & Unified Editor backend routes (task-730)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from virtual_world_engine import VirtualWorld
from area import Area
from player import Player
from routes.memories import register_memories_routes
from engine.derive import derive_person_profile


def _make_app():
    app = Flask(__name__)
    world = VirtualWorld()
    world.time_ticks = 200
    world.movement.add_area(Area("Kitchen", "A warm stone kitchen.", []))
    world.movement.add_area(Area("Garden", "A quiet walled garden.", []))

    vera = Player("Vera")
    vera.current_area = "Kitchen"
    vera.personality = "Observant, cautious, fiercely loyal once trust is earned."
    vera.base_description = "A tall woman with ink-stained fingers."
    vera.fear_tags = ["fire", "betrayal"]
    vera.interest_tags = ["cinema", "tea"]

    rex = Player("Rex")
    rex.current_area = "Kitchen"
    rex.description = "A loud man in a leather apron."

    sol = Player("Sol")
    sol.current_area = "Garden"
    sol.description = "A quiet gardener with kind eyes."

    world.add_player(vera)
    world.add_player(rex)
    world.add_player(sol)

    app.world = world
    register_memories_routes(app)
    return app, world, vera, rex, sol


def test_memory_context_returns_grounding_and_non_mutating_previews():
    app, world, vera, rex, sol = _make_app()
    vera.memories.append({
        "id": "mem_existing_1",
        "text": "Rex stole the silver key from the Kitchen drawer.",
        "tick": 120,
        "importance": 8,
        "type": "observation",
        "category": "episodic",
        "entity_ids": [world._player_node_id("Rex")],
        "tags": ["rel:Rex"],
        "confidence": 0.9,
        "reinforcements": 0,
    })

    client = app.test_client()
    resp = client.post(
        "/api/players/Vera/memories/context",
        json={
            "query": "silver key Rex",
            "candidate": {
                "text": "Rex did not steal the silver key from the Kitchen drawer; he returned it.",
                "importance": 8,
                "tick": 50,
                "entities": ["Rex", "Kitchen"],
                "relationship_deltas": [
                    {
                        "who": "Rex",
                        "why": "He actually returned the key instead of stealing it",
                        "data": {"trust": 3, "respect": 2},
                    }
                ],
            },
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["character"] == "Vera"
    assert data["current_tick"] == 200
    assert "Observant" in data["persona_summary"]["personality"]
    assert "fire" in data["persona_summary"]["fears"]

    # Recalled memories must be returned without incrementing reinforcements on stored memories
    assert len(data["recalled_memories"]) >= 1
    assert vera.memories[0]["reinforcements"] == 0

    # Contradiction preview detects conflict with mem_existing_1 without mutating stored memory
    assert len(data["contradictions_preview"]) == 1
    assert data["contradictions_preview"][0]["id"] == "mem_existing_1"
    assert vera.memories[0].get("contradicts", []) == []
    assert vera.memories[0]["confidence"] == 0.9

    # Relationship preview computes before vs after without mutating Vera's memories or relationships
    assert len(data["relationship_preview"]) == 1
    rel_prev = data["relationship_preview"][0]
    assert rel_prev["who"] == "Rex"
    assert rel_prev["before"]["trust"] == 0
    assert rel_prev["after"]["trust"] > rel_prev["before"]["trust"]
    assert rel_prev["after"]["respect"] > rel_prev["before"]["respect"]
    assert len(vera.memories) == 1


def test_add_memory_with_backdate_age_decay_multi_relationships_and_expectation():
    app, world, vera, rex, sol = _make_app()
    client = app.test_client()

    resp = client.post(
        "/api/players/Vera/memories/entry",
        json={
            "text": "Three days ago in the Garden, Rex threatened Sol while Sol shielded me.",
            "type": "event",
            "category": "social",
            "importance": 7,
            "tick": -400,
            "location": "Garden",
            "source": "manual",
            "entities": ["Garden", "Rex", "Sol"],
            "simulate_age_decay": True,
            "relationship_deltas": [
                {
                    "who": "Rex",
                    "why": "He threatened Sol in front of me",
                    "data": {"fear": 3, "trust": -4},
                },
                {
                    "who": "Sol",
                    "why": "Sol stepped between us to protect me",
                    "data": {"trust": 4, "respect": 3, "affection": 2},
                },
            ],
            "derived_expectation": "When Rex raises his voice, I step between him and Sol and look for an exit.",
            "force": True,
        },
    )
    assert resp.status_code == 201
    payload = resp.get_json()
    entry = payload["entry"]
    derived = payload.get("derived_entry")

    # Backdated tick and natural age decay
    assert entry["tick"] == -400
    assert entry["activation"] < 1.0
    assert entry["activation"] >= 0.15

    # Both relationships registered and tagged
    assert "rel:Rex" in entry["tags"]
    assert "rel:Sol" in entry["tags"]
    assert "Rex" in vera.relationships
    assert "Sol" in vera.relationships

    # Derived profiles reflect each person's specific deltas without cross-contamination
    rex_prof = derive_person_profile(vera, "Rex")
    sol_prof = derive_person_profile(vera, "Sol")
    assert rex_prof["fear"] > 15
    assert rex_prof["trust"] < -15
    assert sol_prof["trust"] > 20
    assert sol_prof["respect"] > 15
    assert sol_prof["fear"] == 0

    # Derived procedural expectation memory created and linked to source memory
    assert derived is not None
    assert derived["category"] == "procedural"
    assert derived["type"] == "expectation"
    assert derived["reflection_depth"] == 1
    assert entry["id"] in derived["source_memory_ids"]
    assert len(vera.memories) == 2


def test_memory_routes_reject_ticks_prior_to_character_birthday():
    """Creating or updating a memory before birth_tick is rejected with 400."""
    app, world, vera, _, _ = _make_app()
    client = app.test_client()
    from engine import character_appearance as ca
    from engine import lifecycle as lc

    node = world.graph.get_node(world._player_node_id("Vera"))
    ca.set_record(node, {"identity": {"birthday": "14.03.2006", "age": 20}})
    birth_tick = lc.ensure_birth_tick(vera, world, node, force=True)
    assert birth_tick is not None and birth_tick < 0

    # Context endpoint reports birth_tick, birthday, and birth_gate_error when target_tick < birth_tick
    ctx_resp = client.post(
        "/api/players/Vera/memories/context",
        json={"query": "before I was born", "target_tick": birth_tick - 500},
    )
    assert ctx_resp.status_code == 200
    ctx_data = ctx_resp.get_json()
    assert ctx_data["birth_tick"] == birth_tick
    assert ctx_data["birthday"] == "14.03.2006"
    assert ctx_data["birth_gate_error"] is not None
    assert "14.03.2006" in ctx_data["birth_gate_error"]

    # Adding a memory prior to birth_tick fails with 400
    bad_add = client.post(
        "/api/players/Vera/memories/entry",
        json={"text": "An impossible pre-birth memory.", "tick": birth_tick - 10},
    )
    assert bad_add.status_code == 400
    assert "not born until" in bad_add.get_json()["error"].lower()
    assert "14.03.2006" in bad_add.get_json()["error"]
    assert len(vera.memories) == 0

    # Adding a memory on or after birth_tick succeeds
    ok_add = client.post(
        "/api/players/Vera/memories/entry",
        json={"text": "My earliest childhood memory of the orchard.", "tick": birth_tick + 100},
    )
    assert ok_add.status_code == 201
    entry_id = ok_add.get_json()["entry"]["id"]

    # Moving an existing memory to a tick prior to birth_tick fails with 400
    bad_edit = client.post(
        f"/api/players/Vera/memories/entry/{entry_id}",
        json={"tick": birth_tick - 1},
    )
    assert bad_edit.status_code == 400
    assert vera.memories[0]["tick"] == birth_tick + 100

