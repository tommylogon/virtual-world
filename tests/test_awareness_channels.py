"""Awareness channels: audibility replaces a hop radius (task-418).

The point of retiring `radius_hops` is that a barrier can *reason*. A hop radius
can only count; a locked door can exclude. So the load-bearing test here is the
one that says sound reaches B through an open door and does not reach C through a
locked one — and that it stops reaching C the instant the door is locked, without
anything being told to invalidate a cache.

The rest is the seam: one implemented channel, one test double, and a selection
that is bounded by a cap and reproducible for a fixed state.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.awareness import (
    Anchor,
    AwarenessIndex,
    ChannelContext,
    SoundChannel,
    normalise_anchors,
    select_attended,
)
from graph import EDGE_CONNECTION, Edge, Node, WorldGraph

# A shout is 2 and a scream is 3, so a two-solid-door chain (1 + 1 = 2) is
# exactly the boundary these tests sit on.
OPEN, LOCKED, CLOSED = "open", "locked", "closed"


def _room(graph, name):
    room = Node(id=name, type="area", name=name, properties={})
    graph.add_node(room)
    return room


def _join(graph, a, b, state=OPEN, **way_props):
    """Two areas, one way between them, with a real acoustic barrier."""
    way_id = f"way_{a}__{b}"
    way = Node(id=way_id, type="way", name=way_id,
               properties={"current_state": state, **way_props})
    graph.add_node(way)
    graph.add_edge(Edge(source=a, target=way_id, type=EDGE_CONNECTION))
    graph.add_edge(Edge(source=way_id, target=a, type=EDGE_CONNECTION))
    graph.add_edge(Edge(source=b, target=way_id, type=EDGE_CONNECTION))
    graph.add_edge(Edge(source=way_id, target=b, type=EDGE_CONNECTION))
    return way


def _two_rooms(state=OPEN, **way_props):
    """A — B, one way between them."""
    graph = WorldGraph()
    _room(graph, "A")
    _room(graph, "B")
    return graph, _join(graph, "A", "B", state, **way_props)


def _three_rooms(second_state=OPEN):
    """A — B — C, with the barrier state of the *second* way configurable."""
    graph = WorldGraph()
    for name in ("A", "B", "C"):
        _room(graph, name)
    _join(graph, "A", "B", OPEN)
    second = _join(graph, "B", "C", second_state)
    return graph, second


# ── the barrier test the task asks for ────────────────────────────────────
#
# The engine's scale: whisper 0, normal 1, shout 2, scream 3; open door 0.5,
# see-through 0.75, closed/locked 1, hidden 2. So normal speech (1) crosses one
# open door (0.5, leaving 0.5) and dies on the next closed one (total 1.5).
# Every test below names its penetration rather than relying on a default,
# because the arithmetic is the thing under test.

def test_sound_reaches_through_an_open_door():
    graph, _ = _three_rooms(OPEN)
    index = AwarenessIndex(graph, [SoundChannel(penetration=1)])

    assert set(index.aware_from("A")) == {"A", "B"}, "one open door carries"


def test_a_locked_door_cuts_off_the_room_behind_it():
    graph, _ = _three_rooms(LOCKED)
    index = AwarenessIndex(graph, [SoundChannel(penetration=1)])

    aware = index.aware_from("A")
    assert "B" in aware, "the open door still carries"
    assert "C" not in aware, "C is behind a locked door and is not audible"
    assert index.is_aware("A", "B")
    assert not index.is_aware("A", "C")


def test_a_closed_door_cuts_off_the_room_behind_it():
    graph, _ = _three_rooms(CLOSED)
    index = AwarenessIndex(graph, [SoundChannel(penetration=1)])

    assert set(index.aware_from("A")) == {"A", "B"}


def test_a_lock_is_a_latch_not_a_wall():
    """A shout crosses one locked door, and it should.

    `engine/sound.py` gives locked and closed the same barrier because a lock is
    a latch on an already-closed door and adds no acoustic mass. A channel that
    treated a locked door as soundproof would be inventing physics, so this is
    pinned: exclusion comes from a *chain* of barriers, not from one latch.
    """
    graph, _ = _three_rooms(LOCKED)
    assert AwarenessIndex(graph, [SoundChannel(penetration=2)]).is_aware("A", "C"), (
        "one locked door does not stop a shout")

    # A — B open, B — C locked, C — D locked: 0.5 + 1 + 1 = 2.5, which a shout
    # (2) does not survive. C itself is still heard.
    chained = WorldGraph()
    for name in ("A", "B", "C", "D"):
        _room(chained, name)
    _join(chained, "A", "B", OPEN)
    _join(chained, "B", "C", LOCKED)
    _join(chained, "C", "D", LOCKED)
    far = AwarenessIndex(chained, [SoundChannel(penetration=2)])
    assert far.is_aware("A", "C"), "two doors in, still audible"
    assert not far.is_aware("A", "D"), "three doors in, not"


def test_the_door_is_the_only_difference_between_those_two_answers():
    """Same graph, one property changed — so the exclusion is the door's doing.

    A single door is the cleanest fixture: normal speech (1) leaves 0.5 through
    an open door and 0 through a closed one, and 0 is not audible.
    """
    graph, way = _two_rooms(CLOSED)
    index = AwarenessIndex(graph, [SoundChannel(penetration=1)])
    assert not index.is_aware("A", "B")

    way.properties["current_state"] = OPEN
    assert index.is_aware("A", "B"), "and the cache noticed"


def test_a_see_through_way_is_quieter_than_open_and_quieter_than_solid():
    """Three barriers, three strengths, in the order a wall implies."""
    def strength(state, **props):
        graph, _ = _two_rooms(state, **props)
        channel = SoundChannel(penetration=3)
        return channel.propagate(graph, "A")["B"]

    through_window = strength(CLOSED, see_through=True)   # barrier 0.75
    through_open = strength(OPEN)                          # barrier 0.5
    through_wall = strength(CLOSED)                        # barrier 1.0
    assert 0 < through_wall < through_window < through_open, (
        "barriers run open 0.5 < see-through 0.75 < solid 1.0, so loudness runs "
        "the other way: a bare opening carries most, a gridded window less, and "
        "a wall least")


def test_a_hidden_way_stops_a_shout_but_not_a_scream():
    graph, _ = _two_rooms("hidden")
    assert not AwarenessIndex(graph, [SoundChannel(penetration=2)]).is_aware("A", "B")
    assert AwarenessIndex(graph, [SoundChannel(penetration=3)]).is_aware("A", "B")


def test_the_threshold_demotes_rather_than_cuts():
    """One channel's threshold must not be another channel's business."""
    graph, _ = _three_rooms(LOCKED)
    shout = SoundChannel(penetration=2, threshold=0.5)
    index = AwarenessIndex(graph, [shout])
    # A arrives at 1.0, B at 0.75, C at 0.25.
    assert set(index.aware_from("A")) == {"A", "B"}, "C is below the bar already"

    shout.threshold = 0.8
    index.invalidate()
    assert set(index.aware_from("A")) == {"A"}, "raising the bar demotes B too"


# ── the seam ─────────────────────────────────────────────────────────────


class _TeleportChannel:
    """A second channel, to prove the seam without implementing comms or magic."""

    name = "teleport"

    def __init__(self, links=()):
        self.links = dict(links)      # origin area id -> {area id: strength}
        self.calls = 0

    def propagate(self, graph, origin_area_id, context=None):
        self.calls += 1
        out = {origin_area_id: 1.0}
        out.update(self.links.get(origin_area_id, {}))
        return out


def test_a_second_channel_needs_only_propagate():
    graph, _ = _three_rooms(LOCKED)
    # Normal speech, so sound cannot reach C and the teleport link is the only
    # thing that can — which is the point of a second channel.
    index = AwarenessIndex(graph, [SoundChannel(penetration=1),
                                   _TeleportChannel({"A": {"C": 0.4}})])

    aware = index.aware_from("A")
    assert "C" in aware, "the locked door is irrelevant to magic"
    assert aware["C"] == 0.4, "and the strength is the channel's own"


def test_channels_combine_rather_than_overwrite():
    graph, _ = _three_rooms(LOCKED)
    weak = _TeleportChannel({"A": {"C": 0.2}})
    strong = _TeleportChannel({"A": {"C": 0.8}})
    index = AwarenessIndex(graph, [SoundChannel(penetration=1), weak, strong])

    assert index.aware_from("A")["C"] == 0.8, "the strongest channel wins"


def test_the_origin_is_always_aware_of_itself():
    graph, _ = _three_rooms(LOCKED)
    index = AwarenessIndex(graph, [_TeleportChannel()])
    assert index.aware_from("A") == {"A": 1.0}, "so callers need no special case"


def test_an_unknown_origin_is_empty_rather_than_an_error():
    graph, _ = _three_rooms(OPEN)
    index = AwarenessIndex(graph, [SoundChannel()])
    assert index.aware_from("nowhere") == {}
    assert index.aware_from("") == {}


def test_one_broken_channel_does_not_blind_the_others():
    class Broken:
        name = "broken"

        def propagate(self, graph, origin_area_id, context=None):
            raise RuntimeError("this channel is not implemented yet")

    graph, _ = _three_rooms(OPEN)
    index = AwarenessIndex(graph, [Broken(), SoundChannel()])
    assert set(index.aware_from("A")) == {"A", "B", "C"}, "sound still answered"


def test_a_context_shares_the_area_map_across_channels():
    graph, _ = _three_rooms(OPEN)
    ctx = ChannelContext(graph)
    first = SoundChannel()
    second = _TeleportChannel()
    first.propagate(graph, "A", ctx)
    second.propagate(graph, "A", ctx)
    assert ctx.areas is not None, "the map was built once, not per channel"


# ── caching ──────────────────────────────────────────────────────────────


def test_awareness_is_cached_between_queries():
    graph, _ = _three_rooms(OPEN)
    channel = _TeleportChannel()
    index = AwarenessIndex(graph, [channel])

    index.aware_from("A")
    index.aware_from("A")
    index.aware_from("A")
    assert channel.calls == 1, "the same origin is not re-walked every tick"


def test_a_graph_change_invalidates_the_cache():
    graph, _ = _three_rooms(OPEN)
    channel = _TeleportChannel()
    index = AwarenessIndex(graph, [channel])
    index.aware_from("A")

    _room(graph, "D")
    index.aware_from("A")
    assert channel.calls == 2, "adding an area is a graph revision"


def test_caching_is_per_origin_not_global():
    graph, _ = _three_rooms(OPEN)
    channel = _TeleportChannel()
    index = AwarenessIndex(graph, [channel])
    index.aware_from("A")
    index.aware_from("B")
    assert channel.calls == 2, "each origin walks once"


# ── the attended set ─────────────────────────────────────────────────────


def _roster(where):
    """A `characters_by_area` callable over a fixed {area: [ids]} map."""
    return lambda area: list(where.get(area, ()))


def test_an_anchor_is_attended_and_its_room_comes_with_it():
    aware = {"pit": {"pit": 1.0}}
    where = {"pit": ["Gribba", "Krikka"]}
    attended = select_attended(
        [Anchor("human", "Human")], {"Human": "pit"}, aware,
        _roster(where), cap=8)
    assert attended == ["Human", "Gribba", "Krikka"], "anchor, then the room"


def test_a_character_behind_a_locked_door_is_not_attended():
    """The acceptance case, end to end through the real channel."""
    graph, _ = _three_rooms(LOCKED)
    index = AwarenessIndex(graph, [SoundChannel(penetration=1)])
    where = {"A": ["Watcher"], "B": ["Middle"], "C": ["Behind"]}

    attended = select_attended(
        [Anchor("character", "Watcher")], {"Watcher": "A"},
        {"A": index.aware_from("A")}, _roster(where), cap=8)

    assert "Behind" not in attended
    assert "Middle" in attended, "the open door still carries"
    assert attended[0] == "Watcher"


def test_the_set_never_exceeds_the_cap_however_many_can_hear():
    where = {f"room{i}": [f"N{i}a", f"N{i}b"] for i in range(50)}
    aware = {f"room{i}": {f"room{j}": 0.5 for j in range(50)} for i in range(50)}
    attended = select_attended(
        [Anchor("character", "N0a")], {"N0a": "room0"}, aware,
        _roster(where), cap=8)
    assert len(attended) == 8, "100 candidates, 8 seats"


def test_eviction_is_deterministic_for_a_fixed_state():
    where = {f"room{i}": [f"N{i}"] for i in range(20)}
    aware = {f"room{i}": {f"room{j}": 0.5 for j in range(20)} for i in range(20)}
    args = ([Anchor("character", "N0")], {"N0": "room0"}, aware, _roster(where), 5)
    first = select_attended(*args)
    assert all(select_attended(*args) == first for _ in range(5)), "stable"
    assert first == sorted(first), "ties break by id, so the order is the id order"


def test_recency_breaks_ties_inside_a_tier():
    where = {"pit": ["Late", "Early"]}
    aware = {"pit": {"pit": 1.0}}
    attended = select_attended(
        [Anchor("character", "W")], {"W": "pit"}, aware, _roster(where), cap=3,
        recency={"Early": 900, "Late": 100, "W": 1000})
    assert attended == ["W", "Early", "Late"], "most recent first, within a tier"


def test_a_hook_admits_someone_nothing_can_perceive():
    where = {"pit": ["Watcher"], "far": ["Stranger"]}
    aware = {"pit": {"pit": 1.0}}
    attended = select_attended(
        [Anchor("character", "Watcher")], {"Watcher": "pit"}, aware,
        _roster(where), cap=8, hooks=["Stranger"])
    assert "Stranger" in attended, "a mid-quest character is attended anyway"
    assert attended[-1] == "Stranger", "but at the lowest tier"


def test_no_anchors_attends_nobody():
    aware = {"pit": {"pit": 1.0}}
    assert select_attended([], {}, aware, _roster({"pit": ["W"]}), cap=8) == []


def test_a_cap_of_zero_attends_nobody():
    aware = {"pit": {"pit": 1.0}}
    assert select_attended(
        [Anchor("character", "W")], {"W": "pit"}, aware,
        _roster({"pit": ["W"]}), cap=0) == []


def test_an_anchor_with_no_known_area_is_still_attended():
    """A followed character is attended even before anyone knows where they are."""
    attended = select_attended(
        [Anchor("character", "Gribba")], {}, {}, _roster({}), cap=8)
    assert attended == ["Gribba"]


def test_only_audible_rooms_are_asked_about():
    """The perf claim: the roster is not scanned, the *aware* rooms are."""
    asked = []

    def spy(area):
        asked.append(area)
        return ["W"] if area == "pit" else []

    aware = {"pit": {"pit": 1.0, "next": 0.4, "far": 0.2, "inaudible": None}}
    del aware["pit"]["inaudible"]
    select_attended([Anchor("character", "W")], {"W": "pit"}, aware,
                    spy, cap=8)
    assert sorted(asked) == ["far", "next", "pit"]
    assert asked.count("pit") == 1, "the origin's room is asked about once"


# ── anchor normalisation ─────────────────────────────────────────────────


def test_anchors_normalise_from_dicts_ids_and_anchors():
    anchors = normalise_anchors([
        {"kind": "human", "id": "player_human"},
        "player_gribba",
        Anchor("item", "item_water_skin"),
        {"kind": "item", "id": ""},        # blank: dropped
        None,
    ])
    assert [(a.kind, a.id) for a in anchors] == [
        ("human", "player_human"),
        ("character", "player_gribba"),
        ("item", "item_water_skin"),
    ]


def test_a_duplicate_anchor_appears_once_and_keeps_its_first_position():
    anchors = normalise_anchors([
        {"kind": "human", "id": "A"},
        {"kind": "character", "id": "B"},
        {"kind": "human", "id": "A"},
    ])
    assert [(a.kind, a.id) for a in anchors] == [("human", "A"), ("character", "B")]


def test_an_item_anchor_contributes_its_area_but_is_not_attended_itself():
    """A pinned place is a where, not a who."""
    where = {"vault": ["Guard"]}
    aware = {"vault": {"vault": 1.0}}
    attended = select_attended(
        [Anchor("item", "item_key")], {"item_key": "vault"}, aware,
        _roster(where), cap=8)
    assert attended == ["Guard"], "the pin pulled the room in, not the key"


# ── the perf claim, through the real entry point ─────────────────────────


class _CountingRoster(dict):
    """A roster dict that records how many times it is iterated wholesale."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scans = 0

    def items(self):
        self.scans += 1
        return super().items()

    def values(self):
        self.scans += 1
        return super().values()

    def keys(self):
        self.scans += 1
        return super().keys()


