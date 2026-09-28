"""Elevation-gated chained sightlines (task-498).

Task-201 established that you can see people and items in the room *through* one
open or see-through way. This extends that to a **run** of ways: an observer sees
along a straight line of open or see-through ways, as long as the storey does not
change and the run does not turn.

Two decisions the task asked to be made explicitly rather than left implicit are
recorded in `engine/beyond_visibility.py` and pinned here:

* **the depth cap** — 3 by default, configurable, and argued;
* **contents vs name/description** — a room's name and who or what is in it,
  never its exits, its description, or anything past it.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.beyond_visibility import (  # noqa: E402
    DEFAULT_SIGHTLINE_DEPTH,
    chained_sightline_summary,
    sightline_depth,
    sightline_run,
)
from graph import EDGE_CONNECTION, Edge, Node, WorldGraph  # noqa: E402

BACK = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _line(graph, names, way_overrides=None):
    """A straight run of areas joined east-west, one way per step.

    *way_overrides* is ``{index: {property: value}}``, applied to way *index*.
    Named explicitly rather than collected in ``**kwargs`` — a ``way_overrides=`` call
    then lands in the collected dict under the key ``"way_props"``, every
    ``overrides.get(index)`` misses, and every test passes for the wrong reason.
    """
    way_overrides = way_overrides or {}
    for name in names:
        graph.add_node(Node(id=name, type="area", name=name.title(),
                            properties={"environment": {"light": 60}}))
    for index in range(len(names) - 1):
        way_id = f"way_{index}"
        props = {"current_state": "open", "kind": "open", "direction": "east",
                 "description": "", "pass_message": "", "floor": 0}
        props.update(way_overrides.get(index, {}))
        if "floor" not in way_overrides.get(index, {}):
            props["floor"] = 0
        graph.add_node(Node(id=way_id, type="way", name=way_id, properties=props))
        left, right = names[index], names[index + 1]
        for source, target, direction in ((left, way_id, "east"),
                                           (way_id, right, "west"),
                                           (right, way_id, "west"),
                                           (way_id, left, "east")):
            graph.add_edge(Edge(source=source, target=target,
                                type=EDGE_CONNECTION,
                                properties={"direction": direction}))
    return graph


class _Players:
    def __init__(self, where=()):
        self._where = {name: [{"name": name}] for name in where}

    def get_players_in_area(self, name):
        return self._where.get(name, [])

    @property
    def players(self):
        return {}


# ── the run ────────────────────────────────────────────────────────────────


def test_an_open_run_is_visible_down_its_whole_length():
    graph = _line(WorldGraph(), ["a", "b", "c", "d"])
    run = sightline_run(graph, "a", "east")
    assert [step["area_name"] for step in run] == ["B", "C", "D"]
    assert [step["depth"] for step in run] == [1, 2, 3]
    assert all(step["direction"] == "east" for step in run)


def test_the_cap_stops_the_run_at_three_by_default():
    graph = _line(WorldGraph(), ["a", "b", "c", "d", "e", "f"])
    assert DEFAULT_SIGHTLINE_DEPTH == 3
    assert len(sightline_run(graph, "a", "east")) == 3
    assert [s["area_name"] for s in sightline_run(graph, "a", "east")] == ["B", "C", "D"]


def test_the_cap_is_configurable():
    graph = _line(WorldGraph(), ["a", "b", "c", "d", "e"])
    assert len(sightline_run(graph, "a", "east", depth=4)) == 4
    assert len(sightline_run(graph, "a", "east", depth=0)) == 0
    assert sightline_run(graph, "a", "east", depth=-1) == []


def test_the_configured_cap_is_read_and_clamped():
    from engine.runtime_config import config

    previous = config._values.get("sightline.depth")
    try:
        config._values["sightline.depth"] = 5
        assert sightline_depth() == 5
        config._values["sightline.depth"] = -4
        assert sightline_depth() == 0, "a negative cap is a disabled sightline"
        config._values["sightline.depth"] = "nonsense"
        assert sightline_depth() == DEFAULT_SIGHTLINE_DEPTH
    finally:
        if previous is None:
            config._values.pop("sightline.depth", None)
        else:
            config._values["sightline.depth"] = previous
    assert sightline_depth() == DEFAULT_SIGHTLINE_DEPTH


# ── what breaks a chain ────────────────────────────────────────────────────


def test_a_floor_step_breaks_the_run():
    """The task's elevation gate. A step means the line of sight leaves the storey
    it started on."""
    graph = _line(WorldGraph(), ["a", "b", "c", "d"],
                  way_overrides={1: {"floor": 2}})
    run = sightline_run(graph, "a", "east")
    assert [step["area_name"] for step in run] == ["B"], (
        "a run cannot cross a storey step; the room past it is a different storey"
    )


def test_a_stairway_is_visible_across_but_the_run_stops_at_it():
    """A step is detected on the way that carries the new storey, so the room
    *beyond* the stairway is not reported — the line of sight left the floor it
    started on, and the stairway is where it left."""
    graph = _line(WorldGraph(), ["a", "b", "c", "d"], way_overrides={1: {"floor": 1}})
    run = sightline_run(graph, "a", "east")
    assert [step["area_name"] for step in run] == ["B"]
    assert run[0]["floor"] == 0
    # One floor up is exactly the break, and the same way one floor down is.
    down = _line(WorldGraph(), ["a", "b", "c"], way_overrides={1: {"floor": -1}})
    assert [s["area_name"] for s in sightline_run(down, "a", "east")] == ["B"]


def test_ways_with_no_floor_do_not_break_the_run():
    """A hand-placed way that never declared a storey has not claimed a different
    one, so treating 'unknown' as 'different' would blank every hand-authored
    corridor in the game."""
    graph = _line(WorldGraph(), ["a", "b", "c", "d"])
    for way_id in ("way_0", "way_1", "way_2"):
        graph.get_node(way_id).properties.pop("floor", None)
    assert len(sightline_run(graph, "a", "east")) == 3


def test_a_turn_breaks_the_run():
    """You cannot see round a corner, and a chain that turned would report rooms
    behind the observer's shoulder."""
    graph = WorldGraph()
    for name in ("a", "b", "c"):
        graph.add_node(Node(id=name, type="area", name=name, properties={}))
    graph.add_node(Node(id="way_1", type="way", name="w1", properties={
        "current_state": "open", "floor": 0, "direction": "east"}))
    graph.add_node(Node(id="way_2", type="way", name="w2", properties={
        "current_state": "open", "floor": 0, "direction": "north"}))
    for source, target, way, direction in (("a", "way_1", None, "east"),
                                           ("way_1", "b", None, "west"),
                                           ("b", "way_2", None, "west"),
                                           ("way_2", "c", None, "north")):
        graph.add_edge(Edge(source=source, target=target, type=EDGE_CONNECTION,
                            properties={"direction": direction}))
    # `a -> b` east is a straight step; `b -> c` is north, a turn.
    assert [s["area_name"] for s in sightline_run(graph, "a", "east")] == ["b"]


