"""Tests for spatial relations in library item `contents` entries.

Verifies that a `relation` keyword on a contained item resolves to the correct
graph edge type (on/under/behind/beside/at) instead of always forcing `in`.
"""
import pytest
from unittest.mock import MagicMock

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BESIDE
from routes.library_routes import (
    _content_ref_id,
    _content_relation,
    graph_add_relation_edge,
    RELATION_EDGE_TYPES,
)


class TestContentRelationResolver:
    def test_string_ref_defaults_to_in(self):
        assert _content_relation("plain_id") == "in"

    def test_dict_ref_reads_relation(self):
        assert _content_relation({"id": "chair_1", "relation": "beside"}) == "beside"
        assert _content_relation({"id": "cup", "relation": "ON"}) == "on"

    def test_dict_ref_without_relation_defaults_to_in(self):
        assert _content_relation({"id": "cup"}) == "in"

    def test_unknown_relation_falls_back_to_default(self):
        assert _content_relation({"id": "x", "relation": "wobble"}) == "in"
        assert _content_relation({"id": "x", "relation": "wobble"}, default="at") == "at"

    def test_ref_id_extracts_from_string_and_dict(self):
        assert _content_ref_id("chair_1") == "chair_1"
        assert _content_ref_id({"id": "chair_1"}) == "chair_1"
        assert _content_ref_id({"name": "Chair", "id": "chair_1"}) == "chair_1"
        assert _content_ref_id({"name": "Chair"}) is None


@pytest.fixture
def world_graph():
    g = WorldGraph()
    g.add_node(Node(id="item_table", type="item", name="table", properties={"name": "table"}))
    return g


class TestGraphRelationEdge:
    def test_in_relation_creates_in_edge(self, world_graph):
        graph_add_relation_edge(world_graph, "register_1", "counter", "in")
        assert any(e.source == "register_1" and e.target == "counter" and e.type == EDGE_IN
                   for e in world_graph.edges)

    def test_on_relation_creates_on_edge(self, world_graph):
        graph_add_relation_edge(world_graph, "register_1", "counter", "on")
        assert any(e.source == "register_1" and e.target == "counter" and e.type == EDGE_ON
                   for e in world_graph.edges)

    def test_beside_relation_creates_beside_edge(self, world_graph):
        graph_add_relation_edge(world_graph, "chair_1", "table", "beside")
        assert any(e.source == "chair_1" and e.target == "table" and e.type == "beside"
                   for e in world_graph.edges)

    def test_default_relation_is_in(self, world_graph):
        graph_add_relation_edge(world_graph, "cup", "table", "")
        assert any(e.source == "cup" and e.target == "table" and e.type == EDGE_IN
                   for e in world_graph.edges)

    def test_relation_edge_replaces_same_type(self, world_graph):
        graph_add_relation_edge(world_graph, "register_1", "counter", "on")
        graph_add_relation_edge(world_graph, "register_1", "counter", "on")
        edges = [e for e in world_graph.edges
                 if e.source == "register_1" and e.target == "counter"]
        assert len(edges) == 1
        assert edges[0].type == EDGE_ON