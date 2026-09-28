"""Item ``quantity`` and pooled resource nodes (task-504).

One item node can stand for *many of the same kind*. That is mostly a
presentation win — "1 giant tree" and "40 berries" read correctly, and one
node is far cheaper than hundreds — but underneath it is the **pooled
resource node**: a bush, thicket or tree that yields real item copies when
taken from and depletes as it goes.

The distinction this file exists to pin down is between the two counters:

- ``uses``    — charges left on *this copy* (a lantern's fuel, an apple's bites)
- ``quantity`` — how many *of this kind* the node stands for

A stack of 40 berries is not one berry with 40 charges, and a tree standing in
a forest is not something you can carry at all.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from graph import EDGE_CARRYING, EDGE_IN, Edge, Node
from engine.room_perception import (
    MAX_ITEM_QUANTITY,
    describe_item,
    describe_item_quantity,
    item_quantity,
    pluralise,
)

AREA = "Deep Forest"


# ── the pure property ────────────────────────────────────────────────────────

def _item(name, **props):
    return Node(id=f"item_{name}", type="item", name=name,
                properties={"current_state": "normal", **props})


def test_absent_quantity_reads_as_one():
    assert item_quantity(_item("iron key")) == 1
    assert item_quantity(_item("iron key", quantity=1)) == 1


def test_quantity_is_read_from_the_node():
    assert item_quantity(_item("berry bush", quantity=40)) == 40
    assert item_quantity(_item("berry bush", quantity="12")) == 12


def test_quantity_is_capped():
    """A generator handing out nonsense must not print six digits."""
    assert item_quantity(_item("gravel bank", quantity=10 ** 9)) == MAX_ITEM_QUANTITY


def test_junk_quantity_reads_as_one():
    """A drained pool is removed from the world, not rendered "0 berries"."""
    for junk in (0, -5, "many", None, [], {}):
        assert item_quantity(_item("berry bush", quantity=junk)) == 1, junk


def test_missing_node_is_empty_not_an_error():
    assert item_quantity(None) == 1
    assert describe_item_quantity(None) == ""
    assert describe_item(None) == ""


# ── pluralisation ────────────────────────────────────────────────────────────

def test_pluralise_keeps_the_singular_at_one():
    assert pluralise("berry", 1) == "berry"


def test_pluralise_appends_s_by_default():
    """The naive fallback. Anything irregular is authored, never guessed."""
    assert pluralise("berry", 3) == "berrys"
    assert pluralise("apple", 2) == "apples"
    assert pluralise("apple", 1) == "apple"


def test_an_authored_plural_beats_the_fallback():
    assert pluralise("berry", 3, "berries") == "berries"


def test_irregular_plurals_are_authored_not_guessed():
    """1 mouse / 3 mice — the item authors it, the renderer never guesses."""
    mouse = _item("mouse", quantity=3, plural="mice")
    assert describe_item_quantity(mouse) == "3 mice"
    assert describe_item_quantity(_item("mouse")) == "mouse"


def test_an_authored_count_is_shown_even_at_one():
    """"you see 1 giant tree" — the prose stays uniform with "40 berries"."""
    assert describe_item_quantity(_item("giant tree", quantity=1)) == "1 giant tree"


def test_an_unauthored_count_is_never_invented():
    assert describe_item_quantity(_item("iron key")) == "iron key"
    assert describe_item_quantity(_item("berry", quantity=1)) == "1 berry"


def test_a_pool_reads_as_a_counted_plural():
    assert describe_item_quantity(_item("berry", quantity=40, plural="berries")) == "40 berries"
    assert describe_item_quantity(_item("berry bush", quantity=3, plural="berry bushes")) \
        == "3 berry bushes"


# ── the description line ─────────────────────────────────────────────────────

def test_describe_item_joins_label_and_description():
    node = _item("berry", quantity=40, plural="berries")
    assert describe_item(node, "dark fruit on low canes.") \
        == "40 berries, dark fruit on low canes."


def test_a_plain_item_reads_without_a_number():
    assert describe_item(_item("iron key"), "rusted but whole.") == "iron key, rusted but whole."


def test_a_quantity_token_in_the_description_does_the_counting():
    """When the prose does the counting the label drops its own number, or
    "a thicket of {qty} of them heavy with fruit" would read the count twice."""
    node = _item("wild berry thicket", quantity=7,
                 description="a dense thicket, {qty} of them heavy with fruit.")
    assert describe_item(node, node.properties["description"]) \
        == "a dense thicket, 7 of them heavy with fruit."


def test_a_name_token_resolves_to_the_stored_singular():
    node = _item("berry", quantity=3, description="{qty} clusters of {name}.")
    assert describe_item(node, node.properties["description"]) == "3 clusters of berry."


# ── the two perception paths agree ───────────────────────────────────────────

def test_both_perception_paths_render_a_pool_identically():
    from engine.area_description import AreaDescription
    from engine.scene_snapshot import build_scene
    from player import Player
    from unittest.mock import MagicMock

    g = __import__("graph").WorldGraph()
    g.add_node(Node(id="area_deep_forest", type="area", name=AREA,
                    properties={"environment": {"light": 90}, "description": "trees."}))
    g.add_node(_item("berry", quantity=40, plural="berries",
                     description="heavy with fruit."))
    g.add_edge(Edge(source="item_berry", target="area_deep_forest", type=EDGE_IN))

    jake = Player("jake halloway")
    jake.current_area = AREA
    pm = MagicMock()
    pm.players = {"jake halloway": jake}
    pm.active_player = "jake halloway"
    pm.current_area = MagicMock()
    pm.current_area.name = AREA
    pm.is_slasher = MagicMock(return_value=False)
    pm.get_active_player_obj = MagicMock(return_value=jake)

    lighting = MagicMock()
    lighting.get_ambient_light = MagicMock(return_value=90)
    ad = AreaDescription(g, lighting, pm, item_actions=None)

    world = MagicMock()
    world.graph = g
    world.player_manager = pm
    world.area_node_id = lambda name: f"area_{name.lower().replace(' ', '_')}"
    world.lighting = lighting
    world.area_description = ad
    world._get_available_actions = MagicMock(return_value=[])
    world.name_matcher.way_handle = MagicMock(
        side_effect=lambda way, d, area: d or way.name)

    agent_items = ad.get_area_items()
    scene = build_scene(world, "jake halloway")

    assert agent_items == ["40 berries"], agent_items
    assert [i["name"] for i in scene["items"]] == agent_items
    assert scene["items"][0]["quantity"] == 40


# ── the pool: taking from it ─────────────────────────────────────────────────

def _world():
    from virtual_world_engine import VirtualWorld
    w = VirtualWorld()
    w.time_per_tick_minutes = 1
    w.movement.add_area(Area(AREA, "Tall trees and undergrowth.", []))
    w.name_matcher._set_player_area(w.active_player, AREA)
    return w


def _place(w, library_id):
    node, _lib = w.effects._hydrate_item(library_id, {}, always_fresh=True)
    w.graph.add_edge(Edge(source=node.id, target=w.get_current_area_id(), type=EDGE_IN))
    return node


def _skilled(w):
    """A harvester who passes the pool's Survival check.

    The real check is a roll; these tests are about the *cap* and the
    *decrement*, so the roll is pinned rather than left to chance.
    ``take_item`` is handed the world as its player manager, so that is where
    the check has to be stubbed.
    """
    w.skill_check = lambda name, dc: (True, dc + 10, "")
    return w


def _unskilled(w):
    """A harvester who fails it — the yield drops to a scanty handful."""
    w.skill_check = lambda name, dc: (False, 1, "you fumble")
    return w


def _carried(w, library_id="berries"):
    player_id = w.player_manager.get_player_node_id(w.player_manager.active_player)
    out = []
    for edge in w.graph.get_edges_for_target(player_id, EDGE_CARRYING):
        node = w.graph.get_node(edge.source)
        if node and node.properties.get("library_id") == library_id:
            out.append(node)
    return out


def test_an_unpooled_item_is_taken_whole_as_before():
    """The whole point of an absent `quantity`: nothing changes."""
    w = _world()
    key = _place(w, "iron_key")
    before = w.graph.get_node(key.id)
    w.take_item("iron key")
    assert w.graph.get_node(key.id) is not None, "an ordinary item must still be picked up"


def test_a_pool_yields_real_copies_and_decrements():
    w = _skilled(_world())
    pool = _place(w, "berry_thicket")
    start = item_quantity(pool)
    assert start > 1

    w.take_item("1 berries")
    assert item_quantity(pool) == start - 1
    assert len(_carried(w)) == 1, "one find is one real berries node"


def test_take_n_yields_n_and_leaves_the_rest():
    w = _skilled(_world())
    pool = _place(w, "berry_thicket")
    start = item_quantity(pool)

    w.take_item("3 berries")
    assert item_quantity(pool) == start - 3
    assert len(_carried(w)) == 3


def test_an_over_take_is_capped_by_what_the_pool_holds():
    w = _skilled(_world())
    pool = _place(w, "berry_thicket")
    start = item_quantity(pool)
    size = pool.properties["harvest"]["size"]
    assert start >= size

    w.take_item("99 berries")
    assert len(_carried(w)) == size, "a harvest is a bounded handful"
    assert item_quantity(pool) == start - size


def test_the_check_decides_how_much_not_whether():
    """Harvest is skill-gated: the check scales the yield, it does not gate
    the attempt. A failed check still nets a scanty handful."""
    w = _unskilled(_world())
    pool = _place(w, "berry_thicket")
    start = item_quantity(pool)

    w.take_item("3 berries")
    assert len(_carried(w)) == 1, "a failed check comes away with one"
    assert item_quantity(pool) == start - 1


def test_a_failed_check_cannot_empty_a_pool():
    w = _unskilled(_world())
    pool = _place(w, "berry_thicket")
    start = item_quantity(pool)
    for _ in range(3):
        w.take_item("3 berries")
    assert item_quantity(pool) == start - 3 > 0
    assert len(_carried(w)) == 3


def test_an_ask_for_more_than_one_without_a_count_is_one():
    w = _skilled(_world())
    pool = _place(w, "berry_thicket")
    w.take_item("berries")
    assert len(_carried(w)) == 1


def test_taking_the_last_unit_removes_the_pool():
    w = _world()
    pool = _place(w, "berry_thicket")
    pool.properties["quantity"] = 1
    pool.properties["harvest"] = dict(pool.properties["harvest"], size=1)

    w.take_item("1 berries")
    assert w.graph.get_node(pool.id) is None, "an emptied pool leaves the world"
    assert len(_carried(w)) == 1


def test_a_pool_is_never_picked_up_whole():
    w = _world()
    pool = _place(w, "berry_thicket")
    w.take_item("wild berry thicket")
    carried_ids = {e.source for e in w.graph.get_edges_for_target(
        w.player_manager.get_player_node_id(w.player_manager.active_player), EDGE_CARRYING)}
    assert pool.id not in carried_ids, "a thicket does not fit in a pack"


def test_a_pool_with_no_yield_is_refused_rather_than_taken():
    """The bug task-504 names: a whole apple tree must not be carryable."""
    w = _world()
    tree = _place(w, "apple_tree")
    tree.properties["harvest"] = {}
    tree.properties["quantity"] = 3
    try:
        w.take_item("apple tree")
    except ValueError as exc:
        assert "rooted" in str(exc).lower()
    else:
        raise AssertionError("a yieldless pool must not be pickable")
    assert w.graph.get_node(tree.id) is not None


def test_a_standing_pool_keeps_giving_after_the_first_pick():
    """"already carrying" must not short-circuit a second harvest."""
    w = _skilled(_world())
    pool = _place(w, "berry_thicket")
    start = item_quantity(pool)

    for _ in range(3):
        w.take_item("3 berries")
    assert len(_carried(w)) == 9
    assert item_quantity(pool) == start - 9


def test_a_still_held_ordinary_item_is_still_a_no_op():
    """The pool exception must not weaken the ordinary 'already carrying'."""
    w = _world()
    key = _place(w, "iron_key")
    w.take_item("iron key")
    assert "already" in w.take_item("iron key").lower()
    assert w.graph.get_node(key.id) is not None


def test_the_apple_tree_stands_as_a_pool_of_apples():
    w = _world()
    tree = _place(w, "apple_tree")
    assert item_quantity(tree) == 3
    start = item_quantity(tree)
    w.take_item("1 apple")
    assert item_quantity(tree) == start - 1
    assert len(_carried(w, "apple")) == 1


def test_a_pool_never_stacks_with_a_carried_copy():
    """Stacking is the other direction: many copies merged into one carried
    node. Merging a pool would sum its count into a copy's `uses`."""
    from engine.items.stacking import stackable_twins

    pool = Node(id="pool", type="item", name="berries",
                properties={"library_id": "berries", "actions": ["take"],
                            "quantity": 40, "current_state": "normal"})
    copy = Node(id="copy", type="item", name="berries",
                properties={"library_id": "berries", "actions": ["take"],
                            "current_state": "normal"})
    assert not stackable_twins(pool, copy)
    assert not stackable_twins(copy, pool)
    assert not stackable_twins(pool, pool)


