"""Tests for the semantic-memory vector store (task-91)."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.vector_store import VectorStore


# Axis-aligned unit vectors keep cosine math obvious:
# e1·e2=0, e1·e1'=1, mixed=(0.6, 0.8) → 45°-ish scores.
E1 = [1.0, 0.0]
E2 = [0.0, 1.0]
E1_SCALED = [5.0, 0.0]          # same direction as E1 → cos 1.0
MIXED = [0.7071067811865476, 0.7071067811865476]


@pytest.fixture()
def store(tmp_path):
    return VectorStore(str(tmp_path))


def test_upsert_and_exact_direction_scores_highest(store):
    written = store.upsert([
        {"key": "Lyrie::mem_1", "vector": E2},
        {"key": "Lyrie::mem_2", "vector": E1},
        {"key": "Lyrie::mem_3", "vector": MIXED},
    ])
    assert written == 3
    results = store.search(E1, character="Lyrie", k=3)
    assert results[0]["key"] == "Lyrie::mem_2"
    assert results[0]["score"] == pytest.approx(1.0, abs=1e-4)
    # Orthogonal vector ranks last with score ~0
    assert results[-1]["key"] == "Lyrie::mem_1"
    assert results[-1]["score"] == pytest.approx(0.0, abs=1e-6)


def test_scaled_vector_same_direction(store):
    store.upsert([{"key": "A::m", "vector": E1_SCALED}])
    assert store.search(E1)[0]["score"] == pytest.approx(1.0, abs=1e-4)


def test_character_filter_excludes_others(store):
    store.upsert([
        {"key": "Lyrie::mem_1", "vector": E1},
        {"key": "Miki::mem_9", "vector": E1},
    ])
    hits = store.search(E1, character="Miki")
    assert [h["key"] for h in hits] == ["Miki::mem_9"]
    assert len(store.search(E1)) == 2


def test_dimension_mismatch_rejected_and_file_unharmed(store):
    store.upsert([{"key": "A::m1", "vector": E1}])
    with pytest.raises(ValueError):
        store.upsert([{"key": "A::m2", "vector": [1.0, 2.0, 3.0]}])
    # Original data still intact and searchable
    assert store.known_keys() == ["A::m1"]


def test_zero_vector_query_returns_nothing(store):
    store.upsert([{"key": "A::m1", "vector": E1}])
    assert store.search([0.0, 0.0]) == []


def test_remove_character_keeps_others(store):
    store.upsert([
        {"key": "Lyrie::mem_1", "vector": E1},
        {"key": "Miki::mem_9", "vector": E1},
    ])
    assert store.remove_character("Lyrie") == 1
    assert store.known_keys() == ["Miki::mem_9"]
    assert store.remove_character("Nobody") == 0


def test_persistence_across_instances(tmp_path):
    VectorStore(str(tmp_path)).upsert(
        [{"key": "Kael::mem_7", "vector": MIXED}], model="nomic-embed-text")
    again = VectorStore(str(tmp_path))
    assert again.stats()["model"] == "nomic-embed-text"
    assert again.search(MIXED)[0]["key"] == "Kael::mem_7"


def test_corrupt_file_falls_back_to_empty(tmp_path):
    path = tmp_path / "embeddings.json"
    path.write_text("{ not json ]", encoding="utf-8")
    store = VectorStore(str(tmp_path))
    assert store.stats()["count"] == 0
    store.upsert([{"key": "A::m", "vector": E1}])
    assert VectorStore(str(tmp_path)).stats()["count"] == 1


# --- Route-level integration -------------------------------------------------

def _client_with_data_dir(tmp_path):
    from app import create_app
    data_dir = str(tmp_path)
    app = create_app({"TESTING": True, "DATA_DIR": data_dir})
    app.config["DATA_DIR"] = data_dir
    return app.test_client()


def test_embedding_routes_round_trip(tmp_path):
    client = _client_with_data_dir(tmp_path)
    r = client.post("/api/memory/embeddings", json={
        "items": [{"key": "Lyrie::mem_1", "vector": E1}],
        "model": "test-model"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["written"] == 1
    assert body["stats"]["model"] == "test-model"

    r = client.post("/api/memory/embeddings/search",
                    json={"character": "Lyrie", "vector": E1, "k": 1})
    hits = r.get_json()["results"]
    assert hits[0]["memory_id"] == "mem_1"
    assert hits[0]["character"] == "Lyrie"

    stats = client.get("/api/memory/embeddings/stats").get_json()
    assert stats["count"] == 1


def test_embedding_route_dimension_conflict_is_409(tmp_path):
    client = _client_with_data_dir(tmp_path)
    client.post("/api/memory/embeddings",
                json={"items": [{"key": "A::m", "vector": E1}]})
    r = client.post("/api/memory/embeddings",
                    json={"items": [{"key": "B::m", "vector": [1.0, 2.0, 3.0]}]})
    assert r.status_code == 409


def test_clearing_memories_also_drops_vectors(tmp_path):
    client = _client_with_data_dir(tmp_path)
    app = client.application
    player = app.world.players.get(list(app.world.players.keys())[0]) if app.world.players else None
    if player is None:
        pytest.skip("no players in default world fixture")
    name = getattr(player, "name", None) or list(app.world.players.keys())[0]

    client.post(f"/api/players/{name}/memories/entry",
                json={"text": "test memory", "id": "mem_vec_test"})
    client.post("/api/memory/embeddings", json={
        "items": [{"key": f"{name}::mem_vec_test", "vector": E1}]})
    assert client.get("/api/memory/embeddings/stats").get_json()["count"] == 1

    client.post(f"/api/players/{name}/memories/clear")
    assert client.get("/api/memory/embeddings/stats").get_json()["count"] == 0
