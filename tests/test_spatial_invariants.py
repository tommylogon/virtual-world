"""One `at` edge per character, and a distance that is walked, not stored (task-419).

The model has three claims worth testing and one worth refusing:

- A character holds **exactly one** `at` edge in the world, so the edge set is
  O(population) and not O(n²). That is enforced on the write path *and* against
  whatever wrote an edge directly.
- Positional detail is allocated by the attendance decision, so `in <area>` is
  the population's edge and `at <anchor>` is at most `cap`.
- Proximity is **derived** from the relation path. Nothing caches a distance, so
  re-authoring a `beside` edge cannot leave a stale one behind.
- The last claim is about the *refusal*: there is no coordinate, and this module
  never invents one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.character_spatial import (
    ANCHOR_BUDGET_MAX,
    ANCHOR_BUDGET_MIN,
    PROXIMITY_ACROSS_ROOM,
    PROXIMITY_AT,
    PROXIMITY_NEAR,
    apply_positional_fidelity,
    area_anchor_candidates,
    check_spatial_invariants,
    describe_pool,
    enforce_single_at,
    is_pool_anchor,
    pool_remaining,
    proximity_hops,
    proximity_phrase,
    select_area_anchors,
    set_character_position,
    spawn_from_pool,
)
from graph import (
    EDGE_AT,
    EDGE_BESIDE,
    EDGE_IN,
    EDGE_ON,
    Edge,
    Node,
    WorldGraph,
)


def _graph():
    graph = WorldGraph()
    graph.add_node(Node(id="area_wood", type="area", name="Wood", properties={}))
    return graph


def _person(graph, name):
    node_id = f"player_{name.lower().replace(' ', '_')}"
    graph.add_node(Node(id=node_id, type="player", name=name, properties={}))
    return node_id


def _item(graph, item_id, **props):
    graph.add_node(Node(id=item_id, type="item", name=item_id, properties=props))
    return item_id


def _place(graph, item_id, area_id="area_wood"):
    graph.add_edge(Edge(source=item_id, target=area_id, type=EDGE_IN))


def _at_targets(graph, node_id):
    return sorted(e.target for e in graph.get_edges_for_source(node_id, EDGE_AT))


# ── the one-`at` invariant ────────────────────────────────────────────────


def test_setting_a_position_twice_leaves_one_edge():
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    _item(graph, "oak")

    set_character_position(graph, who, "boulder")
    set_character_position(graph, who, "oak")

    assert _at_targets(graph, who) == ["oak"], "the first was cleared"


def test_a_second_at_edge_written_directly_is_reduced_to_one():
    """The path that does not go through the setter: an effect, an NL edit, a load."""
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    _item(graph, "oak")
    _item(graph, "stump")
    for target in ("boulder", "oak", "stump"):
        graph.add_edge(Edge(source=who, target=target, type=EDGE_AT))

    assert len(_at_targets(graph, who)) == 3, "the world is already broken"

    removed = enforce_single_at(graph, who)
    assert removed == 2
    assert len(_at_targets(graph, who)) == 1


def test_which_at_edge_survives_is_deterministic():
    graph = _graph()
    who = _person(graph, "Gribba")
    for target in ("zebra", "apple", "mango"):
        _item(graph, target)
        graph.add_edge(Edge(source=who, target=target, type=EDGE_AT))

    enforce_single_at(graph, who)
    assert _at_targets(graph, who) == ["apple"], "lexicographically first, always"


def test_a_move_is_never_undone_by_the_edge_it_replaced():
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    _item(graph, "oak")
    for target in ("boulder", "oak"):
        graph.add_edge(Edge(source=who, target=target, type=EDGE_AT))

    enforce_single_at(graph, who, keep_target="oak")
    assert _at_targets(graph, who) == ["oak"], "the newer position wins"


def test_enforcing_never_takes_the_last_position_away():
    """Reducing to at most one is not the same as clearing: standing at
    nothing is still standing somewhere, and only demotion takes it."""
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    graph.add_edge(Edge(source=who, target="boulder", type=EDGE_AT))

    assert enforce_single_at(graph, who) == 0
    assert _at_targets(graph, who) == ["boulder"]


def test_the_validator_reports_a_character_with_two_at_edges():
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    _item(graph, "oak")
    for target in ("boulder", "oak"):
        graph.add_edge(Edge(source=who, target=target, type=EDGE_AT))

    violations = check_spatial_invariants(graph)
    assert [v["kind"] for v in violations] == ["multiple_at_edges"]
    assert violations[0]["character_id"] == who


def test_the_validator_reports_a_dangling_or_nonspatial_target():
    graph = _graph()
    who = _person(graph, "Gribba")
    stranger = _person(graph, "Krikka")
    graph.add_node(Node(id="area_other", type="area", name="Elsewhere", properties={}))
    graph.add_edge(Edge(source=who, target="area_other", type=EDGE_AT))
    graph.add_edge(Edge(source=stranger, target="ghost", type=EDGE_AT))

    found = {v["kind"]: v for v in check_spatial_invariants(graph)}
    assert sorted(found) == ["at_non_anchor_target", "dangling_at_edge"]
    assert found["at_non_anchor_target"]["character_id"] == who
    assert found["dangling_at_edge"]["character_id"] == stranger


def test_a_healthy_world_reports_nothing():
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    set_character_position(graph, who, "boulder")
    assert check_spatial_invariants(graph) == []


# ── positional fidelity is an attendance tier ────────────────────────────


def _crowd(graph, count):
    """`count` people in one area, each holding an `in` edge and nothing else."""
    names = {}
    for i in range(count):
        name = f"Goblin {i}"
        node_id = _person(graph, name)
        graph.add_edge(Edge(source=node_id, target="area_wood", type=EDGE_IN))
        names[name] = node_id
    return names


def test_background_characters_hold_no_at_edge_and_attended_hold_exactly_one():
    graph = _graph()
    names = _crowd(graph, 40)
    _item(graph, "boulder")

    attended = [f"Goblin {i}" for i in range(8)]
    result = apply_positional_fidelity(
        graph, names, attended,
        anchor_for={name: "boulder" for name in attended})

    assert result == {"attended": 8, "at_edges": 8, "cleared": 0}
    for name, node_id in names.items():
        targets = _at_targets(graph, node_id)
        assert len(targets) == (1 if name in attended else 0), name
        # The population's edge is the one every character has.
        assert [e.target for e in graph.get_edges_for_source(node_id, EDGE_IN)] == ["area_wood"]


def test_forty_characters_cost_forty_in_edges_and_eight_at_edges():
    """The whole reason positional detail is budgeted rather than pairwise."""
    graph = _graph()
    names = _crowd(graph, 40)
    _item(graph, "boulder")
    attended = [f"Goblin {i}" for i in range(8)]
    apply_positional_fidelity(graph, names, attended,
                              anchor_for={n: "boulder" for n in attended})

    at_edges = [e for e in graph.edges if e.type == EDGE_AT]
    in_edges = [e for e in graph.edges if e.type == EDGE_IN
                and e.source.startswith("player_")]
    assert len(in_edges) == 40
    assert len(at_edges) == 8, "not 40 x 40 pairs"


def test_demoting_a_character_clears_their_at_edge():
    graph = _graph()
    names = _crowd(graph, 2)
    _item(graph, "boulder")
    attended = ["Goblin 0"]
    apply_positional_fidelity(graph, names, attended,
                              anchor_for={"Goblin 0": "boulder"})
    assert _at_targets(graph, names["Goblin 0"]) == ["boulder"]

    result = apply_positional_fidelity(graph, names, [])
    assert _at_targets(graph, names["Goblin 0"]) == [], "background is just 'in'"
    assert result["cleared"] == 1


def test_attending_someone_who_has_no_anchor_does_not_invent_a_place():
    graph = _graph()
    names = _crowd(graph, 1)
    result = apply_positional_fidelity(graph, names, ["Goblin 0"])

    assert _at_targets(graph, names["Goblin 0"]) == []
    assert result == {"attended": 1, "at_edges": 0, "cleared": 0}


def test_an_attended_character_keeps_the_anchor_it_already_had():
    graph = _graph()
    names = _crowd(graph, 1)
    _item(graph, "boulder")
    set_character_position(graph, names["Goblin 0"], "boulder")

    apply_positional_fidelity(graph, names, ["Goblin 0"])
    assert _at_targets(graph, names["Goblin 0"]) == ["boulder"]


def test_an_unknown_character_name_is_skipped_not_invented():
    graph = _graph()
    result = apply_positional_fidelity(graph, {}, ["Nobody"])
    assert result == {"attended": 1, "at_edges": 0, "cleared": 0}


# ── proximity is derived, never stored ───────────────────────────────────


def test_something_you_are_at_is_one_hop():
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    set_character_position(graph, who, "boulder")

    assert proximity_hops(graph, who, "boulder") == PROXIMITY_AT
    assert proximity_phrase(graph, who, "boulder") == "at"


def test_a_neighbour_of_your_anchor_is_two_hops():
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    _item(graph, "oak")
    graph.add_edge(Edge(source="boulder", target="oak", type=EDGE_BESIDE))
    set_character_position(graph, who, "boulder")

    assert proximity_hops(graph, who, "oak") == PROXIMITY_NEAR
    assert proximity_phrase(graph, who, "oak") == "by"


def test_something_else_in_the_room_is_unreachable():
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    _item(graph, "far_corner")
    set_character_position(graph, who, "boulder")

    assert proximity_hops(graph, who, "far_corner") is None
    assert proximity_phrase(graph, who, "far_corner") == PROXIMITY_ACROSS_ROOM


def test_re_authoring_a_beside_edge_changes_the_distance_immediately():
    """Nothing caches a distance, so there is no stale one to go wrong."""
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    _item(graph, "oak")
    set_character_position(graph, who, "boulder")
    assert proximity_hops(graph, who, "oak") is None

    graph.add_edge(Edge(source="boulder", target="oak", type=EDGE_BESIDE))
    assert proximity_hops(graph, who, "oak") == PROXIMITY_NEAR, "walked, not stored"

    graph.remove_edge("boulder", "oak", EDGE_BESIDE)
    assert proximity_hops(graph, who, "oak") is None, "and it un-applies too"


def test_proximity_never_escapes_its_own_area():
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    _item(graph, "stump")
    graph.add_edge(Edge(source="boulder", target="stump", type=EDGE_ON))
    set_character_position(graph, who, "boulder")

    assert proximity_hops(graph, who, "stump") == PROXIMITY_NEAR, "one relation step"


def test_proximity_to_yourself_is_zero_and_unlinked_areas_stay_unreachable():
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "boulder")
    other = _person(graph, "Krikka")

    assert proximity_hops(graph, who, who) == 0
    assert proximity_hops(graph, who, other) is None
    assert proximity_hops(graph, who, "boulder") is None, "no anchor, no chain"


def test_a_relation_cycle_terminates():
    graph = _graph()
    who = _person(graph, "Gribba")
    _item(graph, "a")
    _item(graph, "b")
    graph.add_edge(Edge(source="a", target="b", type=EDGE_BESIDE))
    graph.add_edge(Edge(source="b", target="a", type=EDGE_BESIDE))
    set_character_position(graph, who, "a")

    assert proximity_hops(graph, who, "b") == PROXIMITY_NEAR
    assert proximity_hops(graph, who, "a") == PROXIMITY_AT


# ── the anchor vocabulary ────────────────────────────────────────────────


def _pool(graph, item_id="gravel", remaining=10, max_spawn=3, unit="handful"):
    _item(graph, item_id, anchor_kind="pooled", anchor=True,
          pool={"remaining": remaining, "max_spawn": max_spawn,
                "unit": unit, "item": {"name": "pebble"}})
    _place(graph, item_id)
    return item_id


def test_a_pool_is_described_as_a_quantity():
    graph = _graph()
    _pool(graph, remaining=4, unit="handful")
    assert describe_pool(graph.get_node("gravel")) == "4 handfuls"
    assert describe_pool(graph.get_node("gravel")) == describe_pool(graph.get_node("gravel"))
    assert pool_remaining(graph.get_node("gravel")) == 4
    assert is_pool_anchor(graph.get_node("gravel"))


def test_a_pool_spawns_a_bounded_handful_on_interaction():
    graph = _graph()
    _pool(graph, remaining=10, max_spawn=3)
    spawned = spawn_from_pool(graph, graph.get_node("gravel"))

    assert len(spawned) == 3, "bounded by max_spawn, not by the remaining 10"
    assert all(graph.get_node(i) is not None for i in spawned), "real nodes"
    assert pool_remaining(graph.get_node("gravel")) == 7, "and the pool decremented"


def test_asking_for_fewer_spawns_fewer():
    graph = _graph()
    _pool(graph, remaining=10, max_spawn=3)
    assert len(spawn_from_pool(graph, graph.get_node("gravel"), wanted=1)) == 1
    assert len(spawn_from_pool(graph, graph.get_node("gravel"), wanted=99)) == 3
    assert pool_remaining(graph.get_node("gravel")) == 6


def test_a_pool_depletes_and_then_stops():
    graph = _graph()
    _pool(graph, remaining=4, max_spawn=2)
    pool = graph.get_node("gravel")
    spawn_from_pool(graph, pool)
    spawn_from_pool(graph, pool)
    assert pool_remaining(pool) == 0

    assert spawn_from_pool(graph, pool) == [], "an exhausted pool spawns nothing"
    assert describe_pool(pool) == "0 handfuls"


def test_spawned_items_land_in_the_anchor_area_and_know_their_origin():
    graph = _graph()
    _pool(graph, remaining=2, max_spawn=2)
    spawned = spawn_from_pool(graph, graph.get_node("gravel"))
    pebble = graph.get_node(spawned[0])
    assert [e.target for e in graph.get_edges_for_source(pebble.id, EDGE_IN)] == ["area_wood"]
    assert pebble.properties["spawned_from"] == "gravel"


def test_a_pool_never_spawns_below_zero():
    graph = _graph()
    _pool(graph, remaining=1, max_spawn=5)
    pool = graph.get_node("gravel")
    assert len(spawn_from_pool(graph, pool)) == 1
    assert pool_remaining(pool) == 0
    spawn_from_pool(graph, pool)
    assert pool_remaining(pool) == 0, "not -1"


def test_a_plain_item_is_not_a_pool():
    graph = _graph()
    _item(graph, "rock")
    _place(graph, "rock")
    assert spawn_from_pool(graph, graph.get_node("rock")) == []
    assert not is_pool_anchor(graph.get_node("rock"))


def test_a_pool_outside_any_area_does_not_spawn_orphans():
    graph = _graph()
    _item(graph, "floating_gravel", anchor_kind="pooled",
          pool={"remaining": 5, "max_spawn": 2})
    assert spawn_from_pool(graph, graph.get_node("floating_gravel")) == []
    assert pool_remaining(graph.get_node("floating_gravel")) == 5, "and nothing leaked"


# ── the anchor budget ────────────────────────────────────────────────────


def _wild(graph, plain=20):
    """An area with a few good anchors and a lot of scenery.

    The landmark cluster is authored the way a cluster should be: the boulder
    is *placed* in the area and the old oak is reachable only through it. Both
    are `at` targets, but they are one landmark and so one budget line.
    """
    _pool(graph, "gravel", remaining=6)
    _item(graph, "boulder", anchor_kind="landmark", anchor=True)
    _place(graph, "boulder")
    _item(graph, "old_oak", anchor_kind="landmark", anchor=True)
    graph.add_edge(Edge(source="boulder", target="old_oak", type=EDGE_BESIDE))
    for i in range(plain):
        _item(graph, f"rock_{i:02d}", anchor=True)
        _place(graph, f"rock_{i:02d}")
    return graph


def test_an_anchor_candidate_list_finds_the_shaped_nodes():
    graph = _wild(_graph(), plain=5)
    found = [node.id for node in area_anchor_candidates(graph, "area_wood")]
    assert "gravel" in found and "boulder" in found
    assert "old_oak" not in found, "the cluster partner is not placed, so it is " \
                                 "one landmark rather than a second budget line"
    assert all(graph.get_node(i).type == "item" for i in found)


def test_the_budget_is_between_three_and_eight_and_holds():
    graph = _wild(_graph(), plain=50)
    anchors = select_area_anchors(graph, "area_wood")
    assert ANCHOR_BUDGET_MIN <= len(anchors) <= ANCHOR_BUDGET_MAX
    assert len(anchors) == ANCHOR_BUDGET_MAX, "a rich area takes the whole budget"


def test_the_pool_wins_the_first_seat():
    graph = _wild(_graph(), plain=50)
    assert select_area_anchors(graph, "area_wood")[0] == "gravel", (
        "one pooled node buys more than one rock")


def test_the_budget_choice_is_deterministic_for_a_fixed_world():
    graph = _wild(_graph(), plain=50)
    first = select_area_anchors(graph, "area_wood")
    assert all(select_area_anchors(graph, "area_wood") == first for _ in range(5))


def test_the_budget_is_clamped_into_the_documented_range():
    graph = _wild(_graph(), plain=50)
    assert len(select_area_anchors(graph, "area_wood", budget=99)) == ANCHOR_BUDGET_MAX
    assert len(select_area_anchors(graph, "area_wood", budget=0)) == ANCHOR_BUDGET_MIN


def test_a_sparse_area_gets_what_it_has_rather_than_inventing_anchors():
    graph = _graph()
    _item(graph, "one_rock", anchor=True)
    _place(graph, "one_rock")
    assert select_area_anchors(graph, "area_wood") == ["one_rock"], (
        "the budget is a ceiling, not a quota")