def test_two_ordinary_copies_still_stack():
    from engine.items.stacking import stackable_twins

    a = Node(id="a", type="item", name="berries",
             properties={"library_id": "berries", "actions": ["take"], "current_state": "normal"})
    b = Node(id="b", type="item", name="berries",
             properties={"library_id": "berries", "actions": ["take"], "current_state": "normal"})
    assert stackable_twins(a, b)


# ── the amount parse ─────────────────────────────────────────────────────────

def test_a_leading_count_is_read_as_an_amount():
    from engine.items.take_drop_actions import split_leading_amount

    assert split_leading_amount("3 berries") == (3, "berries")
    assert split_leading_amount("12 wild berries") == (12, "wild berries")
    assert split_leading_amount("berries") == (1, "berries")


def test_a_trailing_number_is_left_alone():
    """``take jumpsuit 2`` is the route's ordinal selection, not an amount."""
    from engine.items.take_drop_actions import split_leading_amount

    assert split_leading_amount("jumpsuit 2") == (1, "jumpsuit 2")


def test_a_bare_number_stays_a_name():
    from engine.items.take_drop_actions import split_leading_amount

    assert split_leading_amount("3") == (1, "3")


# ── library authoring ────────────────────────────────────────────────────────

def test_hydration_keeps_the_pool_properties():
    w = _world()
    pool, lib = w.effects._hydrate_item("berry_thicket", {}, always_fresh=True)
    assert pool.properties["quantity"] == lib["quantity"] > 1
    assert pool.properties["plural"] == "wild berry canes"
    assert pool.properties["harvest"]["item"] == "berries"


