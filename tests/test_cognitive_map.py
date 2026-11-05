"""Unit tests for task-736: Per-character cognitive map: belief-based place and route memory."""

import pytest
from app import create_app
from player import Player
from graph import WorldGraph, Node, Edge, EDGE_CONNECTION
from engine.spatial_memory import SpatialMemory


@pytest.fixture
def test_world():
    graph = WorldGraph()
    # Create 3 areas: A, B, C
    # A <-> Way_AB <-> B
    # B <-> Way_BC <-> C
    a = Node(id="area_a", type="area", name="Town Square")
    b = Node(id="area_b", type="area", name="Market Street")
    c = Node(id="area_c", type="area", name="Secret Garden")
    w_ab = Node(id="way_ab", type="way", name="Archway")
    w_bc = Node(id="way_bc", type="way", name="Iron Gate")

    graph.add_node(a)
    graph.add_node(b)
    graph.add_node(c)
    graph.add_node(w_ab)
    graph.add_node(w_bc)

    # Connections A <-> Way_AB <-> B
    graph.add_edge(Edge(source="area_a", target="way_ab", type=EDGE_CONNECTION, properties={"direction": "north"}))
    graph.add_edge(Edge(source="way_ab", target="area_b", type=EDGE_CONNECTION, properties={"direction": "north"}))
    graph.add_edge(Edge(source="area_b", target="way_ab", type=EDGE_CONNECTION, properties={"direction": "south"}))
    graph.add_edge(Edge(source="way_ab", target="area_a", type=EDGE_CONNECTION, properties={"direction": "south"}))

    # Connections B <-> Way_BC <-> C
    graph.add_edge(Edge(source="area_b", target="way_bc", type=EDGE_CONNECTION, properties={"direction": "east"}))
    graph.add_edge(Edge(source="way_bc", target="area_c", type=EDGE_CONNECTION, properties={"direction": "east"}))
    graph.add_edge(Edge(source="area_c", target="way_bc", type=EDGE_CONNECTION, properties={"direction": "west"}))
    graph.add_edge(Edge(source="way_bc", target="area_b", type=EDGE_CONNECTION, properties={"direction": "west"}))

    return graph


def test_cognitive_map_shows_only_characters_known_places(test_world):
    p_alice = Player("Alice")
    p_alice.current_area = "Town Square"
    # Alice knows Town Square and Market Street, but NOT Secret Garden
    p_alice.known_areas = {"Town Square", "Market Street"}
    p_alice.learn_way_aspect("Town Square", "north", "clear")

    sm = SpatialMemory(test_world)
    alice_map = sm.build_cognitive_map(p_alice)

    # Alice sees Town Square and Market Street
    area_names = {a["name"] for a in alice_map["areas"]}
    assert "Town Square" in area_names
    assert "Market Street" in area_names
    # Unvisited and unknown Secret Garden does NOT appear
    assert "Secret Garden" not in area_names

    # Way AB is included
    assert alice_map["known_way_count"] == 1
    assert alice_map["ways"][0]["id"] == "way_ab"

    # Character Bob only knows Town Square
    p_bob = Player("Bob")
    p_bob.current_area = "Town Square"
    p_bob.known_areas = {"Town Square"}

    bob_map = sm.build_cognitive_map(p_bob)
    bob_area_names = {a["name"] for a in bob_map["areas"]}
    assert bob_area_names == {"Town Square"}
    assert bob_map["known_way_count"] == 0


def test_recall_route_honest_negative(test_world):
    p = Player("Alice")
    p.current_area = "Town Square"
    # Alice knows Town Square and Market Street
    p.known_areas = {"Town Square", "Market Street"}

    sm = SpatialMemory(test_world)

    # Route to known Market Street succeeds
    route_to_b = sm.recall_route(p, "Market Street")
    assert route_to_b is not None
    assert len(route_to_b) == 1
    assert route_to_b[0]["to"] == "Market Street"

    # Route to Secret Garden returns honest negative (None) despite being in ground truth world graph
    route_to_c = sm.recall_route(p, "Secret Garden")
    assert route_to_c is None


def test_cognitive_map_api_endpoints():
    app = create_app({"TESTING": True})
    client = app.test_client()

    p = Player("Lyra")
    p.current_area = "area_a"
    p.known_areas = {"Town Square"}
    app.world.players["Lyra"] = p

    # GET cognitive map
    resp = client.get("/api/players/Lyra/memories/cognitive_map")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["character"] == "Lyra"
    assert "areas" in data
    assert "ways" in data

    # POST recall route for unknown area returns honest negative
    route_resp = client.post("/api/players/Lyra/memories/recall_route", json={"target": "Forbidden Crypt"})
    assert route_resp.status_code == 200
    r_data = route_resp.get_json()
    assert r_data["found"] is False
    assert r_data["route"] is None
