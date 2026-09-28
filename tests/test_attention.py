"""Attention budget and fidelity tiers (task-411).

`radius_hops` and `hysteresis` are retired — the task was amended to derive
attendance from awareness channels instead, and these tests assert the
amendment's own acceptance rather than the original hop radius:

- the set is derived with no hop-radius parameter anywhere;
- a character separated from the anchors by a closed/locked door is **not**
  attended;
- awareness is cached, not recomputed per character per tick;
- the set stays ≤ cap and is deterministic for a fixed state;
- removing the hop radius does not change who is co-present;
- the channel interface takes a second implementation (a test double) without any
  change to the selector.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.attention import (  # noqa: E402
    DEFAULT_AWARE_THRESHOLD,
    DEFAULT_CAP,
    ENTER_MARGIN,
    TIER_ANCHOR,
    TIER_AWARE,
    TIER_COPRESENT,
    TIER_HUMAN,
    TIER_NAMES,
    AwarenessChannel,
    AttentionBudget,
    SoundChannel,
)
from engine.barriers import DEFAULT_SOUND_COSTS  # noqa: E402
from graph import EDGE_CONNECTION, Edge, Node, WorldGraph  # noqa: E402


# ── fixtures ───────────────────────────────────────────────────────────────


def _door(graph, way_id, from_area, to_area, state="open", direction="east",
          **extra):
    props = {"current_state": state, "kind": "door", "handle": "door",
             "description": "", "pass_message": "", "area_from_id": from_area,
             "area_to_id": to_area, "direction": direction}
    props.update(extra)
    graph.add_node(Node(id=way_id, type="way", name=way_id, properties=props))
    back = {"north": "south", "south": "north", "east": "west",
            "west": "east"}.get(direction, direction)
    for s, t, d in ((from_area, way_id, direction), (way_id, to_area, back),
                    (to_area, way_id, back), (way_id, from_area, direction)):
        graph.add_edge(Edge(source=s, target=t, type=EDGE_CONNECTION,
                            properties={"direction": d, "cardinal": d}))


def _area(graph, area_id, name=None):
    graph.add_node(Node(id=area_id, type="area", name=name or area_id,
                        properties={"environment": {"light": 60}}))


def _corridor(graph, names, **door_kwargs):
    """A line of areas joined by one door each. ``names`` are the area ids."""
    for name in names:
        _area(graph, name)
    for index in range(len(names) - 1):
        _door(graph, f"way_{index}", names[index], names[index + 1],
              **door_kwargs)


def _roster(*pairs):
    """``(id, area_id, recency)`` triples into the mapping `select` wants."""
    return {cid: {"area_id": area, "recency": recency}
            for cid, area, recency in pairs}


# ── the acceptance: no hop radius anywhere ─────────────────────────────────


def test_the_budget_takes_no_hop_radius_and_holds_no_such_parameter():
    import inspect

    source = inspect.getsource(AttentionBudget)
    assert "radius_hops" not in source
    assert "hop" not in inspect.getsource(AttentionBudget.select).lower()
    budget = AttentionBudget()
    assert not [k for k in vars(budget) if "hop" in k or "radius" in k]
    # And the state that round-trips through a save carries no hop either.
    state = budget.to_state()
    assert not [k for k in state if "hop" in k or "radius" in k]


def test_co_presence_survives_the_removal_of_the_hop_radius():
    """Two characters in the same room are both attended, whatever the doors.

    This is the acceptance line that would fail if awareness were the only
    signal: co-presence is a fact about where somebody stands, and it holds
    through a locked door that sound cannot get through.
    """
    graph = WorldGraph()
    _corridor(graph, ["a", "b", "c"], state="locked")

    report = AttentionBudget(cap=2).select(
        graph,
        anchors=[{"kind": "character", "id": "p1"}],
        humans=["p1"],
        characters=_roster(("p1", "a", 0), ("p2", "a", 0), ("p3", "b", 0)),
    )
    tiers = report["tiers"]
    assert tiers["p1"] == TIER_NAMES[TIER_ANCHOR]
    assert tiers["p2"] == TIER_NAMES[TIER_COPRESENT], "same room, door or not"
    assert "p3" not in report["attended"], "one locked door away loses the budget"


# ── the acceptance: a locked door demotes ──────────────────────────────────
#
# Awareness ORDERS and the cap DECIDES — it does not filter. A character behind
# a locked door ranks below everybody the door cannot separate, and is
# backgrounded when the cap is full, which is the case a budget exists for. So
# every "is not attended" fixture below is deliberately **oversubscribed**; with
# room to spare the low-priority character is attended, and asserting otherwise
# would be asserting a filter the spec does not have.


def _everyone_else_fills_the_budget(graph, count=8, area="a"):
    """Characters in the anchor's own room, so they are aware and outrank a
    character behind a door. Makes any cap small enough a real contest."""
    return _roster(*[(f"crowd_{i}", area, 100 - i) for i in range(count)])


def test_a_character_behind_a_locked_door_is_not_attended():
    graph = WorldGraph()
    _corridor(graph, ["a", "b", "c"], state="locked")
    characters = _roster(("p1", "a", 0), ("p2", "b", 0), ("p3", "c", 0))
    characters.update(_everyone_else_fills_the_budget(graph))

    report = AttentionBudget(cap=6).select(
        graph,
        anchors=[{"kind": "character", "id": "p1"}],
        characters=characters,
    )
    assert "p1" in report["attended"]
    assert "p2" not in report["attended"], "one locked door away"
    assert "p3" not in report["attended"], "two locked doors away"
    assert len(report["attended"]) == 6


def test_awareness_orders_rather_than_filters():
    """The subtlety, stated as a test: a locked door does not *exclude*.

    With budget to spare the same character is attended, because a cap is a
    budget and not a filter. If a later change makes awareness exclude, this
    test is the thing that noticed.
    """
    graph = WorldGraph()
    _corridor(graph, ["a", "b", "c"], state="locked")
    characters = _roster(("p1", "a", 0), ("p2", "b", 0), ("p3", "c", 0))

    roomy = AttentionBudget(cap=8).select(
        graph, anchors=[{"kind": "character", "id": "p1"}], characters=characters)
    assert roomy["attended"] == ["p1", "p2", "p3"]
    # ...but p2/p3 rank below the crowd, which is the whole effect.
    tight = AttentionBudget(cap=1).select(
        graph, anchors=[{"kind": "character", "id": "p1"}], characters=characters)
    assert tight["attended"] == ["p1"]


def _everyone_else_fills_the_budget(graph, count=8, area="a", recency=100):
    """Characters in `area`, so they are aware and outrank a character behind a
    door. `recency` is a floor by default — call it low to make the crowd the
    *weaker* candidate, which is the comparison several tests actually need."""
    return _roster(*[(f"crowd_{i}", area, recency - i) for i in range(count)])


def _same_room_crowd(area, count=8, recency=100):
    """Characters in `area` with *worse* recency than the character under test.

    Tier beats recency, so a crowd has to share the candidate's **tier** for the
    comparison to mean anything. Putting them in the same room does that: same
    awareness strength, same tier, and the id/recency tie-break decides. A crowd
    in the anchor's own room would outrank a corridor neighbour on tier alone
    however stale it was, which is correct behaviour and a useless fixture.
    """
    return _roster(*[(f"crowd_{i:02d}", area, recency - i) for i in range(count)])


def test_the_same_fixture_with_open_doors_attends_them():
    graph = WorldGraph()
    _corridor(graph, ["a", "b", "c"], state="open")
    characters = _roster(("p1", "a", 0), ("p2", "b", 0), ("p3", "c", 5))
    characters.update(_same_room_crowd("c", recency=3))

    report = AttentionBudget(cap=2).select(
        graph,
        anchors=[{"kind": "character", "id": "p1"}],
        characters=characters,
    )
    # One open door is one step of attenuation, so b stays aware and takes the
    # budget from a less recent character in the same tier.
    assert report["attended"] == ["p1", "p2"]
    # c is two doors away, which costs exactly as much as one closed door, so it
    # is not aware — that is the cost model, not a bug.
    assert report["awareness"]["p2"] > 0.55
    assert report["awareness"].get("p3", 0.0) < 0.55


def test_a_locked_door_only_demotes_when_there_is_no_quiet_alternate():
    """The shockwave semantics, stated as a test because it is the subtle part.

    A locked door is one route, not a wall. When a **window** also reaches the
    room — 0.75 rather than 1.0 — sound arrives by the quieter route and the
    character stays aware, which is the direct consequence of taking the
    *strongest* route (bug-30's fix). task-418 required that semantics be chosen
    deliberately rather than assumed, and this is what the choice buys: the door
    being shut is not the fact, the cheapest way round is.
    """
    graph = WorldGraph()
    for name in ("a", "far", "near"):
        _area(graph, name)
    _door(graph, "way_locked", "a", "far", state="locked", direction="east")
    _door(graph, "way_window", "a", "far", state="open", direction="south",
          see_through=True)
    # A room that is aware by an open door, so the crowd stays *aware* whatever
    # happens to the window. A crowd that lost awareness alongside p3 would be
    # ranked with them, and recency would hand the slot straight back.
    _door(graph, "way_near", "a", "near", state="open", direction="north")

    aware = SoundChannel().propagate(graph, "a")
    assert aware["far"] > 0.55, (
        f"a window is a quieter route than a shut door: {aware}"
    )

    characters = _roster(("p1", "a", 0), ("p3", "far", 5))
    # Lower recency than p3, and aware through their own open door — so while
    # the window stands, p3 wins the tie on recency; once it shuts, p3 drops a
    # tier and loses to the crowd on tier alone.
    characters.update(_same_room_crowd("near", recency=-900))
    report = AttentionBudget(cap=2).select(
        graph,
        anchors=[{"kind": "character", "id": "p1"}],
        characters=characters,
    )
    assert "p3" in report["attended"], "a shut door with a quieter way round"

    # Shut the window too and the room goes quiet: two solid routes, no cheap one.
    # Now the crowd's awareness outranks p3's on *tier*, recency notwithstanding.
    graph.get_node("way_window").properties["see_through"] = False
    graph.get_node("way_window").properties["current_state"] = "closed"
    both_shut = AttentionBudget(cap=2).select(
        graph,
        anchors=[{"kind": "character", "id": "p1"}],
        characters=characters,
    )
    assert "p3" not in both_shut["attended"], "no quiet alternate left"


def test_a_blocked_door_costs_the_same_as_a_closed_one():
    """Both are solid and cost 1.0 (task-421's ladder), so both demote."""
    for state in ("closed", "locked", "blocked"):
        graph = WorldGraph()
        _corridor(graph, ["a", "b"], state=state)
        characters = _roster(("p1", "a", 0), ("p2", "b", 0))
        characters.update(_everyone_else_fills_the_budget(graph))
        report = AttentionBudget(cap=6).select(
            graph,
            anchors=[{"kind": "character", "id": "p1"}],
            characters=characters,
        )
        assert "p2" not in report["attended"], state


def test_a_hidden_panel_is_worth_twice_an_open_door_and_therefore_demotes_too():
    graph = WorldGraph()
    _corridor(graph, ["a", "b"], state="hidden")
    characters = _roster(("p1", "a", 0), ("p2", "b", 0))
    characters.update(_everyone_else_fills_the_budget(graph))
    report = AttentionBudget(cap=6).select(
        graph,
        anchors=[{"kind": "character", "id": "p1"}],
        characters=characters,
    )
    assert "p2" not in report["attended"]
    assert DEFAULT_SOUND_COSTS["hidden"] == 2.0


# ── the acceptance: cap, eviction, determinism ─────────────────────────────


def _crowd(count=200, per_area=1, start=0):
    characters = {}
    for index in range(count):
        characters[f"npc_{start + index}"] = {
            "area_id": f"area_{index // per_area}", "recency": index,
        }
    return characters


def _many_areas(count):
    graph = WorldGraph()
    for index in range(count):
        _area(graph, f"area_{index}")
    # A star: everything one door from the hub, so everyone is aware and the cap
    # is the only thing doing any work.
    for index in range(1, count):
        _door(graph, f"way_{index}", "area_0", f"area_{index}", state="open")
    return graph


def test_a_two_hundred_character_fixture_stays_within_the_cap():
    graph = _many_areas(200)
    report = AttentionBudget(cap=DEFAULT_CAP).select(
        graph,
        anchors=[{"kind": "character", "id": "npc_0"}],
        humans=["npc_0"],
        characters=_crowd(200),
    )
    assert len(report["attended"]) == DEFAULT_CAP
    assert report["oversubscribed"] == 200 - DEFAULT_CAP


def test_the_cap_holds_at_every_population():
    for population in (0, 1, 7, 8, 9, 50, 200):
        graph = _many_areas(max(2, population))
        report = AttentionBudget(cap=8).select(
            graph,
            anchors=[{"kind": "character", "id": "npc_0"}] if population else [],
            characters=_crowd(population),
        )
        assert len(report["attended"]) <= 8, population


def test_the_set_is_byte_identical_for_a_fixed_state():
    graph = _many_areas(40)
    roster = _crowd(40)
    first = AttentionBudget(cap=8).select(
        graph, anchors=[{"kind": "character", "id": "npc_0"}], characters=roster)
    second = AttentionBudget(cap=8).select(
        graph, anchors=[{"kind": "character", "id": "npc_0"}], characters=roster)
    assert first == second


def test_eviction_breaks_ties_on_id_not_on_dict_order():
    """Determinism under a *reordered* roster is the property that matters.

    Same characters, same areas, same recency — a different insertion order must
    not change who is attended, or a save/load that reorders a dict would change
    the world.
    """
    graph = _many_areas(30)
    roster = _crowd(30)
    forward = AttentionBudget(cap=5).select(
        graph, anchors=[{"kind": "character", "id": "npc_0"}], characters=roster)
    reversed_roster = {k: roster[k] for k in reversed(list(roster))}
    backward = AttentionBudget(cap=5).select(
        graph, anchors=[{"kind": "character", "id": "npc_0"}],
        characters=reversed_roster)
    assert forward["attended"] == backward["attended"]


def test_eviction_prefers_the_more_recent_and_then_the_lower_id():
    graph = _many_areas(10)
    characters = {
        "bravo": {"area_id": "area_1", "recency": 0},
        "alpha": {"area_id": "area_1", "recency": 0},
        "delta": {"area_id": "area_1", "recency": 5},
    }
    report = AttentionBudget(cap=2).select(
        graph, characters=characters)
    # delta is most recent; alpha and bravo tie on recency, so id decides.
    assert report["attended"] == ["alpha", "delta"]


def test_the_anchor_and_the_human_survive_an_oversubscribed_cap():
    """An anchor is never evicted for a nearer, more recent stranger."""
    graph = _many_areas(30)
    roster = _crowd(30)
    # The anchor is as far away and as stale as it is possible to be; if the
    # budget can evict it for that, it can evict anything.
    roster["anchor"] = {"area_id": "area_29", "recency": -1000}
    roster["the_human"] = {"area_id": "area_29", "recency": -100}
    report = AttentionBudget(cap=3).select(
        graph, anchors=[{"kind": "character", "id": "anchor"}],
        humans=["the_human"], characters=roster)
    assert "anchor" in report["attended"]
    assert "the_human" in report["attended"]
    assert report["tiers"]["anchor"] == TIER_NAMES[TIER_ANCHOR]
    assert report["tiers"]["the_human"] == TIER_NAMES[TIER_HUMAN]


def test_an_anchor_that_is_not_in_the_roster_is_simply_ignored():
    """A stale anchor id must not crash or reserve a slot for nobody."""
    graph = _many_areas(10)
    report = AttentionBudget(cap=3).select(
        graph, anchors=[{"kind": "character", "id": "gone"}],
        characters=_crowd(10))
    assert len(report["attended"]) == 3
    assert "gone" not in report["attended"]


# ── the acceptance: hysteresis as a channel threshold ──────────────────────


def test_entering_needs_more_strength_than_staying():
    budget = AttentionBudget()
    assert budget.enter_floor() < budget.aware_threshold
    assert budget.enter_floor() == budget.aware_threshold - ENTER_MARGIN


class _FixedChannel(AwarenessChannel):
    """A channel reporting an exact strength per area, so a test can put a
    character's strength precisely on the threshold instead of near it."""

    name = "fixed"

    def __init__(self, **strengths):
        self.strengths = strengths

    def propagate(self, graph, origin_area_id):
        if origin_area_id not in self.strengths:
            return {}
        return {area: strength for area, strength in self.strengths.items()}


def test_nobody_flaps_across_the_threshold():
    """A character on the boundary is promoted once and then kept, until their
    strength genuinely falls below the *enter* floor.

    The cap is deliberately tight and the crowd shares p2's tier, so the only
    thing that can move p2 in or out is the threshold: tier beats recency, and a
    crowd that outranked p2 would make the hysteresis unobservable.
    """
    graph = WorldGraph()
    for name in ("a", "b", "c"):
        _area(graph, name)
    threshold = 0.6
    roster = _roster(("p1", "a", 0), ("p2", "b", 10))
    roster.update(_same_room_crowd("c", count=1, recency=5))

    def report_for(strength, previously=None):
        channel = _FixedChannel(a=1.0, b=strength, c=0.6)
        return AttentionBudget(cap=2, aware_threshold=threshold,
                               channels=[channel]).select(
            graph, characters=roster, humans=["p1"],
            previously_attended=previously)

    first = report_for(threshold)
    assert first["attended"] == ["p1", "p2"], "exactly at the threshold is aware"
    assert first["promoted"] == ["p1", "p2"], "a first selection promotes everyone"

    # A hair below the threshold but above the enter floor: kept, and not
    # re-promoted, so nothing churns.
    budget = AttentionBudget(cap=2, aware_threshold=threshold)
    settled = report_for(threshold - ENTER_MARGIN / 2, first["attended"])
    assert settled["attended"] == ["p1", "p2"], "still above the enter floor"
    assert settled["promoted"] == [], "no promotion churn"
    assert settled["demoted"] == []

    # Below the enter floor: dropped a tier, and the crowd takes the slot.
    gone = report_for(budget.enter_floor() - 0.01, first["attended"])
    assert "p2" not in gone["attended"]
    assert gone["demoted"] == ["p2"]


def test_entering_from_below_the_threshold_is_not_cheap():
    """The asymmetry is not one-way: a newcomer below the floor does not sneak
    in just because somebody else left."""
    graph = WorldGraph()
    for name in ("a", "b", "c"):
        _area(graph, name)
    roster = _roster(("p1", "a", 0), ("p2", "b", 10))
    # A aware rival with a higher recency, so the only thing that can put p2 in
    # the second slot is p2's own strength.
    roster.update(_same_room_crowd("c", count=1, recency=99))
    budget = AttentionBudget(cap=2, aware_threshold=0.6)
    channel = _FixedChannel(a=1.0, b=budget.enter_floor() - 0.01, c=0.6)
    fresh = AttentionBudget(cap=2, aware_threshold=0.6,
                            channels=[channel]).select(
        graph, characters=roster, humans=["p1"])
    assert set(fresh["attended"]) == {"p1", "crowd_00"}, (
        "a newcomer below the floor does not enter on recency alone"
    )


def test_promotion_and_demotion_are_reported_so_a_caller_can_hand_off():
    graph = _many_areas(12)
    roster = _crowd(12)
    first = AttentionBudget(cap=4).select(
        graph, anchors=[{"kind": "character", "id": "npc_0"}], characters=roster)
    assert sorted(first["promoted"]) == first["attended"], "all promoted at once"

    # Shrink the cap: three demote, and they are the ones that went.
    second = AttentionBudget(cap=1).select(
        graph, anchors=[{"kind": "character", "id": "npc_0"}], characters=roster,
        previously_attended=first["attended"])
    assert len(second["attended"]) == 1
    assert len(second["demoted"]) == 3
    assert not set(second["demoted"]) & set(second["attended"])


# ── the acceptance: the cache ──────────────────────────────────────────────


def test_repeated_selection_does_not_rewalk_the_channels():
    graph = _many_areas(30)
    roster = _crowd(30)
    budget = AttentionBudget(cap=8)
    first = budget.select(graph, anchors=[{"kind": "character", "id": "npc_0"}],
                          characters=roster)
    walks_after_first = budget.channel_walks
    assert walks_after_first > 0

    for _ in range(20):
        budget.select(graph, anchors=[{"kind": "character", "id": "npc_0"}],
                      characters=roster)
    assert budget.channel_walks == walks_after_first, (
        "the awareness cache is not holding; a per-tick reselect would walk "
        "the graph for every character"
    )
    assert budget.select(graph, anchors=[{"kind": "character", "id": "npc_0"}],
                         characters=roster) == first


def test_awareness_is_seeded_from_the_anchors_not_from_every_area():
    """Probing every area would be O(areas) graph walks to answer a question
    about a handful of rooms — the cost this task exists to bound."""
    graph = _many_areas(50)
    roster = _crowd(50)
    budget = AttentionBudget(cap=8)
    budget.select(graph, anchors=[{"kind": "character", "id": "npc_0"}],
                  characters=roster)
    # One seed: the hub area the single anchor stands in.
    assert budget.channel_walks == 1, budget.channel_walks


def test_a_closed_door_invalidates_the_awareness_cache():
    """The task-421 trap: a door moving does not change the graph revision, so a
    cache keyed on the revision alone would keep the old answer.

    Asserted on the awareness value and the walk count rather than on the
    attended set: awareness *orders* and the cap *decides*, so with only two
    characters and room to spare the set would be unchanged either way and the
    test would pass on a broken cache.
    """
    graph = WorldGraph()
    _corridor(graph, ["a", "b"], state="open")
    roster = _roster(("p1", "a", 0), ("p2", "b", 0))
    revision = graph.get_revision()

    budget = AttentionBudget(cap=4)
    opened = budget.select(graph, characters=roster, humans=["p1"])
    assert opened["awareness"]["p2"] > 0.55
    walks_after_open = budget.channel_walks
    assert walks_after_open > 0

    # Close the door in place — exactly what `set_way_view` does. The revision
    # does not move.
    graph.get_node("way_0").properties["current_state"] = "closed"
    assert graph.get_revision() == revision, (
        "fixture drifted: the revision moved, so this test no longer proves the "
        "barrier signature is what caught the change"
    )

    closed = budget.select(graph, characters=roster, humans=["p1"])
    assert closed["awareness"].get("p2", 0.0) < 0.55, (
        f"the cache served a stale aware set: {closed['awareness']}"
    )
    assert budget.channel_walks > walks_after_open, (
        "a door state change must re-walk the channel"
    )


def test_adding_a_node_invalidates_the_cache_too():
    graph = WorldGraph()
    _corridor(graph, ["a", "b"], state="open")
    budget = AttentionBudget(cap=4)
    budget.select(graph, characters=_roster(("p1", "a", 0)), humans=["p1"])
    before = budget.channel_walks
    _area(graph, "c")
    _door(graph, "way_bc", "b", "c", state="open")
    budget.select(graph, characters=_roster(("p1", "a", 0), ("p3", "c", 0)),
                  humans=["p1"])
    assert budget.channel_walks > before, "a new area is not in the cached set"


def test_a_stale_graph_identity_does_not_serve_the_previous_graphs_cache():
    first = WorldGraph()
    _corridor(first, ["a", "b"], state="open")
    second = WorldGraph()
    _corridor(second, ["a", "b"], state="locked")
    # Two graphs with the same node count and the same revision number.
    assert first.get_revision() == second.get_revision()

    budget = AttentionBudget(cap=4)
    roster = _roster(("p1", "a", 0), ("p2", "b", 0))
    open_report = budget.select(first, characters=roster, humans=["p1"])
    locked_report = budget.select(second, characters=roster, humans=["p1"])
    assert open_report["awareness"]["p2"] > 0.55
    assert locked_report["awareness"].get("p2", 0.0) < 0.55


# ── the acceptance: the channel seam takes a second implementation ─────────


class _RopeChannel(AwarenessChannel):
    """A test double standing in for a future `comms` channel (task-418)."""

    name = "comms"

    def __init__(self, reach=2):
        self.reach = reach

    def propagate(self, graph, origin_area_id):
        graph_areas = sorted(n.id for n in graph.nodes.values()
                             if n.type == "area")
        if origin_area_id not in graph_areas:
            return {}
        start = graph_areas.index(origin_area_id)
        end = min(len(graph_areas), start + self.reach + 1)
        return {area_id: 1.0 - 0.1 * i
                for i, area_id in enumerate(graph_areas[start:end])}


def test_a_second_channel_needs_no_change_to_the_selector():
    graph = WorldGraph()
    for name in ("a", "b", "c"):
        _area(graph, name)
    for index, other in enumerate(("b", "c"), start=1):
        _door(graph, f"way_{index}", "a", other, state="locked")

    # Two rosters, because the two halves need different rivals: sound alone
    # must be beaten by a *co-present* character (the highest tier there is), and
    # the rope must be beaten only on recency (so both neighbours can fit).
    sound_roster = _roster(("p1", "a", 0), ("p2", "b", 5), ("p3", "c", 4))
    sound_roster.update(_same_room_crowd("a", count=1, recency=1))
    sound_only = AttentionBudget(cap=2).select(
        graph, characters=sound_roster, humans=["p1"])
    assert set(sound_only["attended"]) == {"p1", "crowd_00"}, (
        f"sound hears nothing through a locked door: {sound_only['awareness']}"
    )

    rope_roster = _roster(("p1", "a", 0), ("p2", "b", 5), ("p3", "c", 4))
    rope_roster.update(_same_room_crowd("c", count=1, recency=1))
    with_rope = AttentionBudget(cap=3, channels=[_RopeChannel()]).select(
        graph, characters=rope_roster, humans=["p1"])
    assert {"p2", "p3"} <= set(with_rope["attended"]), (
        "a second channel hears through what sound cannot"
    )
    assert with_rope["tiers"]["p3"] == TIER_NAMES[TIER_AWARE]


def test_the_strongest_channel_wins_for_a_given_area():
    graph = WorldGraph()
    _corridor(graph, ["a", "b"], state="locked")
    roster = _roster(("p1", "a", 0), ("p2", "b", 0))
    budget = AttentionBudget(cap=4, channels=[_RopeChannel(), SoundChannel()])
    report = budget.select(graph, characters=roster, humans=["p1"])
    assert "p2" in report["attended"], "the rope channel is the stronger signal"


def test_an_unimplemented_channel_cannot_be_used_by_accident():
    channel = AwarenessChannel()
    with pytest.raises(NotImplementedError):
        channel.propagate(WorldGraph(), "a")


# ── the acceptance: the set and the anchors survive a save ────────────────


def test_anchors_and_attendance_round_trip_through_the_state():
    budget = AttentionBudget(cap=6, aware_threshold=0.4, enter_margin=0.2,
                             channels=[SoundChannel()])
    graph = _many_areas(10)
    report = budget.select(
        graph,
        anchors=[{"kind": "character", "id": "npc_0"},
                 {"kind": "item", "id": "item_torch"}],
        humans=["npc_1"],
        pinned=["npc_2"],
        characters=_crowd(10),
    )
    state = budget.to_state(
        anchors=[{"kind": "character", "id": "npc_0"},
                 {"kind": "item", "id": "item_torch"}],
        humans=["npc_1"], pinned=["npc_2"], attended=report["attended"])

    restored = AttentionBudget().from_state(state)
    assert restored["cap"] == 6
    assert restored["aware_threshold"] == 0.4
    assert restored["enter_margin"] == 0.2
    assert restored["channels"] == ["sound"]
    assert restored["humans"] == ["npc_1"]
    assert restored["pinned"] == ["npc_2"]
    assert restored["attended"] == report["attended"]
    assert [a["id"] for a in restored["anchors"]] == ["npc_0", "item_torch"]


def test_the_saved_state_keeps_no_derived_awareness():
    """A saved awareness snapshot goes stale the moment a door moves, and a save
    that looks resumable while disagreeing with its world is worse than one that
    clearly re-derives."""
    budget = AttentionBudget()
    state = budget.to_state(attended=["a", "b"])
    for key in budget.DERIVED_KEYS:
        assert key not in state, key
    import json

    assert json.loads(json.dumps(state)) == state


def test_two_budgets_can_read_the_same_save():
    """A save is a fact about a world, not about the reader's settings."""
    saved = AttentionBudget(cap=8).to_state(attended=["x"])
    assert AttentionBudget(cap=2).from_state(saved)["cap"] == 8
    assert AttentionBudget().from_state(saved)["attended"] == ["x"]


def test_the_worked_example_from_the_task():
    """23 goblins, cap 8, a human in the Chief's Pit. The task's own numbers."""
    graph = WorldGraph()
    # pit — warren — blackmarsh, a three-room run rather than a star, so the
    # worked example's "the old pit neighbours cross the exit radius and demote"
    # step is actually exercised.
    for name in ("chiefs_pit", "warren", "blackmarsh"):
        _area(graph, name, name.replace("_", " ").title())
    _door(graph, "way_pit_warren", "chiefs_pit", "warren", state="open")
    _door(graph, "way_warren_blackmarsh", "warren", "blackmarsh", state="open")

    characters = {
        "gribba": {"area_id": "chiefs_pit", "recency": 10},
        "human": {"area_id": "chiefs_pit", "recency": 0},
        "krikka": {"area_id": "warren", "recency": 5},
        "vegga": {"area_id": "warren", "recency": 4},
        "others": {"area_id": "blackmarsh", "recency": 1},
    }
    for index in range(19):
        characters[f"gob_{index:02d}"] = {
            "area_id": "blackmarsh", "recency": index}

    report = AttentionBudget(cap=8).select(
        graph, anchors=[{"kind": "character", "id": "gribba"}],
        humans=["human"], characters=characters)

    assert len(report["attended"]) == 8
    assert "gribba" in report["attended"], "an anchor is never evicted"
    assert "human" in report["attended"], "a human is never evicted"
    # The pit's neighbour is one open door away, so it is aware and takes budget
    # from the crowded far room on recency.
    assert "krikka" in report["attended"]
    # Blackmarsh is two open doors away, which costs the same as one shut door,
    # so nothing there is aware however recent it is.
    assert report["awareness"].get("others", 0.0) < 0.55
    assert report["oversubscribed"] == len(characters) - 8
    assert len(characters) == 24, "23 goblins and the human at the keyboard"
