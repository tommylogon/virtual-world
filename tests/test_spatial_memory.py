"""Tests for SpatialMemory route building from visited_areas + real graph."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import WorldGraph, Node, Edge, EDGE_CONNECTION
from engine.spatial_memory import SpatialMemory


def make_graph():
    """Small graph: Living Area --north--> Hallway --east--> Study.

    Connections go area -> way (with direction) and way -> area (direction='enter').
    """
    g = WorldGraph()
    nodes = [
        Node(id="area_living_area", type="area", name="Living Area"),
        Node(id="area_hallway", type="area", name="Hallway"),
        Node(id="area_study", type="area", name="Study"),
        Node(id="area_cellar", type="area", name="Cellar"),
    ]
    for n in nodes:
        g.add_node(n)

    ways = [
        Node(id="way_la_hall_north", type="way", name="Living Area-north"),
        Node(id="way_hall_study_east", type="way", name="Hallway-east"),
        Node(id="way_la_cellar_south", type="way", name="Living Area-south"),
    ]
    for w in ways:
        g.add_node(w)

    g.add_edge(Edge(source="area_living_area", target="way_la_hall_north", type=EDGE_CONNECTION, properties={"direction": "north"}))
    g.add_edge(Edge(source="way_la_hall_north", target="area_hallway", type=EDGE_CONNECTION, properties={"direction": "enter"}))
    g.add_edge(Edge(source="area_hallway", target="way_hall_study_east", type=EDGE_CONNECTION, properties={"direction": "east"}))
    g.add_edge(Edge(source="way_hall_study_east", target="area_study", type=EDGE_CONNECTION, properties={"direction": "enter"}))
    g.add_edge(Edge(source="area_living_area", target="way_la_cellar_south", type=EDGE_CONNECTION, properties={"direction": "south"}))
    g.add_edge(Edge(source="way_la_cellar_south", target="area_cellar", type=EDGE_CONNECTION, properties={"direction": "enter"}))
    return g


def test_routes_only_include_visited_areas():
    g = make_graph()
    sm = SpatialMemory(g)
    # Visited stores AREA NAMES (movement.py:231), not node ids
    block = sm.build_known_routes("Living Area", {"Living Area", "Hallway"})
    assert "KNOWN ROUTES FROM HERE" in block
    assert "Hallway" in block
    assert "Study" not in block
    assert "Cellar" not in block


def test_routes_include_direction_steps():
    g = make_graph()
    sm = SpatialMemory(g)
    block = sm.build_known_routes("Living Area", {"Living Area", "Hallway"}, max_depth=2)
    assert "north" in block
    assert "Hallway" in block


def test_deep_route_includes_direction_arrow():
    g = make_graph()
    sm = SpatialMemory(g)
    block = sm.build_known_routes(
        "Living Area",
        {"Living Area", "Hallway", "Study"},
        max_depth=2,
    )
    assert "→" in block
    assert "north → east" in block


def test_no_routes_when_nothing_visited():
    g = make_graph()
    sm = SpatialMemory(g)
    block = sm.build_known_routes("Living Area", set())
    assert block == ""


def test_no_routes_for_unknown_current_area():
    g = make_graph()
    sm = SpatialMemory(g)
    block = sm.build_known_routes("Nowhere", {"Living Area"})
    assert block == ""


def test_deep_route_included_with_max_depth():
    g = make_graph()
    sm = SpatialMemory(g)
    # Visit all four areas — Study is 2 hops from Living Area
    block = sm.build_known_routes(
        "Living Area",
        {"Living Area", "Hallway", "Study"},
        max_depth=2,
    )
    assert "Study" in block
    assert "north" in block
    assert "east" in block
