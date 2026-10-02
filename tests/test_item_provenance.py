"""task-514: item provenance (where a carried thing came from).

Provenance lives on the instance node, not the shared template id. It renders as
one bounded line on examine and in the agent prompt, and it is set by authored
templates and by acquisitions (steal, take-from-container). It deliberately does
NOT take part in stack identity.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from graph import Node
from engine.items.provenance import (
    MAX_LINE,
    normalize_provenance,
    render_provenance,
    stamp_provenance,
)
from engine.items.stacking import stackable_twins
from engine.library_nodes import library_item_properties
from engine.room_perception import describe_item

AREA = "Kraktooth Camp"


def test_normalize_accepts_a_string_or_a_dict():
    assert normalize_provenance("Traded from a scout.") == {"text": "Traded from a scout."}
    assert normalize_provenance({"text": "Found.", "source": "a ruined cart"}) == {
        "text": "Found.", "source": "a ruined cart"}
    assert normalize_provenance("") is None
    assert normalize_provenance(None) is None
    assert normalize_provenance({"source": "somewhere"}) is None


def test_render_is_one_bounded_line():
    assert render_provenance("Traded from a scout.") == "Traded from a scout."
    assert render_provenance({"text": "Found it.", "source": "a dead dwarf's boot"}) \
        == "Found it. (from a dead dwarf's boot)"
    assert render_provenance(None) == ""
    long = render_provenance("x" * 400)
    assert len(long) <= MAX_LINE
    assert long.endswith("…")


def test_stamp_sets_only_the_given_fields():
    node = Node(id="i", type="item", name="knife", properties={})
    stamp_provenance(node, text="Stolen from Gribba.", source="Gribba")
    assert node.properties["provenance"] == {"text": "Stolen from Gribba.", "source": "Gribba"}
    stamp_provenance(node, tick=42)
    assert node.properties["provenance"]["tick"] == 42


def test_library_template_provenance_lands_on_the_instance():
    props = library_item_properties(
        {"name": "Wrench", "provenance": "Stolen from a human wagon on the old road."},
        "wrench")
    assert props["provenance"] == {"text": "Stolen from a human wagon on the old road."}


def test_describe_item_appends_a_bounded_provenance_line():
    node = Node(id="i", type="item", name="Mirror",
                properties={"provenance": {"text": "Traded from a scout."}})
    line = describe_item(node, "A little steel mirror.")
    assert "Traded from a scout." in line
    assert line.startswith("Mirror, A little steel mirror.")


def test_provenance_does_not_take_part_in_stack_identity():
    """Two otherwise-identical items with different stories still combine."""
    def _node(nid, prov):
        return Node(id=nid, type="item", name="Bread", properties={
            "library_id": "bread", "actions": "use", "tags": ["food"],
            "current_state": "normal", "equip_slots": [], "max_uses": 0,
            "provenance": {"text": prov},
        })
    assert stackable_twins(_node("a", "baked at home"),
                           _node("b", "looted from a wagon")) is True


# ── acquisition: steal rewrites the story ────────────────────────────────────


def _world():
    from virtual_world_engine import VirtualWorld
    w = VirtualWorld()
    w.movement.add_area(Area(AREA, "Stones and cookfires.", []))
    w.name_matcher._set_player_area(w.active_player, AREA)
    return w


def _gribba(w):
    from player import Player
    from graph import EDGE_CARRYING, EDGE_IN, Edge
    gribba = Player("Gribba")
    gribba.current_area = AREA
    w.player_manager.players["Gribba"] = gribba
    gribba_id = w.player_manager.get_player_node_id("Gribba")
    w.graph.add_edge(Edge(source=gribba_id, target=w.get_current_area_id(), type=EDGE_IN))
    knife, _ = w.effects._hydrate_item("gribbas_good_knife", {}, always_fresh=True)
    w.graph.add_edge(Edge(source=knife.id, target=gribba_id, type=EDGE_CARRYING))
    return gribba, knife


def test_steal_rewrites_provenance():
    w = _world()
    _gribba(w)
    # Find the materialized knife and give it an initial story.
    from graph import EDGE_CARRYING
    knife_id = None
    gribba_id = w.player_manager.get_player_node_id("Gribba")
    for edge in w.graph.get_edges_for_target(gribba_id, EDGE_CARRYING):
        node = w.graph.get_node(edge.source)
        if node and node.properties.get("library_id") == "gribbas_good_knife":
            knife_id = node.id
    assert knife_id, "knife not materialized"
    knife = w.graph.get_node(knife_id)
    knife.properties["provenance"] = {"text": "Gribba's since she was small."}

    w.player_manager.player.skills["Sleight of Hand"] = 30
    w.name_matcher._set_player_area(w.player_manager.active_player, AREA)
    w.steal_item("Gribba's Good Knife", "Gribba")

    prov = knife.properties["provenance"]
    assert prov["text"] == "Stolen from Gribba."
    assert prov["source"] == "Gribba"
