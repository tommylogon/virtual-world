"""Tests for engine-owned turn order resolution and modes (task-437).

Verifies sequential, random, initiative, and simultaneous turn order resolution,
determinism across rounds, invariance to input order in simultaneous mode,
engine state exposure, and API routes.
"""

from app import create_app
from engine.turn_order import TurnOrderResolver, MODES
from player import Player
from virtual_world_engine import VirtualWorld


def test_turn_order_resolver_sequential():
    chars = {
        "char_z": {"stats": {"DEX": 10}},
        "char_a": {"stats": {"DEX": 10}},
        "char_m": {"stats": {"DEX": 10}},
    }
    resolver = TurnOrderResolver(mode="sequential", seed=42)
    order = resolver.resolve(chars, round_number=0)
    assert order == ["char_a", "char_m", "char_z"]


def test_turn_order_resolver_random_is_deterministic():
    chars = {
        "c1": {}, "c2": {}, "c3": {}, "c4": {}, "c5": {}
    }
    resolver = TurnOrderResolver(mode="random", seed=123)
    order_r0 = resolver.resolve(chars, round_number=0)
    order_r1 = resolver.resolve(chars, round_number=1)

    # Different rounds should produce different shuffles
    assert order_r0 != order_r1 or len(chars) <= 1

    # Same seed and round produces identical shuffle
    resolver_repeat = TurnOrderResolver(mode="random", seed=123)
    assert resolver_repeat.resolve(chars, round_number=0) == order_r0


def test_turn_order_resolver_initiative():
    chars = {
        "dex_low": {"stats": {"DEX": 6}},    # -2 bonus
        "dex_high": {"stats": {"DEX": 18}},  # +4 bonus
        "dex_med": {"stats": {"DEX": 10}},   # +0 bonus
    }
    resolver = TurnOrderResolver(mode="initiative", seed=999)
    order = resolver.resolve(chars, round_number=0)
    rolls = resolver.initiative_rolls

    assert len(order) == 3
    assert len(rolls) == 3
    # First character must have highest roll
    assert rolls[order[0]] >= rolls[order[1]] >= rolls[order[2]]


def test_turn_order_resolver_simultaneous_is_order_invariant():
    chars_normal = {
        "alpha": {}, "beta": {}, "gamma": {}
    }
    chars_reversed = {
        "gamma": {}, "beta": {}, "alpha": {}
    }
    resolver = TurnOrderResolver(mode="simultaneous", seed=42)
    order_normal = resolver.resolve(chars_normal, round_number=0)
    order_reversed = resolver.resolve(chars_reversed, round_number=0)

    # Input roster dict iteration order does not alter output order
    assert order_normal == order_reversed == ["alpha", "beta", "gamma"]


def test_engine_turn_order_integration():
    world = VirtualWorld()
    world.players.clear()
    world.turn_order_mode = "sequential"

    p1 = Player("Alice")
    p1.id = "id_alice"
    p2 = Player("Bob")
    p2.id = "id_bob"

    world.add_player(p1)
    world.add_player(p2)

    order_ids = world.get_turn_order_ids()
    assert order_ids == ["id_alice", "id_bob"]

    order_players = world.get_turn_order()
    assert [p.id for p in order_players] == ["id_alice", "id_bob"]

    info = world.get_turn_order_info()
    assert info["mode"] == "sequential"
    assert info["order"] == ["id_alice", "id_bob"]


def test_turn_order_api_routes():
    app = create_app({"TESTING": True})
    client = app.test_client()

    # GET /api/turn/order
    resp_get = client.get("/api/turn/order")
    assert resp_get.status_code == 200
    data = resp_get.get_json()
    assert "mode" in data
    assert "order" in data

    # POST /api/turn/order updates mode
    resp_post = client.post("/api/turn/order", json={"mode": "initiative"})
    assert resp_post.status_code == 200
    data_post = resp_post.get_json()
    assert data_post["mode"] == "initiative"
    assert app.world.turn_order_mode == "initiative"

    # Invalid mode returns 400
    resp_invalid = client.post("/api/turn/order", json={"mode": "invalid_mode"})
    assert resp_invalid.status_code == 400
