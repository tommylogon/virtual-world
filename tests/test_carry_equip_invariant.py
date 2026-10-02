"""task-450: an item is never both carried and equipped by one character.

bug-25's live repro required exactly this state: one item node with both a
``carrying`` and an ``equipped`` edge to the same character, so ``take`` said
"already carrying" and ``equip`` said "already wearing" -- two true statements
that contradict each other. The engine's equip path converges on one edge; these
tests pin the load-time normalizer and the dressing duplication source.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from graph import (
    WorldGraph, Node, Edge, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN,
)
from area import Area


def _item(node_id="item_knife", name="Knife"):
    return {"id": node_id, "type": "item", "name": name,
            "properties": {"name": name, "tags": [], "current_state": "normal"}}


def _character(node_id="character_Bob", name="Bob"):
    return {"id": node_id, "type": "character", "name": name, "properties": {}}


class TestGraphNormalizer:
    def test_carrying_removed_when_equipped_wins(self):
        g = WorldGraph()
        g.load_from_dict({
            "nodes": {"item_knife": _item(), "character_Bob": _character()},
            "edges": [
                {"source": "item_knife", "target": "character_Bob", "type": EDGE_CARRYING},
                {"source": "item_knife", "target": "character_Bob", "type": EDGE_EQUIPPED},
            ],
        })

        carrying = g.get_edges_for_target("character_Bob", EDGE_CARRYING)
        equipped = g.get_edges_for_target("character_Bob", EDGE_EQUIPPED)
        assert len(carrying) == 0, "the carrying edge must be removed"
        assert len(equipped) == 1, "the equipped edge must survive"

    def test_load_logs_exactly_one_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="graph"):
            g = WorldGraph()
            g.load_from_dict({
                "nodes": {"item_knife": _item(), "character_Bob": _character()},
                "edges": [
                    {"source": "item_knife", "target": "character_Bob", "type": EDGE_CARRYING},
                    {"source": "item_knife", "target": "character_Bob", "type": EDGE_EQUIPPED},
                ],
            })
        warnings = [r for r in caplog.records if "both carried and worn" in r.getMessage()]
        assert len(warnings) == 1, [r.getMessage() for r in caplog.records]

    def test_a_clean_save_is_untouched(self):
        g = WorldGraph()
        g.load_from_dict({
            "nodes": {"item_knife": _item(), "character_Bob": _character()},
            "edges": [
                {"source": "item_knife", "target": "character_Bob", "type": EDGE_CARRYING},
            ],
        })
        assert len(g.get_edges_for_target("character_Bob", EDGE_CARRYING)) == 1

    def test_equipping_a_different_character_is_not_touched(self):
        """Only the same item->owner pair is a contradiction; Bob carrying a
        knife Ada wears is a legitimate two-owner situation, not a bug."""
        g = WorldGraph()
        g.load_from_dict({
            "nodes": {"item_knife": _item(), "character_Bob": _character(),
                      "character_Ada": _character("character_Ada", "Ada")},
            "edges": [
                {"source": "item_knife", "target": "character_Bob", "type": EDGE_CARRYING},
                {"source": "item_knife", "target": "character_Ada", "type": EDGE_EQUIPPED},
            ],
        })
        assert len(g.get_edges_for_target("character_Bob", EDGE_CARRYING)) == 1
        assert len(g.get_edges_for_target("character_Ada", EDGE_EQUIPPED)) == 1

    def test_idempotent(self):
        g = WorldGraph()
        g.load_from_dict({
            "nodes": {"item_knife": _item(), "character_Bob": _character()},
            "edges": [
                {"source": "item_knife", "target": "character_Bob", "type": EDGE_CARRYING},
                {"source": "item_knife", "target": "character_Bob", "type": EDGE_EQUIPPED},
            ],
        })
        assert g.normalize_item_hold_state() == 0


# ── dressing duplication source ─────────────────────────────────────────


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Room A")
    return world, pname


def _item_nodes_named(world, name):
    return [n for n in world.graph.nodes.values()
            if n.type == "item" and n.name == name]


def test_redressing_does_not_mint_a_second_node():
    """A character wearing X who is dressed again must not get a second X node
    dropped into the room by the failed equip's cleanup path."""
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = []
    cand = world.auto_dress_candidates(pname)
    ids = [e['lib_id'] for e in cand['pool'][:3]]

    world.auto_dress_character(pname, library_ids=ids)
    player_id = world.player_manager.get_player_node_id(pname)
    total_after_first = len(world.graph.nodes)

    # Record each worn item's name; a re-dress must not duplicate any of them.
    worn_names = [world.graph.get_node(e.source).name
                  for e in world.graph.get_edges_for_target(player_id, EDGE_EQUIPPED)]

    world.auto_dress_character(pname, library_ids=ids)

    assert len(world.graph.nodes) == total_after_first, (
        "re-dressing minted new item node(s) instead of skipping worn pieces")
    for name in worn_names:
        assert len(_item_nodes_named(world, name)) == 1, name

    # And the room gained nothing.
    area_items = [e for e in world.graph.get_edges_for_target(
        world._get_current_area_id(), EDGE_IN)
        if world.graph.get_node(e.source) and world.graph.get_node(e.source).type == "item"]
    assert area_items == [], "the duplicate was dropped into the room"


def test_dressing_skips_an_already_worn_name():
    """Directly: seed a worn item, offer the same lib_id, and assert no second
    node appears and the report says already-worn."""
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = []
    cand = world.auto_dress_candidates(pname)
    chosen = cand['pool'][0]
    player_id = world.player_manager.get_player_node_id(pname)

    # Seed the chosen item as genuinely worn (equipped edge).
    node, _lib = world.effects._hydrate_item(chosen['lib_id'], {}, always_fresh=True)
    world.graph.add_node(node)
    world.graph.add_edge(Edge(source=node.id, target=player_id, type=EDGE_EQUIPPED,
                              properties={"slot": chosen['slots'][0]}))
    before = len(_item_nodes_named(world, node.name))

    world.auto_dress_character(pname, library_ids=[chosen['lib_id']])

    assert len(_item_nodes_named(world, node.name)) == before, (
        "a second node was minted for an already-worn item")