def _world_with(population):
    """A world of `population` characters, all in one room, on a real graph."""
    from app import create_app
    from area import Area
    from player import Player

    world = create_app({"TESTING": True}).world
    room = "Attended Hall"
    if room not in getattr(world, "areas", {}):
        world.movement.add_area(Area(room, "a room everyone is in.", []))
    for i in range(population):
        p = Player(f"Bench {i}")
        world.add_player(p)
        world.set_player_area(p.name, room)
    return world


def _scans_for_attendance(population):
    world = _world_with(population)
    world.tick_manager._presence_reset()
    roster = _CountingRoster(world.player_manager.players)
    world.player_manager.players = roster
    attended = world.tick_manager.attended_set(
        [Anchor("character", "Bench 0")], cap=8)
    return roster.scans, attended


def test_building_the_attended_set_does_not_scan_the_roster():
    """200 characters in one room, 8 seats, and the roster is never walked.

    Candidates come from the task-416 presence buckets of the rooms a channel
    found audible. That is the reason a hop radius is not needed: the scan
    follows awareness, so it grows with how much of the world is audible rather
    than with how many characters exist.
    """
    scans, attended = _scans_for_attendance(8)
    assert len(attended) == 8, "the cap holds"
    assert scans <= 2, f"an attended set cost {scans} roster passes"

    big_scans, big_attended = _scans_for_attendance(200)
    assert len(big_attended) == 8, "still 8 seats at 200 characters"
    assert big_scans == scans, (
        f"roster passes grew from {scans} to {big_scans} when the population "
        "went from 8 to 200 — the set is scanning the population again")


def test_the_attended_set_comes_from_the_presence_buckets():
    world = _world_with(6)
    attended = world.tick_manager.attended_set(
        [Anchor("character", "Bench 0")], cap=4)
    assert attended[0] == "Bench 0", "the anchor leads"
    assert len(attended) == 4
    assert set(attended) <= set(world.player_manager.players), (
        "and everyone in it is a real character")


def test_no_anchors_attends_nobody_through_the_entry_point():
    world = _world_with(4)
    assert world.tick_manager.attended_set([], cap=8) == []


def test_a_cap_of_zero_attends_nobody_through_the_entry_point():
    world = _world_with(4)
    assert world.tick_manager.attended_set(
        [Anchor("character", "Bench 0")], cap=0) == []
