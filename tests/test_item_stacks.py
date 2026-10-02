"""task-473: homogeneous stacks (draw one, merge on put) and relational piles.

The homogeneous stack is one world node carrying N ``uses`` behind an explicit
``stackable`` marker: taking draws a discrete copy and decrements, putting a
matching piece back merges it. The relational pile is a container holding
distinct child items (the existing `contents`/EDGE_IN model).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import MagicMock

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
from engine.item_actions import ItemActions
from engine.items.stacking import is_stackable, stackable_twins


def make_graph():
    g = WorldGraph()
    g.add_node(Node(id="area_test", type="area", name="Test",
                    properties={"environment": {"light": 80}}))
    g.add_node(Node(id="player_Hero", type="character", name="Hero", properties={}))
    g.add_edge(Edge(source="player_Hero", target="area_test", type=EDGE_IN))
    return g


def make_actions(g, active="Hero"):
    pm = MagicMock()
    pm.graph = g
    pm.active_player = active
    pm.current_area = MagicMock()
    pm.current_area.name = "Test"
    pm.ghost_mode = False
    pm.record_turn_event = MagicMock()
    pm.apply_action = MagicMock()
    hero = MagicMock()
    hero.name = active
    hero.state = "awake"
    hero.vitals = {}
    hero.exhaustion_count = 0
    pm.players = {active: hero}
    pm.player = hero
    pm._get_current_area_id = lambda: "area_test"
    pm._player_node_id = lambda name: f"player_{name}"
    pm.get_player_node_id = lambda name: f"player_{name}"

    def _find(name):
        for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
            for e in g.get_edges_for_target(f"player_{active}", edge_type):
                n = g.get_node(e.source)
                if n and n.name == name:
                    return n
        for e in g.get_edges_for_target("area_test", EDGE_IN):
            n = g.get_node(e.source)
            if n and n.name == name:
                return n
        return None

    pm.find_item_node = _find

    ia = ItemActions.__new__(ItemActions)
    ia.graph = g
    ia.matching = MagicMock()
    ia.matching._match_item_name = MagicMock(return_value=None)
    ia.matching.match_item_name_in_inventory = MagicMock(return_value=None)
    ia.matching._is_item_reachable = MagicMock(return_value=True)
    ia.trigger_system = MagicMock()
    ia.trigger_system._execute_triggers = MagicMock(return_value=[])
    ia.trigger_system._get_available_actions = MagicMock(return_value=[])
    ia.trigger_system._contextual_failure = MagicMock(return_value="")
    ia.equipment = MagicMock()
    ia.ghost_system = MagicMock()
    ia.ghost_system.check_ghost_action = MagicMock(return_value=None)
    ia.world = MagicMock()
    return ia, pm


def add_stack(g, node_id, name="Pile of Raw Meat", uses=10, max_uses=10,
              weight=5.0):
    node = Node(id=node_id, type="item", name=name, properties={
        "name": name, "uses": uses, "max_uses": max_uses,
        "base_weight": weight, "weight": weight * (uses / max_uses),
        "stackable": True, "current_state": "normal",
        "actions": ["examine", "take", "drop"], "tags": ["food"],
    })
    g.add_node(node)
    return node


# ── marker ───────────────────────────────────────────────────────────────


class TestStackMarker:
    def test_ordinary_prop_is_not_a_stack(self):
        assert not is_stackable(Node(id="i", type="item", name="Rock", properties={}))

    def test_marked_item_is_a_stack(self):
        n = Node(id="i", type="item", name="Pile", properties={"stackable": True})
        assert is_stackable(n)


# ── take from stack ──────────────────────────────────────────────────────


class TestTakeFromStack:
    def test_take_draws_one_and_decrements(self):
        g = make_graph()
        ia, pm = make_actions(g)
        pile = add_stack(g, "item_pile", uses=10)
        g.add_edge(Edge(source=pile.id, target="area_test", type=EDGE_IN))

        result = ia.take_item(pm, "Pile of Raw Meat")

        assert "take 1" in result
        assert pile.properties["uses"] == 9
        carried = [g.get_node(e.source) for e in
                   g.get_edges_for_target("player_Hero", EDGE_CARRYING)]
        assert any(n.name == "Pile of Raw Meat" for n in carried)
        assert len(carried) == 1, "exactly one discrete unit taken"

    def test_taking_the_last_unit_moves_the_node_whole(self):
        g = make_graph()
        ia, pm = make_actions(g)
        pile = add_stack(g, "item_pile", uses=2)
        g.add_edge(Edge(source=pile.id, target="area_test", type=EDGE_IN))
        ia.take_item(pm, "Pile of Raw Meat")   # uses 2 -> 1, one unit carried
        ia.take_item(pm, "Pile of Raw Meat")   # uses 1: the stack itself is carried
        carried = [e.source for e in g.get_edges_for_target("player_Hero", EDGE_CARRYING)]
        assert "item_pile" in carried
        assert not [e for e in g.get_edges_for_target("area_test", EDGE_IN)
                    if e.source == "item_pile"]

    def test_take_amount_capped_at_remaining(self):
        g = make_graph()
        ia, pm = make_actions(g)
        pile = add_stack(g, "item_pile", uses=3)
        g.add_edge(Edge(source=pile.id, target="area_test", type=EDGE_IN))
        result = ia.take_item(pm, "5 Pile of Raw Meat")
        assert pile.properties["uses"] == 0
        assert g.get_node("item_pile") is None
        assert "take 3" in result or "took 3" in result


# ── merge on drop ────────────────────────────────────────────────────────


class TestMergeOnDrop:
    def test_dropping_onto_a_matching_stack_merges(self):
        g = make_graph()
        ia, pm = make_actions(g)
        ground = add_stack(g, "item_ground", uses=5)
        g.add_edge(Edge(source=ground.id, target="area_test", type=EDGE_IN))
        held = add_stack(g, "item_held", uses=3)
        g.add_edge(Edge(source=held.id, target="player_Hero", type=EDGE_CARRYING))

        result = ia.drop_item(pm, "Pile of Raw Meat")

        assert "add" in result.lower()
        assert ground.properties["uses"] == 8
        assert g.get_node("item_held") is None, "the moved node is destroyed"
        left = [e for e in g.get_edges_for_target("area_test", EDGE_IN)
                if g.get_node(e.source) and g.get_node(e.source).name == "Pile of Raw Meat"]
        assert len(left) == 1

    def test_dropping_an_unmarked_prop_does_not_merge(self):
        g = make_graph()
        ia, pm = make_actions(g)
        ground = Node(id="item_ground", type="item", name="Rock",
                      properties={"name": "Rock", "uses": -1, "weight": 1,
                                  "current_state": "normal",
                                  "actions": ["examine", "take", "drop"], "tags": []})
        g.add_node(ground)
        g.add_edge(Edge(source=ground.id, target="area_test", type=EDGE_IN))
        held = Node(id="item_held", type="item", name="Rock",
                    properties=dict(ground.properties, uses=-1))
        g.add_node(held)
        g.add_edge(Edge(source=held.id, target="player_Hero", type=EDGE_CARRYING))

        ia.drop_item(pm, "Rock")

        rocks = [g.get_node(e.source) for e in g.get_edges_for_target("area_test", EDGE_IN)
                 if g.get_node(e.source) and g.get_node(e.source).name == "Rock"]
        assert len(rocks) == 2, "ordinary props must not fuse"


# ── merge on put ─────────────────────────────────────────────────────────


class TestMergeOnPut:
    def test_put_into_container_merges_with_a_matching_stack(self):
        g = make_graph()
        ia, pm = make_actions(g)
        box = Node(id="item_box", type="item", name="Crate",
                   properties={"name": "Crate", "tags": ["container"],
                               "current_state": "open", "max_weight_capacity": 100,
                               "uses": -1, "weight": 5,
                               "actions": ["examine", "take", "put", "drop"]})
        g.add_node(box)
        g.add_edge(Edge(source=box.id, target="player_Hero", type=EDGE_CARRYING))
        inside = add_stack(g, "item_inside", uses=6)
        g.add_edge(Edge(source=inside.id, target=box.id, type=EDGE_IN))
        held = add_stack(g, "item_held2", uses=4)
        g.add_edge(Edge(source=held.id, target="player_Hero", type=EDGE_CARRYING))

        result = ia.put_item_in_container(pm, "Pile of Raw Meat", "Crate")

        assert "add" in result.lower()
        assert inside.properties["uses"] == 10
        assert g.get_node("item_held2") is None


# ── split id collision regression ────────────────────────────────────────


class TestSplitIds:
    def test_splitting_twice_does_not_overwrite(self):
        g = make_graph()
        ia, pm = make_actions(g)
        node = add_stack(g, "item_bread", name="Bread", uses=8, max_uses=8)
        g.add_edge(Edge(source=node.id, target="player_Hero", type=EDGE_CARRYING))
        ia.split_item(pm, "Bread")
        ia.split_item(pm, "Bread")
        pieces = [g.get_node(e.source) for e in
                  g.get_edges_for_target("player_Hero", EDGE_CARRYING)]
        assert len(pieces) == 3, "a second split must add a third piece, not overwrite"
        assert len({p.id for p in pieces}) == 3


# ── authored content ─────────────────────────────────────────────────────


class TestAuthoredContent:
    def test_authored_meat_pile_is_a_stack(self):
        import json
        path = Path(__file__).parent.parent / "data" / "library" / "items" / "pile_of_raw_meat.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        assert data["stackable"] is True
        assert data["uses"] == data["max_uses"]

    def test_authored_herb_pile_has_distinct_contents(self):
        import json
        path = Path(__file__).parent.parent / "data" / "library" / "items" / "foraged_herb_pile.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        assert "container" in data["tags"]
        assert len(data["contents"]) >= 2
        assert len(set(data["contents"])) == len(data["contents"])
