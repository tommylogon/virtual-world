"""Tests for spatial edge types (on/under/behind/beside/at) and legacy edge migration."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import (
    WorldGraph, Node, Edge,
    EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT,
    EDGE_CARRYING, EDGE_EQUIPPED,
    SPATIAL_EDGE_TYPES,
    normalize_edge_type, resolve_edge_types,
)


def make_graph():
    g = WorldGraph()
    area = Node(id="area_kitchen", type="area", name="Kitchen")
    table = Node(id="item_table", type="item", name="Table")
    knife = Node(id="item_knife", type="item", name="Knife")
    keys = Node(id="item_keys", type="item", name="Keys")
    lamp = Node(id="item_lamp", type="item", name="Lamp")
    g.add_node(area)
    g.add_node(table)
    g.add_node(knife)
    g.add_node(keys)
    g.add_node(lamp)
    g.add_edge(Edge(source=table.id, target=area.id, type=EDGE_IN))
    g.add_edge(Edge(source=knife.id, target=table.id, type=EDGE_ON))
    g.add_edge(Edge(source=keys.id, target=table.id, type=EDGE_UNDER))
    g.add_edge(Edge(source=lamp.id, target=table.id, type=EDGE_BESIDE))
    return g


def test_spatial_edges_discovered_in_area():
    g = make_graph()
    sources = {e.source for e in g.get_edges_for_target("area_kitchen", EDGE_IN)}
    assert "item_table" in sources
    assert "item_knife" in sources
    assert "item_keys" in sources
    assert "item_lamp" in sources


def test_spatial_edges_not_returned_without_edge_type():
    g = make_graph()
    plain = [e for e in g.edges if e.target == "area_kitchen"]
    assert len(plain) == 1


def test_spatial_edges_pointed_at_area_directly():
    g = make_graph()
    crate = Node(id="item_crate", type="item", name="Crate")
    g.add_node(crate)
    g.add_edge(Edge(source=crate.id, target="area_kitchen", type=EDGE_AT))
    sources = {e.source for e in g.get_edges_for_target("area_kitchen", EDGE_IN)}
    assert "item_crate" in sources


def test_spatial_types_listed_as_present():
    assert SPATIAL_EDGE_TYPES == {EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT}


def test_legacy_edge_normalization():
    g = WorldGraph()
    area = Node(id="area_kitchen", type="area", name="Kitchen")
    item = Node(id="item_box", type="item", name="Box")
    char = Node(id="player_Hero", type="player", name="Hero")
    g.add_node(area)
    g.add_node(item)
    g.add_node(char)
    g.edges = [
        Edge(source=item.id, target=area.id, type="location"),
        Edge(source=item.id, target=char.id, type="location"),
        Edge(source=item.id, target=char.id, type="carried_by"),
        Edge(source=item.id, target=area.id, type="contains"),
    ]
    g.normalize_edges()
    types = {e.type for e in g.edges}
    assert types == {EDGE_IN, EDGE_CARRYING}


def test_normalize_edge_type_maps_legacy_to_modern():
    assert normalize_edge_type("location") == EDGE_IN
    assert normalize_edge_type("contains") == EDGE_IN
    assert normalize_edge_type("carried_by") == EDGE_CARRYING
    assert normalize_edge_type(EDGE_ON) == EDGE_ON
    assert normalize_edge_type("on") == "on"


def test_resolve_edge_types_includes_legacy():
    assert resolve_edge_types(EDGE_IN) == {EDGE_IN, "location", "contains"}
    assert resolve_edge_types(EDGE_CARRYING) == {EDGE_CARRYING, "carried_by", "location"}