def test_a_closed_door_breaks_the_run_and_a_window_does_not():
    shut = _line(WorldGraph(), ["a", "b", "c"], way_overrides={0: {"current_state": "closed"}})
    assert sightline_run(shut, "a", "east") == [], (
        "the first closed door ends it: a wall is a wall"
    )

    glazed = _line(WorldGraph(), ["a", "b", "c"], way_overrides={0: {"see_through": True}})
    assert [s["area_name"] for s in sightline_run(glazed, "a", "east")] == ["B", "C"]


def test_a_locked_or_blocked_way_breaks_the_run():
    """Read through the shared barrier ladder, so a new state cannot be 'open by
    omission' here."""
    from engine.barriers import WAY_STATES

    for state in ("closed", "locked", "blocked", "hidden"):
        graph = _line(WorldGraph(), ["a", "b", "c"],
                      way_overrides={0: {"current_state": state}})
        assert sightline_run(graph, "a", "east") == [], state
    assert len(WAY_STATES) == 6


def test_a_cycle_terminates_rather_than_looping():
    graph = WorldGraph()
    for name in ("a", "b"):
        graph.add_node(Node(id=name, type="area", name=name, properties={}))
    for index, (x, y) in enumerate((("a", "b"), ("b", "a"))):
        way_id = f"way_{index}"
        graph.add_node(Node(id=way_id, type="way", name=way_id, properties={
            "current_state": "open", "floor": 0, "direction": "east"}))
        graph.add_edge(Edge(source=x, target=way_id, type=EDGE_CONNECTION,
                            properties={"direction": "east"}))
        graph.add_edge(Edge(source=way_id, target=y, type=EDGE_CONNECTION,
                            properties={"direction": "west"}))
    run = sightline_run(graph, "a", "east")
    assert [s["area_id"] for s in run] == ["b"], "a two-room cycle stops at one hop"