def test_the_library_lint_rejects_a_yieldless_pool():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "lint_library", Path(__file__).parent.parent / "tools" / "lint_library.py")
    lint = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lint)

    report = lint.Report()
    lint.check_resource_pools({"thicket": {"quantity": 4}}, report)
    assert any("takeable whole" in message for _check, message in report.errors)

    report = lint.Report()
    lint.check_resource_pools(
        {"thicket": {"quantity": 4, "harvest": {"item": "no_such_item"}}}, report)
    assert any("not in the library" in message for _check, message in report.errors)

    report = lint.Report()
    lint.check_resource_pools(
        {"ok": {"quantity": 4, "harvest": {"item": "berries", "size": 3}},
         "berries": _library_items()["berries"]},
        report)
    assert not [e for e in report.errors if e[0] == "resource_pools"]


def _library_items():
    import json
    lib_dir = Path(__file__).parent.parent / "data" / "library" / "items"
    return {p.stem: json.loads(p.read_text(encoding="utf-8-sig")) for p in lib_dir.glob("*.json")}


# ── save / load ──────────────────────────────────────────────────────────────

def test_quantity_round_trips_a_save():
    """Item properties are serialised verbatim, so a pool survives a real
    save → load cycle without any whitelist for anyone to forget to add."""
    from virtual_world_engine import VirtualWorld

    w = _world()
    pool = _place(w, "berry_thicket")
    pool.properties["quantity"] = 33
    pool.properties["plural"] = "wild berry canes"

    data = w.to_scenario_dict()

    w2 = VirtualWorld()
    w2.load_from_dict(data)
    restored = w2.graph.get_node(pool.id)
    assert restored is not None, "the pool node itself must survive"
    assert restored.properties["quantity"] == 33
    assert restored.properties["plural"] == "wild berry canes"
    assert describe_item_quantity(restored) == "33 wild berry canes"
