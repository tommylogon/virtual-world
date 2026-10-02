"""Canonical area identity: id-first, loud on a duplicate display name (task-439).

An area id is the stable handle; a display name may repeat once a world is
decomposed (many "Hollow"s). These tests pin the three things that must stay
true: two same-named areas both survive a round trip with distinct exits and
distinct environments, a name lookup is deterministic and reported rather than
iteration-order, and the validator/lint can see the duplicate.
"""
import importlib.util
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import EDGE_CONNECTION, Edge, Node
from player import Player
from virtual_world_engine import VirtualWorld

ROOT = Path(__file__).parent.parent

A_HOLLOW = "area_a_hollow"
B_HOLLOW = "area_b_hollow"
A_NORTH = "area_a_north"
B_SOUTH = "area_b_south"


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _add_way(world, way_id, from_id, to_id, direction):
    world.graph.add_node(Node(id=way_id, type="way", name=way_id,
                              properties={"current_state": "open"}))
    for source, target, label in (
            (from_id, way_id, direction),
            (way_id, to_id, "back"),
            (to_id, way_id, "back"),
            (way_id, from_id, direction)):
        world.graph.add_edge(Edge(source=source, target=target,
                                  type=EDGE_CONNECTION, properties={"direction": label}))


def _world_with_two_hollows():
    """Two areas both named 'Hollow', distinct ids/exits/temperatures."""
    world = VirtualWorld()
    world.graph.add_node(Node(id=A_HOLLOW, type="area", name="Hollow",
                              properties={"environment": {"temperature": 10}}))
    world.graph.add_node(Node(id=B_HOLLOW, type="area", name="Hollow",
                              properties={"environment": {"temperature": 30}}))
    world.graph.add_node(Node(id=A_NORTH, type="area", name="A North",
                              properties={"environment": {"temperature": 10}}))
    world.graph.add_node(Node(id=B_SOUTH, type="area", name="B South",
                              properties={"environment": {"temperature": 30}}))
    _add_way(world, "way_a", A_HOLLOW, A_NORTH, "north")
    _add_way(world, "way_b", B_HOLLOW, B_SOUTH, "south")
    return world


# ── resolution ──────────────────────────────────────────────────────────


def test_id_resolution_is_exact_even_with_duplicate_names():
    from engine.room_perception import resolve_area

    world = _world_with_two_hollows()
    assert resolve_area(world.graph, A_HOLLOW).id == A_HOLLOW
    assert resolve_area(world.graph, B_HOLLOW).id == B_HOLLOW
    # Ids are case-insensitive through the graph's own index.
    assert resolve_area(world.graph, A_HOLLOW.upper()).id == A_HOLLOW


def test_ambiguous_name_resolves_deterministically_and_warns(caplog):
    from engine.room_perception import resolve_area

    world = _world_with_two_hollows()
    with caplog.at_level(logging.WARNING, logger="engine.room_perception"):
        node = resolve_area(world.graph, "Hollow")

    assert node.id == A_HOLLOW, "ambiguous name must pick by smallest id, not order"
    assert any("ambiguous" in rec.getMessage() for rec in caplog.records)


def test_unique_name_still_resolves():
    from engine.room_perception import resolve_area

    world = _world_with_two_hollows()
    assert resolve_area(world.graph, "A North").id == A_NORTH


# ── round trip ──────────────────────────────────────────────────────────


def test_two_same_named_areas_round_trip_with_distinct_exits_and_env():
    world = _world_with_two_hollows()

    data = world.to_dict()
    # Canonical id-keyed projection keeps both; the name-keyed convenience view
    # can only hold one and is documented as non-canonical.
    assert set(data["areas_by_id"]) == {A_HOLLOW, B_HOLLOW, A_NORTH, B_SOUTH}
    assert data["areas_by_id"][A_HOLLOW]["environment"]["temperature"] == 10
    assert data["areas_by_id"][B_HOLLOW]["environment"]["temperature"] == 30

    exits_a = world.area_description.build_exits_for_area(A_HOLLOW)
    exits_b = world.area_description.build_exits_for_area(B_HOLLOW)
    assert exits_a and exits_b
    assert set(exits_a) != set(exits_b), "same-named areas must not share exits"
    assert exits_a[next(iter(exits_a))]["target"] == "A North"
    assert exits_b[next(iter(exits_b))]["target"] == "B South"

    reloaded = VirtualWorld()
    reloaded.load_from_dict(data)
    assert reloaded.graph.get_node(A_HOLLOW) is not None
    assert reloaded.graph.get_node(B_HOLLOW) is not None


def test_temperature_resolves_by_id_not_first_name_match():
    world = _world_with_two_hollows()
    player = Player("Tester")

    player.current_area = A_HOLLOW
    assert world.serializer._compute_feels_like(player) == 10
    player.current_area = B_HOLLOW
    assert world.serializer._compute_feels_like(player) == 30


def test_temperature_of_an_ambiguous_name_is_deterministic_and_warns(caplog):
    world = _world_with_two_hollows()
    player = Player("Tester")
    player.current_area = "Hollow"

    with caplog.at_level(logging.WARNING, logger="engine.room_perception"):
        feels = world.serializer._compute_feels_like(player)

    assert feels == 10, "the smallest-id Hollow wins deterministically"
    assert any("ambiguous" in rec.getMessage() for rec in caplog.records)


# ── validators ──────────────────────────────────────────────────────────


def test_scenario_validator_flags_a_duplicate_area_name():
    module = _load_tool("validate_scenario")
    nodes = {
        A_HOLLOW: {"type": "area", "name": "Hollow", "properties": {}},
        B_HOLLOW: {"type": "area", "name": "Hollow", "properties": {}},
    }
    issues = []
    module.validate_area_names(nodes, issues)
    assert any("Duplicate area display name 'hollow'" in i for i in issues)


def test_library_lint_flags_a_duplicate_area_name():
    module = _load_tool("lint_library")
    report = module.Report()
    module.check_duplicate_area_names(
        {"a": {"name": "Hollow"}, "b": {"name": "Hollow"}}, report)
    assert any(check == "duplicate_area_names" for check, _ in report.warnings)


def test_engine_helper_sees_both_node_and_dict_shapes():
    from engine.room_perception import duplicate_area_names

    world = _world_with_two_hollows()
    assert duplicate_area_names(world.graph) == {"hollow": [A_HOLLOW, B_HOLLOW]}
    assert duplicate_area_names({
        "x": {"type": "area", "name": "Same"},
        "y": {"type": "area", "name": "Same"},
    }) == {"same": ["x", "y"]}