def test_a_run_from_a_room_with_no_way_is_empty():
    graph = WorldGraph()
    graph.add_node(Node(id="a", type="area", name="A", properties={}))
    assert sightline_run(graph, "a", "east") == []
    assert sightline_run(graph, "a", "") == []


# ── the contents-vs-name decision ──────────────────────────────────────────


def test_a_sightline_reports_people_and_items_and_nothing_else():
    """Recorded decision: a room's name and who or what is in it; never its
    exits, its description, or anything past it."""
    graph = _line(WorldGraph(), ["a", "b", "c"])
    for area in ("b", "c"):
        graph.get_node(area).properties["description"] = "A SECRET DESCRIPTION"
    graph.add_node(Node(id="item_chest", type="item", name="chest",
                        properties={"current_state": "normal"}))
    graph.add_edge(Edge(source="item_chest", target="c", type="in",
                        properties={}))

    run = sightline_run(graph, "a", "east")
    text = chained_sightline_summary(graph, _Players(), run, None)

    assert "chest" in text
    assert "C" in text
    assert "SECRET DESCRIPTION" not in text, (
        "a description is prose the author wrote for somebody standing there, "
        "not a thing a glance down a corridor conveys"
    )
    assert "exit" not in text.lower()


def test_people_down_the_line_are_named_once():
    graph = _line(WorldGraph(), ["a", "b", "c"])
    run = sightline_run(graph, "a", "east")
    # People are named like people, not like the room they are standing in —
    # otherwise a character called "B" in room "B" makes every count ambiguous
    # and the test measures a coincidence rather than deduplication.
    class _Named(_Players):
        def get_players_in_area(self, name):
            return [{"name": {"B": "Lyrie", "C": "Corvin"}.get(name, name)}]

    text = chained_sightline_summary(graph, _Named(), run, None)
    assert "Lyrie" in text and "Corvin" in text, text
    assert text.count("Lyrie") == 1 and text.count("Corvin") == 1, text


def test_an_empty_sightline_produces_no_clause():
    graph = _line(WorldGraph(), ["a", "b", "c"])
    assert chained_sightline_summary(graph, _Players(), [], None) == ""
    run = sightline_run(graph, "a", "east")
    assert chained_sightline_summary(graph, _Players(), run, None) == ""


def test_a_single_step_reads_like_the_existing_task_201_line():
    graph = _line(WorldGraph(), ["a", "b"])
    run = sightline_run(graph, "a", "east")
    assert len(run) == 1
    text = chained_sightline_summary(graph, _Players(where=["B"]), run, None)
    assert text.startswith(" Beyond"), text


# ── the existing behaviour is untouched ────────────────────────────────────


def test_the_existing_beyond_visibility_still_builds():
    """task-498 must not regress task-201. `build_beyond_suffix` is unchanged;
    this pins that a depth-1 view still works after the module grew."""
    from engine.beyond_visibility import build_beyond_suffix, normalize_visible_items

    graph = WorldGraph()
    graph.add_node(Node(id="a", type="area", name="A", properties={}))
    graph.add_node(Node(id="b", type="area", name="B", properties={}))
    graph.add_node(Node(id="way_x", type="way", name="w", properties={
        "current_state": "open", "floor": 0}))

    assert build_beyond_suffix(
        graph, _Players(), "b", "B", {"allow_see_characters": True}, None
    ) == "", "an empty room has nothing to report"
    assert normalize_visible_items("thing") == ["thing"]
    assert normalize_visible_items(None) == []


def test_the_run_does_not_mutate_the_graph():
    graph = _line(WorldGraph(), ["a", "b", "c", "d"])
    before = (sorted(graph.nodes),
              sorted((e.source, e.target, e.type) for e in graph.edges))
    sightline_run(graph, "a", "east")
    assert (sorted(graph.nodes),
            sorted((e.source, e.target, e.type) for e in graph.edges)) == before


@pytest.mark.parametrize("direction", ["north", "south", "east", "west"])
def test_every_direction_works(direction):
    graph = WorldGraph()
    for name in ("a", "b"):
        graph.add_node(Node(id=name, type="area", name=name, properties={}))
    graph.add_node(Node(id="way_x", type="way", name="w", properties={
        "current_state": "open", "floor": 0, "direction": direction}))
    for source, target, d in (("a", "way_x", direction),
                              ("way_x", "b", BACK[direction])):
        graph.add_edge(Edge(source=source, target=target, type=EDGE_CONNECTION,
                            properties={"direction": d}))
    run = sightline_run(graph, "a", direction)
    assert [s["area_id"] for s in run] == ["b"], direction
