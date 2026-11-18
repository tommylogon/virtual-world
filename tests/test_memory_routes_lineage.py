"""Unit tests for bug-585 (opaque player ID resolution), task-950 (Two-Lane Factual Invariant & lineage), and bug-601 (per-memory suppress/unblock)."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from area import Area
from engine import lived_log, lived_log_memory
from engine.memory_retrieval import is_active_memory
from graph import EDGE_CARRYING, EDGE_CONNECTION, Edge, Node
from player import Player
from routes.memories import _resolve_player, register_memories_routes


def _make_world_app(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    world = app.world
    world.time_ticks = 25
    world.movement.add_area(Area("North Gallery", "A dimly lit gallery.", []))
    world.movement.add_area(Area("Secret Vault", "A damp stone vault.", []))

    # Connect North Gallery -> locked oak door -> Secret Vault
    door = Node(
        id="way_vault_oak_door",
        type="way",
        name="vault oak door",
        properties={
            "area_from_id": "area_north_gallery",
            "area_to_id": "area_secret_vault",
            "current_state": "locked",
            "locked": True,
        },
    )
    world.graph.add_node(door)
    world.graph.add_edge(Edge(source="area_north_gallery", target="way_vault_oak_door", type=EDGE_CONNECTION, properties={"direction": "north"}))
    world.graph.add_edge(Edge(source="way_vault_oak_door", target="area_secret_vault", type=EDGE_CONNECTION, properties={"direction": "north"}))

    # Iron key carried by Sammy Lopez
    key_item = Node(id="item_vault_iron_key", type="item", name="iron key", properties={"tags": ["key"]})
    world.graph.add_node(key_item)

    sammy = Player("sammy lopez")
    sammy.id = "0610fd64"
    sammy.current_area = "North Gallery"
    world.add_player(sammy)
    sammy_nid = world._player_node_id("sammy lopez")
    world.graph.add_edge(Edge(source="item_vault_iron_key", target=sammy_nid, type=EDGE_CARRYING))

    alex = Player("Alex Mercer")
    alex.id = "99aabbcc"
    alex.current_area = "North Gallery"
    world.add_player(alex)

    return app, app.test_client(), world, sammy, alex


# ---------------------------------------------------------------------------
# bug-585: opaque player IDs, graph node IDs, name_matcher, display names
# ---------------------------------------------------------------------------


def test_bug585_resolve_player_across_id_node_graph_and_name_matcher(tmp_path):
    app, client, world, sammy, alex = _make_world_app(tmp_path)

    # 1. Opaque player.id
    assert _resolve_player(app, "0610fd64") == ("sammy lopez", sammy)
    # 2. Node ID (exact and lowercase)
    assert _resolve_player(app, "player_sammy_lopez") == ("sammy lopez", sammy)
    # 3. Display name (case-insensitive)
    assert _resolve_player(app, "Sammy Lopez") == ("sammy lopez", sammy)
    assert _resolve_player(app, "sammy lopez") == ("sammy lopez", sammy)

    # 4. Character graph node with custom node.id -> node.name
    custom_node = Node(
        id="char_custom_sammy",
        type="character",
        name="sammy lopez",
        properties={"id": "0610fd64"},
    )
    world.graph.add_node(custom_node)
    assert _resolve_player(app, "char_custom_sammy") == ("sammy lopez", sammy)

    # 5. name_matcher fallback (partial name in active area)
    world.player_manager.active_player = "Alex Mercer"
    assert _resolve_player(app, "sammy") == ("sammy lopez", sammy)

    # 6. Unknown reference returns (None, None) and 404 from routes
    assert _resolve_player(app, "nonexistent_id") == (None, None)
    assert client.get("/api/players/nonexistent_id/memories").status_code == 404


def test_bug585_all_memory_routes_accept_opaque_id_and_node_id(tmp_path):
    app, client, world, sammy, alex = _make_world_app(tmp_path)
    sammy.memories = []

    # POST entry via opaque id, including relationship_deltas referencing alex by opaque id
    r_add = client.post(
        "/api/players/0610fd64/memories/entry",
        json={
            "text": "Alex Mercer handed me the brass compass in the Foyer.",
            "tick": 12,
            "importance": 7,
            "type": "observation",
            "relationship_deltas": [
                {"who": "99aabbcc", "why": "shared the compass", "data": {"trust": 2}},
            ],
        },
    )
    assert r_add.status_code == 201
    entry_id = r_add.get_json()["entry"]["id"]
    assert "rel:Alex Mercer" in r_add.get_json()["entry"]["tags"]

    # GET memories via opaque id, node id, and %20 display name
    for ref in ("0610fd64", "player_sammy_lopez", "sammy%20lopez"):
        r_get = client.get(f"/api/players/{ref}/memories")
        assert r_get.status_code == 200
        assert len(r_get.get_json()["memories"]) == 1

    # Retrieve, reinforce, reflect, people, context, spatial, cognitive_map, recall_route, knowledge
    r_ret = client.post(
        "/api/players/0610fd64/memories/retrieve",
        json={"query": "brass compass", "max_results": 3, "reinforce": False},
    )
    assert r_ret.status_code == 200
    assert len(r_ret.get_json()["memories"]) == 1

    r_reinf = client.post("/api/players/0610fd64/memories/reinforce", json={"ids": [entry_id], "tick": 25})
    assert r_reinf.status_code == 200
    assert r_reinf.get_json()["reinforced"] == 1

    r_refl = client.post(
        "/api/players/0610fd64/memories/reflect",
        json={"insights": ["Alex Mercer seems reliable in a crisis."], "source_memory_ids": [entry_id], "tick": 25},
    )
    assert r_refl.status_code == 200
    assert r_refl.get_json()["stored"] == 1

    assert client.get("/api/players/0610fd64/memories/people").status_code == 200
    r_ctx = client.post("/api/players/0610fd64/memories/context", json={"query": "compass"})
    assert r_ctx.status_code == 200
    assert r_ctx.get_json()["character"] == "sammy lopez"

    assert client.get("/api/players/0610fd64/memories/spatial").status_code == 200
    assert client.get("/api/players/0610fd64/memories/cognitive_map").status_code == 200
    assert client.get("/api/players/0610fd64/memories/recall_route?target=Secret%20Vault").status_code == 200
    assert client.get("/api/players/0610fd64/knowledge").status_code == 200

    # Update, delete, clear, PUT via opaque id
    assert client.post(f"/api/players/0610fd64/memories/entry/{entry_id}", json={"importance": 8}).status_code == 200
    assert client.delete(f"/api/players/0610fd64/memories/entry/{entry_id}").status_code == 200
    assert client.post("/api/players/0610fd64/memories/clear").status_code == 200
    assert sammy.memories == []
    assert client.put("/api/players/0610fd64/memories", json={"memories": []}).status_code == 200


# ---------------------------------------------------------------------------
# task-950: Two-Lane Factual Invariant & memory lineage tracking
# ---------------------------------------------------------------------------


def test_task950_routes_lineage_and_debug_payload(tmp_path):
    app, client, world, sammy, _ = _make_world_app(tmp_path)
    sammy.memories = []

    # Raw observation defaults generation_depth=0 from reflection_depth=0
    r_raw = client.post(
        "/api/players/0610fd64/memories/entry",
        json={"id": "obs_1", "text": "Heard footsteps behind the oak door.", "tick": 10, "type": "observation"},
    )
    assert r_raw.status_code == 201
    raw_entry = r_raw.get_json()["entry"]
    assert raw_entry["source_memory_ids"] == []
    assert raw_entry["generation_depth"] == 0

    # Derived reflection defaults generation_depth from reflection_depth=1
    r_ref = client.post(
        "/api/players/0610fd64/memories/entry",
        json={
            "id": "refl_1",
            "text": "Someone may be trapped in the Cellar.",
            "tick": 15,
            "type": "reflection",
            "source": "intermediator",
            "source_memory_ids": ["obs_1"],
        },
    )
    assert r_ref.status_code == 201
    refl_entry = r_ref.get_json()["entry"]
    assert refl_entry["source_memory_ids"] == ["obs_1"]
    assert refl_entry["generation_depth"] == 1

    # Second-generation entry preserves explicit generation_depth=2
    r_gen2 = client.post(
        "/api/players/0610fd64/memories/entry",
        json={
            "id": "refl_2",
            "text": "I must find a way to unlock the oak door right away.",
            "tick": 18,
            "type": "reflection",
            "reflection_depth": 1,
            "generation_depth": 2,
            "source_memory_ids": ["refl_1"],
            "derived_expectation": "Check every drawer in the Foyer for keys.",
            "force": True,
        },
    )
    assert r_gen2.status_code == 201
    gen2_entry = r_gen2.get_json()["entry"]
    assert gen2_entry["generation_depth"] == 2
    assert gen2_entry["source_memory_ids"] == ["refl_1"]
    assert r_gen2.get_json()["derived_entry"]["generation_depth"] == 3
    assert r_gen2.get_json()["derived_entry"]["source_memory_ids"] == ["refl_2"]

    # Immutable source_memory_ids on derived memory cannot be wiped without force
    r_upd = client.post(
        "/api/players/0610fd64/memories/entry/refl_1",
        json={"text": "Someone is definitely hiding in the Cellar.", "source_memory_ids": []},
    )
    assert r_upd.status_code == 200
    assert r_upd.get_json()["entry"]["source_memory_ids"] == ["obs_1"]

    # GET /memories debug payload exposes lineage back to raw obs_1 and factual_lane
    r_dbg = client.get("/api/players/0610fd64/memories?debug=1")
    assert r_dbg.status_code == 200
    dbg = r_dbg.get_json()
    assert dbg["lineage"]["refl_2"]["root_source_memory_ids"] == ["obs_1"]
    assert dbg["lineage"]["refl_2"]["generation_depth"] == 2
    assert dbg["factual_lane"]["inventory"][0]["name"] == "iron key"
    assert any(d["id"] == "way_vault_oak_door" and d["locked"] is True for d in dbg["factual_lane"]["door_locks"])
    refl2_item = next(m for m in dbg["memories"] if m["id"] == "refl_2")
    assert refl2_item["root_source_memory_ids"] == ["obs_1"]
    assert refl2_item["source_lineage"][0]["id"] == "obs_1"


def test_task950_two_lane_factual_invariant_and_lived_log_memory(tmp_path):
    app, client, world, sammy, _ = _make_world_app(tmp_path)
    sammy.memories = []
    sammy.known = ["North Gallery", "area_north_gallery"]
    sammy.learn_way_aspect("North Gallery", "north", "locked")
    sammy.record_observation("area_north_gallery", "A dimly lit gallery.", tick=2, kind="area", location="North Gallery")
    sammy.record_absence("brass key", "North Gallery", tick=4)

    # Subjective palimpsest synthesis falsely claims Sam dropped the key and unlocked the door
    synth = lived_log_memory.synthesize_palimpsest_memory(
        sammy,
        "I am pretty sure I dropped the iron key and unlocked the vault oak door earlier.",
        tick=20,
        source_memory_ids=[],
        tags=["door", "lock", "key"],
    )
    assert synth is not None
    assert synth["lane"] == lived_log_memory.LANE_PALIMPSEST
    assert synth["generation_depth"] == 1
    assert lived_log_memory.is_factual_memory(synth) is False

    # Factual lane stays completely unvarnished by the subjective palimpsest memory
    factual = lived_log_memory.build_factual_lane(sammy, world)
    assert [i["name"] for i in factual["inventory"]] == ["iron key"]
    assert "North Gallery" in factual["spatial_memory"]["known_areas"]
    assert factual["spatial_memory"]["known_way_aspects"]["North Gallery:north"] == ["locked"]
    assert any(d["id"] == "way_vault_oak_door" and d["locked"] is True for d in factual["door_locks"])
    assert any(a["target"] == "brass key" for a in factual["already_known"]["absences"])

    # Lived log bridge skips deterministic factual entries but retains lineage on subjective ones
    lived_log.record(sammy, 21, "door", "vault oak door is locked", why="door:state", area="North Gallery", tags=["lock"])
    lived_log.record(sammy, 21, "inventory", "carrying iron key", why="inventory:check", area="North Gallery")
    lived_log.record(sammy, 22, "pursuit", "started searching for the brass key", why="goal:search", area="North Gallery")

    written = lived_log_memory.bridge(sammy, world)
    assert written == 1
    bridged = [m for m in sammy.memories if m.get("source") == "lived_log"]
    assert len(bridged) == 1
    assert bridged[0]["generation_depth"] == 1
    assert len(bridged[0]["source_memory_ids"]) == 1
    assert bridged[0]["source_memory_ids"][0].startswith("lived_log:22:")
    assert bridged[0]["lane"] == lived_log_memory.LANE_PALIMPSEST

    # Multi-turn palimpsest synthesis preserves root raw observation IDs without drift
    raw_obs = sammy.add_memory("Found scratch marks near the north keyhole.", tick=23, memory_type="observation")
    gen1 = lived_log_memory.synthesize_palimpsest_memory(
        sammy, "Someone tried picking the vault oak door.", tick=24, source_memories=[raw_obs]
    )
    gen2 = lived_log_memory.synthesize_palimpsest_memory(
        sammy, "A thief tested the vault oak door before fleeing.", tick=25, source_memories=[gen1]
    )
    assert gen1["source_memory_ids"] == [raw_obs["id"]]
    assert gen1["generation_depth"] == 1
    assert gen2["source_memory_ids"] == [raw_obs["id"]]
    assert gen2["generation_depth"] == 2

    # HTTP dedup must not merge subjective palimpsest entry into deterministic factual record
    r_dup = client.post(
        "/api/players/0610fd64/memories/entry",
        json={
            "text": "Confirmed absent: brass key is not in North Gallery.",
            "tick": 4,
            "type": "reflection",
            "source": "intermediator",
        },
    )
    assert r_dup.status_code == 201
    assert r_dup.get_json().get("deduped") is not True


# ---------------------------------------------------------------------------
# bug-601: per-memory suppress / unblock + until_tick duration math
# ---------------------------------------------------------------------------


def test_bug601_per_memory_suppress_unblock_and_duration_ticks(tmp_path):
    app, client, world, sammy, _ = _make_world_app(tmp_path)
    world.time_ticks = 30
    sammy.memories = []
    m_a = sammy.add_memory("Memory A about the cellar", tick=10)
    m_b = sammy.add_memory("Memory B about the garden", tick=12)
    id_a, id_b = m_a["id"], m_b["id"]

    # Blank tags / keywords rejected with 400 without mutating any memory
    r_blank = client.post("/api/players/0610fd64/memories/suppress", json={"tags": ["  "], "keywords": "   "})
    assert r_blank.status_code == 400
    assert m_a["suppressions"] == [] and m_b["suppressions"] == []

    # Suppress only id_a with duration_ticks=5 at current_tick=30 -> until_tick=35
    r_sup = client.post(
        "/api/players/0610fd64/memories/suppress",
        json={"memory_id": id_a, "duration_ticks": 5},
    )
    assert r_sup.status_code == 200
    body = r_sup.get_json()
    assert body["suppressed"] == [id_a]
    assert body["until_tick"] == 35
    assert m_a["suppressions"] == [{"until_tick": 35, "source": "self"}]
    assert m_b["suppressions"] == []
    assert is_active_memory(m_a, 34)[0] is False
    assert is_active_memory(m_b, 34)[0] is True

    # Re-suppressing id_a after its suppression expires at tick 35 succeeds for id_a only
    world.time_ticks = 40
    r_resup = client.post(
        "/api/players/0610fd64/memories/suppress",
        json={"memory_id": id_a, "duration_ticks": 3},
    )
    assert r_resup.status_code == 200
    assert r_resup.get_json()["suppressed"] == [id_a]
    assert m_a["suppressions"] == [{"until_tick": 43, "source": "self"}]
    assert m_b["suppressions"] == []

    # Unblocking id_a leaves id_b suppressed even if id_b was suppressed with non-self scope
    sammy.suppress_memory(memory_id=id_b, duration=0, scope="manual", current_tick=40)
    r_un = client.post("/api/players/0610fd64/memories/unblock", json={"memory_id": id_a})
    assert r_un.status_code == 200
    assert r_un.get_json()["unblocked"] == [id_a]
    assert m_a["suppressions"] == []
    assert len(m_b["suppressions"]) == 1


def test_memories_context_time_locks_seed_memory_ids_and_world_datetime(tmp_path):
    app, client, world, sammy, _ = _make_world_app(tmp_path)
    world.time_ticks = 20

    sammy.memories = [
        {
            "id": "mem_past_12",
            "text": "Kyrie tackled me off my skateboard at age 12.",
            "tick": -5000,
            "world_datetime": "2011-05-14T15:00:00",
            "type": "event",
            "category": "episodic",
            "importance": 7,
        },
        {
            "id": "mem_future_99",
            "text": "Future memory that must not leak.",
            "tick": 99,
            "world_datetime": "2025-01-01T12:00:00",
            "type": "event",
            "category": "episodic",
            "importance": 8,
        },
    ]

    resp = client.post(
        "/api/players/0610fd64/memories/context",
        json={
            "query": "skateboard",
            "world_datetime": "2016-05-14T15:00:00",
            "seed_memory_ids": ["mem_past_12", "mem_future_99"],
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["current_world_datetime"] == "2016-05-14T15:00:00"
    recalled_ids = [m.get("id") for m in data["recalled_memories"]]
    assert "mem_past_12" in recalled_ids
    assert "mem_future_99" not in recalled_ids
