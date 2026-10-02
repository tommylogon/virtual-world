"""task-433: agent-reachable, gated, structured inscription.

`use <writing tool> on <writable> "text"` stores `properties.inscriptions`
records instead of overwriting the description. A non-writing tool or a
non-writable target is refused, and ordinary `use X on Y` never inscribes
(task-363 regression).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from graph import Node, Edge, EDGE_CARRYING
from player import Player


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    world.add_player(Player("Author"))
    world.name_matcher._set_player_area("Author", "Room A")
    world.set_active_player("Author")
    return world


def add_carried(world, node_id, name, tags, actions=None, description="", **props):
    node = Node(id=node_id, type="item", name=name, properties={
        "name": name, "weight": 0.1, "current_state": "normal",
        "description": description,
        "actions": actions if actions is not None else ["examine", "take", "use", "drop"],
        "tags": tags,
        **props,
    })
    world.graph.add_node(node)
    world.graph.add_edge(Edge(source=node.id, target=world._player_node_id("Author"),
                              type=EDGE_CARRYING))
    return node


def pen_and_paper(world):
    pen = add_carried(world, "item_pen", "Ink Pen", ["writing", "pen"])
    paper = add_carried(world, "item_parchment", "Parchment",
                        ["writable", "paper", "parchment"],
                        description="A blank sheet.")
    return pen, paper


class TestInscriptionStore:
    def test_writes_a_structured_record(self):
        world = make_world()
        pen, paper = pen_and_paper(world)
        out = world.use_item_on("Ink Pen", "Parchment", params="Meet me at dawn")
        assert "writing" in out.lower()

        records = paper.properties["inscriptions"]
        assert len(records) == 1
        assert records[0]["text"] == "Meet me at dawn"
        assert records[0]["by"] == "Author"
        assert "tick" in records[0]

    def test_description_is_not_overwritten(self):
        world = make_world()
        pen, paper = pen_and_paper(world)
        world.use_item_on("Ink Pen", "Parchment", params="DONT GO HERE")
        assert paper.properties["description"] == "A blank sheet."
        assert "[Inscribed:" not in paper.properties["description"]

    def test_examine_renders_written_here(self):
        world = make_world()
        pen, paper = pen_and_paper(world)
        world.use_item_on("Ink Pen", "Parchment", params="Look behind the well")
        desc = world.get_item_desc("Parchment")
        assert "Written here" in desc
        assert "Look behind the well" in desc
        assert "Author" in desc

    def test_round_trips_through_dict(self):
        world = make_world()
        pen, paper = pen_and_paper(world)
        world.use_item_on("Ink Pen", "Parchment", params="note")
        dumped = paper.to_dict()
        restored = Node(**dumped)
        assert restored.properties["inscriptions"][0]["text"] == "note"


class TestGating:
    def test_non_writing_tool_refused(self):
        world = make_world()
        add_carried(world, "item_crowbar", "Crowbar", ["tool", "metal"])
        add_carried(world, "item_parchment", "Parchment", ["writable", "paper"])
        try:
            world.use_item_on("Crowbar", "Parchment", params="clang")
            assert False, "expected a refusal"
        except ValueError as exc:
            assert "write" in str(exc).lower()

    def test_non_writable_target_refused(self):
        world = make_world()
        add_carried(world, "item_pen", "Ink Pen", ["writing", "pen"])
        add_carried(world, "item_rock", "Rock", ["stone"])
        try:
            world.use_item_on("Ink Pen", "Rock", params="hello")
            assert False, "expected a refusal"
        except ValueError as exc:
            assert "write on" in str(exc).lower()

    def test_ordinary_use_on_never_inscribes(self):
        world = make_world()
        pen, paper = pen_and_paper(world)
        # No params: this is an ordinary `use X on Y` — must not write.
        world.use_item_on("Ink Pen", "Parchment")
        assert "inscriptions" not in paper.properties

    def test_control_chars_stripped_and_length_capped(self):
        world = make_world()
        pen, paper = pen_and_paper(world)
        world.use_item_on("Ink Pen", "Parchment",
                          params=("bad\x00text\n" + "x" * 5000))
        text = paper.properties["inscriptions"][0]["text"]
        assert "\x00" not in text
        assert len(text) <= 2000
