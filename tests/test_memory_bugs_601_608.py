"""Regression tests for bug-601, bug-602, bug-604, and bug-608."""

import time
import pytest

from app import create_app
from engine import daily_reflection, lived_log_memory
from engine.memory_retrieval import is_active_memory
from engine.vector_store import VectorStore
from player import Player


@pytest.fixture()
def app_and_client(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    app.world.time_ticks = 20
    p = Player("Lyrie")
    p.current_area = "Foyer"
    p2 = Player("Anna")
    p2.current_area = "Foyer"
    app.world.players["Lyrie"] = p
    app.world.players["Anna"] = p2
    return app, app.test_client(), p


# ---------------------------------------------------------------------------
# bug-601: per-memory suppress / unblock + until_tick math
# ---------------------------------------------------------------------------

def test_bug601_suppress_unblock_isolation_and_until_tick(app_and_client):
    app, client, p = app_and_client
    p.add_memory("Memory A about the cellar", tick=5)
    p.add_memory("Memory B about the garden", tick=6)
    id_a = p.memories[0]["id"]
    id_b = p.memories[1]["id"]

    # Empty filter without wildcard must be rejected by route and noop on Player
    assert p.suppress_memory() == []
    resp_bad = client.post("/api/players/Lyrie/memories/suppress", json={"tags": [], "duration": 1})
    assert resp_bad.status_code == 400

    # Suppress only id_a for duration=3 at current_tick=20 -> until_tick=23
    resp = client.post(
        "/api/players/Lyrie/memories/suppress",
        json={"memory_id": id_a, "duration": 3},
    )
    assert resp.status_code == 200
    assert resp.get_json()["suppressed"] == [id_a]
    assert p.memories[0]["suppressions"][0]["until_tick"] == 23
    assert p.memories[1]["suppressions"] == []

    # Survives clear_expired_suppressions and is_active_memory at tick 21, expires at 23
    p.clear_expired_suppressions(21)
    assert len(p.memories[0]["suppressions"]) == 1
    assert is_active_memory(p.memories[0], 21)[0] is False
    assert is_active_memory(p.memories[1], 21)[0] is True

    # Unblock only id_a while id_b is also suppressed
    p.suppress_memory(memory_id=id_b, duration=0, current_tick=21)
    assert len(p.memories[1]["suppressions"]) == 1
    resp_un = client.post("/api/players/Lyrie/memories/unblock", json={"memory_id": id_a})
    assert resp_un.status_code == 200
    assert resp_un.get_json()["unblocked"] == [id_a]
    assert p.memories[0]["suppressions"] == []
    assert len(p.memories[1]["suppressions"]) == 1

    # Expiry check on id_a when re-suppressed
    p.suppress_memory(memory_id=id_a, duration=2, current_tick=21)
    assert p.memories[0]["suppressions"][0]["until_tick"] == 23
    p.clear_expired_suppressions(23)
    assert p.memories[0]["suppressions"] == []


# ---------------------------------------------------------------------------
# bug-602: VectorStore single-key removal, delete/update cleanup, Channel 7
# ---------------------------------------------------------------------------

def test_bug602_vector_cleanup_on_delete_and_text_edit(app_and_client):
    app, client, p = app_and_client
    p.add_memory("First memory", tick=1)
    p.add_memory("Second memory", tick=2)
    m1_id = p.memories[0]["id"]
    m2_id = p.memories[1]["id"]
    p.memories[0]["contradicts"] = [m2_id]
    p.memories[1]["contradicts"] = [m1_id]
    p.memory_index["item_key"] = m2_id

    store = VectorStore(app.config["DATA_DIR"])
    store.upsert([
        {"key": f"Lyrie::{m1_id}", "vector": [1.0, 0.0]},
        {"key": f"Lyrie::{m2_id}", "vector": [0.0, 1.0]},
    ], model="test", dims=2)
    assert store.stats()["count"] == 2

    # Edit m1 text -> vector invalidated & removed from VectorStore
    upd = client.post(
        f"/api/players/Lyrie/memories/entry/{m1_id}",
        json={"text": "Updated first memory"},
    )
    assert upd.status_code == 200
    assert upd.get_json().get("vector_invalidated") is True
    assert f"Lyrie::{m1_id}" not in VectorStore(app.config["DATA_DIR"]).known_keys("Lyrie")

    # Delete m2 -> vector removed, contradicts[] scrubbed, memory_index cleared
    dele = client.delete(f"/api/players/Lyrie/memories/entry/{m2_id}")
    assert dele.status_code == 200
    assert f"Lyrie::{m2_id}" not in VectorStore(app.config["DATA_DIR"]).known_keys("Lyrie")
    assert m2_id not in (p.memories[0].get("contradicts") or [])
    assert "item_key" not in p.memory_index


def test_bug602_channel7_semantic_scores_under_associative(app_and_client):
    app, client, p = app_and_client
    p.add_memory("Unrelated phrasing about brass", tick=10, importance=4)
    mid = p.memories[0]["id"]

    res = client.post(
        "/api/players/Lyrie/memories/retrieve",
        json={
            "strategy": "associative",
            "query": "missing key",
            "cues": {"semantic_scores": {mid: 0.9}},
            "min_score": 1.0,
            "reinforce": False,
        },
    )
    assert res.status_code == 200
    mems = res.get_json()["memories"]
    assert any(m["id"] == mid for m in mems)


# ---------------------------------------------------------------------------
# bug-604: reflection depth, legacy string dynamics, closeness, rel:<who> validation
# ---------------------------------------------------------------------------

def test_bug604_reflect_validates_rel_and_legacy_dynamics(app_and_client):
    app, client, p = app_and_client
    p.add_memory("Raw observation 1", tick=1, importance=7)
    raw_id = p.memories[0]["id"]

    # Legacy string insight gets reflection_depth=1 and ensure_dynamics
    resp_leg = client.post(
        "/api/players/Lyrie/memories/reflect",
        json={"insights": ["Anna is hiding something in the cellar."], "source_memory_ids": [raw_id], "tick": 10},
    )
    assert resp_leg.status_code == 200
    leg_mem = p.memories[-1]
    assert leg_mem["reflection_depth"] == 1
    assert leg_mem["source_memory_ids"] == [raw_id]
    assert "activation" in leg_mem

    # Structured insight with closeness + unresolved vs resolved 'who'
    resp_struct = client.post(
        "/api/players/Lyrie/memories/reflect",
        json={
            "insights": [
                {
                    "belief": "Anna has become much closer to me after the cellar talk.",
                    "about": ["Anna"],
                    "confidence": 0.85,
                    "relationship": {"who": "Anna", "dim": "closeness", "delta": 2},
                },
                {
                    "belief": "Ghostly Nobody cannot be trusted at all.",
                    "about": [],
                    "confidence": 0.6,
                    "relationship": {"who": "GhostlyNobody", "dim": "trust", "delta": -3},
                },
            ],
            "source_memory_ids": [raw_id],
            "tick": 12,
        },
    )
    assert resp_struct.status_code == 200
    body = resp_struct.get_json()
    assert len(body["entries"]) >= 2
    tags_all = [t for m in p.memories for t in (m.get("tags") or [])]
    assert "rel:Anna" in tags_all
    assert "closeness:2" in tags_all
    assert "rel:GhostlyNobody" not in tags_all


# ---------------------------------------------------------------------------
# bug-608: /memories/context suppression parity, lived_log same-tick, daily_reflection
# ---------------------------------------------------------------------------

def test_bug608_memories_context_respects_suppressions(app_and_client):
    app, client, p = app_and_client
    p.add_memory("Secret cellar key is under the rug.", tick=5, importance=8)
    p.add_memory("Invalid cellar key rumor.", tick=5, importance=8)
    p.add_memory("Superseded cellar key note.", tick=5, importance=8)
    p.add_memory("Visible cellar note on the table.", tick=6, importance=6)
    secret_id = p.memories[0]["id"]
    invalid_id = p.memories[1]["id"]
    superseded_id = p.memories[2]["id"]
    visible_id = p.memories[3]["id"]
    p.suppress_memory(memory_id=secret_id, duration=0, current_tick=20)
    p.memories[1]["invalid_at"] = 10
    p.memories[2]["superseded_by"] = visible_id
    before_recall = p.memories[3].get("recall_count", 0)

    res = client.post(
        "/api/players/Lyrie/memories/context",
        json={"query": "cellar key"},
    )
    assert res.status_code == 200
    recalled = res.get_json()["recalled_memories"]
    recalled_ids = {m["id"] for m in recalled}
    assert secret_id not in recalled_ids
    assert invalid_id not in recalled_ids
    assert superseded_id not in recalled_ids
    assert visible_id in recalled_ids
    # Read-only preview must not reinforce recalled memories
    assert p.memories[3].get("recall_count", 0) == before_recall


def test_bug608_lived_log_same_tick_bridge_does_not_drop(app_and_client):
    _, _, p = app_and_client
    # Tick 0 events must not be skipped on a fresh player
    p.lived_log = [
        {"tick": 0, "kind": "death", "who": "Rat", "area": "Foyer"},
    ]
    assert lived_log_memory.bridge(p) == 1
    p.lived_log.append(
        {"tick": 0, "kind": "pursuit", "what": "chased Rat", "area": "Foyer"}
    )
    assert lived_log_memory.bridge(p) == 1

    p.lived_log.append(
        {"tick": 5, "kind": "death", "who": "Goblin", "area": "Foyer"}
    )
    assert lived_log_memory.bridge(p) == 1

    # Second event appended later on the SAME tick 5
    p.lived_log.append(
        {"tick": 5, "kind": "pursuit", "what": "chased Anna to the Foyer", "area": "Foyer"}
    )
    assert lived_log_memory.bridge(p) == 1
    assert len(p.memories) == 4
    # Repeated call with no new entries is idempotent
    assert lived_log_memory.bridge(p) == 0


def test_bug608_daily_reflection_unix_timestamp_and_entity_ids(app_and_client):
    app, _, p = app_and_client
    before = time.time() - 5
    res = daily_reflection.apply_reflection_result(
        app.world,
        p,
        {"reflection": "Anna seemed nervous near the Foyer."},
    )
    assert res["memory_added"] is True
    mem = [m for m in p.memories if m["id"] == res["memory_id"]][0]
    assert mem["timestamp"] >= before
    assert "Anna" in mem["entity_ids"] or getattr(app.world.players["Anna"], "id", "Anna") in mem["entity_ids"]


def test_bug608_tick_manager_wires_daily_reflection_under_provider_guard(app_and_client):
    app, _, p = app_and_client
    calls = []

    def _provider(ctx):
        calls.append(ctx.get("character"))
        return {"reflection": f"Anna watched {ctx.get('area')}."}

    app.world.local_provider = _provider
    app.world.tick_manager.tick_turn(skip_npcs=True)
    assert len(calls) >= 1
    refl_mems = [m for m in p.memories if m.get("source") == "daily_reflection"]
    assert len(refl_mems) == 1
    assert refl_mems[0]["timestamp"] >= time.time() - 10
