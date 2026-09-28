"""Per-agent fog of war and map knowledge transfer (task-499).

`player.known` already existed and `engine/room_perception.py` already gated on
it — a known way or area is visible even when hidden. **Nothing ever wrote to
it.** The gate was sound and had no key, and these tests are mostly about the
key.

The honesty half matters more than the rendering half: an unaware agent must not
be told about rooms it has never been in, and the way to guarantee that is a
filter on a **list** that a caller can be audited on using, rather than a
redaction of a rendered prompt string.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import fog  # noqa: E402
from engine.beyond_visibility import sightline_run  # noqa: E402
from engine.fog import (  # noqa: E402
    Known,
    fog_view,
    only_known,
    reveal_area,
    reveal_examined,
    reveal_sightline,
    teach_from_map,
    unknown_are_hidden,
)
from graph import EDGE_CONNECTION, Edge, Node, WorldGraph  # noqa: E402


class _Agent:
    """The smallest thing with a `known` list, which is all the module needs."""

    def __init__(self, known=None):
        self.known = list(known or [])


def _area(graph, area_id, name=None, **props):
    graph.add_node(Node(id=area_id, type="area", name=name or area_id,
                        properties=props))
    return graph.get_node(area_id)


def _world(count=4):
    graph = WorldGraph()
    for index in range(count):
        _area(graph, f"area_{index}", f"Room {index}")
    return graph


# ── the key that was missing ───────────────────────────────────────────────


def test_a_fresh_agent_knows_nothing():
    agent = _Agent()
    known = Known(agent)
    assert len(known) == 0
    assert not known.has("area_0")
    assert not known.has("Room 0")


def test_revealing_an_area_teaches_both_its_id_and_its_name():
    """The perception gate matches on either, so a set holding one form leaks
    through the other."""
    graph = _world()
    agent = _Agent()
    reveal_area(agent, graph.get_node("area_0"))
    known = Known(agent)
    assert known.has("area_0")
    assert known.has("Room 0")


def test_revealing_the_same_area_twice_adds_nothing():
    graph = _world()
    agent = _Agent()
    first = reveal_area(agent, graph.get_node("area_0"))
    second = reveal_area(agent, graph.get_node("area_0"))
    assert first and not second
    assert len(Known(agent)) == len(first) == 2, "id and name, not a duplicate"


def test_two_agents_do_not_share_a_known_set():
    graph = _world()
    one, two = _Agent(), _Agent()
    reveal_area(one, graph.get_node("area_0"))
    assert Known(one).has("area_0")
    assert not Known(two).has("area_0"), (
        "fog of war is per agent; a shared set is omniscience"
    )


def test_a_known_set_survives_being_read_by_a_third_party():
    """Two readers, one registry — constructing a Known must not clear it."""
    agent = _Agent()
    Known(agent).reveal("area_0")
    before = list(agent.known)
    Known(agent).has("area_0")
    Known(agent).entries()
    assert agent.known == before


def test_a_known_forms_covers_id_name_and_props():
    graph = _world()
    way = Node(id="way_x", type="way", name="Door",
               properties={"area_from_id": "area_0", "world_scope_id": "zone_0"})
    graph.add_node(way)
    agent = _Agent()
    Known(agent).reveal(way)
    known = Known(agent)
    assert known.has("way_x")
    assert known.has("Door")
    assert known.has("area_0")
    assert known.has("zone_0")


def test_forgetting_a_place_removes_every_form():
    """A node, not a string: knowing the id and the name are two entries, and
    removing one leaves the perception gate still matching on the other."""
    graph = _world()
    agent = _Agent()
    reveal_area(agent, graph.get_node("area_0"))
    dropped = Known(agent).forget(graph.get_node("area_0"))
    assert set(dropped) == {"area_0", "Room 0"}
    assert not Known(agent).has("area_0")
    assert not Known(agent).has("Room 0")
    # A bare string drops exactly that string and nothing it might mean.
    reveal_area(agent, graph.get_node("area_0"))
    assert Known(agent).forget("area_0") == ["area_0"]
    assert Known(agent).has("Room 0"), "the name entry is a separate entry"


# ── the three reveal verbs ─────────────────────────────────────────────────


def test_walking_in_reveals_the_room():
    graph = _world()
    agent = _Agent()
    assert reveal_area(agent, graph.get_node("area_2")) == ["area_2", "Room 2"]


def test_revealing_nothing_is_not_a_crash():
    agent = _Agent()
    assert reveal_area(agent, None) == []
    assert reveal_examined(agent, None) == []
    assert reveal_sightline(agent, WorldGraph(), []) == []


def test_examining_a_way_teaches_where_it_goes():
    """A way is only ever described in terms of where it goes, so examining one
    teaches the far side."""
    graph = WorldGraph()
    _area(graph, "area_a", "A")
    _area(graph, "area_b", "B")
    graph.add_node(Node(id="way_x", type="way", name="Door",
                        properties={"current_state": "open"}))
    for source, target in (("area_a", "way_x"), ("way_x", "area_b")):
        graph.add_edge(Edge(source=source, target=target, type=EDGE_CONNECTION,
                            properties={"direction": "east"}))

    agent = _Agent()
    agent.graph = graph
    reveal_examined(agent, graph.get_node("way_x"))
    assert Known(agent).has("area_b"), "examining a door tells you where it goes"


def test_examining_an_area_teaches_itself():
    graph = _world()
    agent = _Agent()
    reveal_examined(agent, graph.get_node("area_1"))
    assert Known(agent).has("area_1")


def test_seeing_down_a_corridor_teaches_the_rooms_at_the_end_of_it():
    graph = WorldGraph()
    for index, name in enumerate("abcd"):
        _area(graph, name, name.upper())
    for index in range(3):
        graph.add_node(Node(id=f"way_{index}", type="way", name=f"w{index}",
                            properties={"current_state": "open", "floor": 0,
                                        "direction": "east"}))
    for index in range(3):
        left, right = "abcd"[index], "abcd"[index + 1]
        for source, target, direction in ((left, f"way_{index}", "east"),
                                           (f"way_{index}", right, "west"),
                                           (right, f"way_{index}", "west"),
                                           (f"way_{index}", left, "east")):
            graph.add_edge(Edge(source=source, target=target,
                                type=EDGE_CONNECTION,
                                properties={"direction": direction}))

    run = sightline_run(graph, "a", "east")
    agent = _Agent()
    added = reveal_sightline(agent, graph, run)
    known = Known(agent)
    assert known.has("area_b") is False, "the run carries names, not ids"
    assert known.has("B") and known.has("C")
    assert added, added


# ── a map teaches ──────────────────────────────────────────────────────────


def test_a_map_with_a_chart_teaches_exactly_its_chart():
    graph = _world(4)
    chart = Node(id="item_map", type="item", name="Map",
                 properties={"charted_areas": ["area_0", "Room 1"]})
    agent = _Agent()
    report = teach_from_map(agent, chart, graph=graph)
    assert Known(agent).has("area_0") and Known(agent).has("area_1")
    assert not Known(agent).has("area_2"), (
        "a map of two rooms must not teach the whole world"
    )
    assert report["count"] == 2


def test_a_map_with_no_list_teaches_the_place_you_are_in():
    """A map prop that says nothing lists the world, which is what an item with
    no chart means. An explicit EMPTY list is different, and is the difference
    between a blank prop and an absent one."""
    graph = _world(3)
    plain = Node(id="item_map", type="item", name="Map", properties={})
    agent = _Agent()
    teach_from_map(agent, plain, graph=graph)
    assert Known(agent).has("area_0") and Known(agent).has("area_2")

    blank = Node(id="item_map2", type="item", name="Blank",
                 properties={"charted_areas": []})
    other = _Agent()
    teach_from_map(other, blank, graph=graph)
    assert len(Known(other)) == 0, "an explicit empty chart teaches nothing"


def test_a_map_writes_to_the_same_registry_as_a_walk():
    """Two teach paths would mean two places to look, and one would be forgotten."""
    graph = _world(2)
    agent = _Agent()
    reveal_area(agent, graph.get_node("area_0"))
    teach_from_map(agent, Node(id="m", type="item", name="M",
                               properties={"charted_areas": ["area_1"]}),
                   graph=graph)
    # One list, both routes in, and the perception gate sees both.
    assert Known(agent).has("area_0") and Known(agent).has("area_1")
    assert isinstance(agent.known, list)


# ── honesty: what a character may be told ──────────────────────────────────


def test_an_unaware_agent_is_not_told_about_rooms_it_has_not_visited():
    agent = _Agent()
    reveal_area(agent, "area_0")
    assert only_known(agent, ["area_0", "area_1", "area_2"]) == ["area_0"]


def test_only_known_accepts_names_as_well_as_ids():
    graph = _world()
    agent = _Agent()
    reveal_area(agent, graph.get_node("area_0"))
    assert only_known(agent, ["Room 0", "area_1"]) == ["Room 0"]
    assert only_known(agent, ["area_0", "area_1"]) == ["area_0"]


def test_only_known_degrades_to_nothing_rather_than_everything():
    """The failure this guards: a filter that returns the input when it cannot
    decide is an omniscient agent with extra steps."""
    agent = _Agent()
    assert only_known(agent, ["a", "b", "c"]) == []
    assert only_known(agent, []) == []
    assert only_known(agent, None) == []


def test_the_hiding_predicate_is_the_single_named_boundary():
    agent = _Agent()
    reveal_area(agent, "area_0")
    assert unknown_are_hidden(agent, "area_0") is False
    assert unknown_are_hidden(agent, "area_1") is True


def test_two_agents_get_different_prompt_answers_from_one_world():
    graph = _world(3)
    scout = _Agent()
    homebody = _Agent()
    reveal_area(scout, graph.get_node("area_0"))
    reveal_area(scout, graph.get_node("area_1"))

    names = ["area_0", "area_1", "area_2"]
    assert only_known(scout, names) == ["area_0", "area_1"]
    assert only_known(homebody, names) == []


# ── the map view ───────────────────────────────────────────────────────────


def test_fog_lists_unknown_cells_rather_than_omitting_them():
    """An omitted cell is indistinguishable from one that was never painted, so
    the map cannot tell 'you have not been there' from 'there is nothing there'
    — and fog that looks like empty space is fog nobody explores."""
    agent = _Agent()
    reveal_area(agent, "area_0")
    view = fog_view(agent, ["area_0", "area_1", "area_2"])
    assert view["known"] == ["area_0"]
    assert view["fog"] == ["area_1", "area_2"]
    assert view["known_count"] + view["fog_count"] == 3
    assert "area_1" in view["fog"], "fog is present, marked, not missing"


def test_the_fog_view_is_stable_and_complete_with_no_input():
    assert fog_view(_Agent(), []) == {
        "known": [], "fog": [], "known_count": 0, "fog_count": 0}
    agent = _Agent()
    reveal_area(agent, "area_0")
    assert fog_view(agent, ["area_0", "area_0"]) == {
        "known": ["area_0"], "fog": [], "known_count": 1, "fog_count": 0}


def test_the_fog_view_can_include_zones():
    agent = _Agent()
    reveal_area(agent, "area_0")
    view = fog_view(agent, ["area_0"], zones=True)
    assert "known_zones" in view


# ── the existing gate still works ──────────────────────────────────────────


def test_the_perception_gate_is_now_reachable():
    """`room_perception.way_visible_to` reads `player.known`; this proves a
    revealed hidden way is visible to the agent that revealed it and hidden from
    another — which is the whole point of having had no writer until now."""
    from engine.room_perception import way_visible_to

    class _Manager:
        def __init__(self, players):
            self.players = players

    hidden_way = Node(id="way_secret", type="way", name="Secret",
                      properties={"current_state": "hidden", "description": "",
                                  "pass_message": "", "direction": "north"})
    scout = _Agent()
    homebody = _Agent()
    reveal_examined_type(scout, hidden_way)

    manager = _Manager({"Scout": scout, "Homebody": homebody})
    # The gate also accepts a lossy name-derived id guess ("area_chief's_den").
    # The known set never has to store that: a reveal writes the real id and the
    # real name, so the guess is always redundant.
    assert way_visible_to(scout, manager, "Scout", hidden_way, "A", "north") is True
    assert way_visible_to(homebody, manager, "Homebody", hidden_way,
                          "A", "north") is False


def reveal_examined_type(agent, way_node):
    """A hidden way is taught by being *seen*, which is a reveal of the node
    itself: there is no far area in a one-way fixture to point at."""
    Known(agent).reveal(way_node)
