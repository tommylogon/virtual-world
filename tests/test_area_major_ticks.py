"""The per-tick sweep is area-major, and co-presence is an index lookup.

Two claims are under test.

**Co-presence is grouped, not rescanned.** "Who else is standing here" used to
be reconstructed at every site that needed it, by scanning the whole roster once
per character — quadratic in the population, which is what made a large world
tick slowly. It is now a reverse index built once per turn.

**Iteration order is not turn order.** Area grouping decides the order that
*scoped* evaluation runs in — which is why an area's own on_tick items fire
together, in sorted area-id order. It must never decide who acts: the character
loop still walks the roster in registry order, and co-presence returns the same
set, in the same order, the old scan did.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from graph import EDGE_IN, EDGE_TRIGGERS, Edge, Node
from player import Player

HALL = "Great Hall"
YARD = "Sunny Yard"
CELLAR = "Damp Cellar"


def _world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _area(world, name):
    if name not in getattr(world, "areas", {}):
        world.movement.add_area(Area(name, f"{name} description.", []))
    return name


def _place(world, name, area):
    p = world.player_manager.players.get(name)
    if p is None:
        p = Player(name)
        world.add_player(p)
    world.set_player_area(name, area)
    return p


def _populated(world, per_area):
    """Place `per_area` characters in each named area, in a known roster order."""
    for area, count in per_area.items():
        _area(world, area)
        for i in range(count):
            _place(world, f"{area} {i}", area)


# ── the presence index ────────────────────────────────────────────────────


def test_characters_in_one_area_share_one_bucket():
    world = _world()
    _populated(world, {HALL: 3, YARD: 1})

    world.tick_manager._presence_reset()

    assert sorted(world.tick_manager.co_present(f"{HALL} 0")) == [
        f"{HALL} 1", f"{HALL} 2",
    ]
    assert world.tick_manager.co_present(f"{YARD} 0") == []
    assert [k for k, _ in world.tick_manager.characters_in(HALL)] == [
        f"{HALL} 0", f"{HALL} 1", f"{HALL} 2",
    ]


def test_characters_in_different_areas_never_meet():
    world = _world()
    _populated(world, {HALL: 2, YARD: 2, CELLAR: 1})

    world.tick_manager._presence_reset()

    for key in (f"{HALL} 0", f"{HALL} 1", f"{YARD} 0", f"{YARD} 1", f"{CELLAR} 0"):
        for other in world.tick_manager.co_present(key):
            assert world.tick_manager.area_of(other) == world.tick_manager.area_of(key)


def test_co_present_agrees_with_the_scan_it_replaced():
    """Same set, same order as the old inline `for n, op in players.items()` scan."""
    world = _world()
    _populated(world, {HALL: 3, YARD: 2})
    dead = _place(world, f"{HALL} dead", HALL)
    dead.state = "dead"
    elsewhere = _place(world, "Outlier", CELLAR)
    _area(world, CELLAR)
    world.set_player_area("Outlier", CELLAR)

    world.tick_manager._presence_reset()

    for key in world.player_manager.players:
        p = world.player_manager.players[key]
        expected = [
            n for n, op in world.player_manager.players.items()
            if op.current_area == p.current_area and n != key
            and op.state != "dead" and not world.is_undead_ghost(n)
        ]
        assert world.tick_manager.co_present(key) == expected
    assert elsewhere.name == "Outlier"


def test_the_index_follows_a_character_who_moves():
    world = _world()
    _populated(world, {HALL: 2})
    tm = world.tick_manager
    tm._presence_reset()

    mover = world.player_manager.players[f"{HALL} 0"]
    mover.current_area = YARD
    tm._presence_sync(f"{HALL} 0", mover)

    assert tm.area_of(f"{HALL} 0") == YARD
    assert tm.co_present(f"{HALL} 0") == []
    assert tm.co_present(f"{HALL} 1") == []
    assert [k for k, _ in tm.characters_in(HALL)] == [f"{HALL} 1"]


def test_an_empty_bucket_is_dropped():
    """A room nobody is left in costs nothing — no stale entry lingers."""
    world = _world()
    _populated(world, {HALL: 1})
    tm = world.tick_manager
    tm._presence_reset()
    assert HALL in tm._presence_by_area

    p = world.player_manager.players[f"{HALL} 0"]
    p.current_area = None
    tm._presence_sync(f"{HALL} 0", p)

    assert HALL not in tm._presence_by_area
    assert tm.area_of(f"{HALL} 0") is None


# ── the area-major item sweep ─────────────────────────────────────────────


def _ticking_item(world, area, item_id, uses=None):
    """A plain item in `area` that owns an on_tick trigger (the task-406 shape)."""
    area_id = world._area_node_id(area)
    node = Node(id=item_id, type="item", name=item_id, properties={})
    if uses is not None:
        node.properties["uses"] = uses
    world.graph.add_node(node)
    world.graph.add_edge(Edge(source=item_id, target=area_id, type=EDGE_IN))
    trigger = Node(id=f"trig_{item_id}", type="logic_trigger", name=f"trig_{item_id}")
    world.graph.add_node(trigger)
    world.graph.add_edge(Edge(
        source=item_id, target=trigger.id, type=EDGE_TRIGGERS,
        properties={"trigger_type": "on_tick"},
    ))
    return node


def _record_ticks(world, log):
    original = world.triggers._execute_triggers

    def recording(node, trigger_type, *args, **kwargs):
        if trigger_type == "on_tick":
            log.append(node.id)
        return original(node, trigger_type, *args, **kwargs)

    world.triggers._execute_triggers = recording
    return original


def test_standing_on_tick_items_fire_once_each_in_sorted_area_order():
    """Two rooms, two ticking items: room order, not graph insertion order."""
    world = _world()
    _area(world, YARD)
    _area(world, CELLAR)
    # Cellar is added *first* on purpose: graph insertion order would run it
    # first, and the area-major sweep must not depend on that.
    late = _ticking_item(world, YARD, "item_late")
    early = _ticking_item(world, CELLAR, "item_early")

    log = []
    original = _record_ticks(world, log)
    try:
        world.tick_manager.tick_turn(skip_npcs=True)
    finally:
        world.triggers._execute_triggers = original

    fired = [i for i in log if i in ("item_late", "item_early")]
    assert fired == ["item_early", "item_late"], "sorted by area id, once each"
    assert late.id == "item_late" and early.id == "item_early"


def test_a_carrying_character_does_not_also_fire_the_item_standing_here():
    """Carried items tick in the character loop; the sweep must not re-fire them."""
    from graph import EDGE_CARRYING

    world = _world()
    _area(world, HALL)
    _ticking_item(world, HALL, "item_torch")
    holder = _place(world, "Torchbearer", HALL)
    world.graph.add_edge(Edge(
        source="item_torch", target=world.player_manager.get_player_node_id(
            holder.name), type=EDGE_CARRYING,
    ))

    log = []
    original = _record_ticks(world, log)
    try:
        world.tick_manager.tick_turn(skip_npcs=True)
    finally:
        world.triggers._execute_triggers = original

    assert log.count("item_torch") == 1


def test_areas_with_nothing_to_tick_are_never_visited():
    world = _world()
    _populated(world, {HALL: 1})
    _area(world, YARD)

    tm = world.tick_manager
    tm._presence_reset()
    standing = tm._standing_items_by_area()
    assert world._area_node_id(YARD) not in standing, (
        "an empty room contributes no standing items, so the sweep skips it"
    )

    _ticking_item(world, YARD, "item_only_here")
    standing = tm._standing_items_by_area()
    assert world._area_node_id(YARD) in standing


def test_placement_cache_follows_a_moved_item():
    world = _world()
    _area(world, HALL)
    _area(world, YARD)
    item = _ticking_item(world, HALL, "item_mover")

    tm = world.tick_manager
    hall_id, yard_id = world._area_node_id(HALL), world._area_node_id(YARD)
    assert item in tm._standing_items_by_area()[hall_id]
    assert yard_id not in tm._standing_items_by_area()

    world.graph.remove_edge("item_mover", hall_id, EDGE_IN)
    world.graph.add_edge(Edge(source="item_mover", target=yard_id, type=EDGE_IN))

    standing = tm._standing_items_by_area()
    assert item not in standing.get(hall_id, [])
    assert item in standing[yard_id]


def test_an_unplaced_on_tick_item_still_fires_after_the_areas():
    """No area owns it, so it has no bucket — it must not silently stop ticking."""
    world = _world()
    _populated(world, {HALL: 1})
    in_room = _ticking_item(world, YARD, "item_in_room")
    orphan = world.graph.get_node("item_orphan")
    if orphan is None:
        orphan = Node(id="item_orphan", type="item", name="orphan", properties={})
        world.graph.add_node(orphan)
    world.graph.add_node(Node(
        id="trig_item_orphan", type="logic_trigger", name="trig_orphan",
    ))
    world.graph.add_edge(Edge(
        source="item_orphan", target="trig_item_orphan", type=EDGE_TRIGGERS,
        properties={"trigger_type": "on_tick"},
    ))

    log = []
    original = _record_ticks(world, log)
    try:
        world.tick_manager.tick_turn(skip_npcs=True)
    finally:
        world.triggers._execute_triggers = original

    fired = [i for i in log if i in (in_room.id, "item_orphan")]
    assert fired == [in_room.id, "item_orphan"], (
        "the room's item runs in area order; the unplaced one follows, id-sorted"
    )


def test_two_identical_worlds_sweep_in_the_same_order():
    """Same graph, same order — including when the graphs were built differently.

    The sweep sorts by node id precisely so that a fixed seed replays: nothing
    about it may depend on the order nodes happened to be added in.
    """
    orders = []
    for reverse in (False, True):
        world = _world()
        _area(world, HALL)
        _area(world, YARD)
        # Same placements both times, added to the graph in opposite orders.
        placement = [(HALL, "det_0_0"), (HALL, "det_0_1"),
                     (YARD, "det_1_0"), (YARD, "det_1_1")]
        for room, item_id in (placement if reverse else placement[::-1]):
            _ticking_item(world, room, item_id)

        log = []
        original = _record_ticks(world, log)
        try:
            world.tick_manager.tick_turn(skip_npcs=True)
        finally:
            world.triggers._execute_triggers = original
        orders.append([i for i in log if i.startswith("det_")])

    assert orders[0] == orders[1] == ["det_0_0", "det_0_1", "det_1_0", "det_1_1"]


# ── the guard: no per-character scan of the roster ────────────────────────


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


def _scan_count_for(world, population):
    world2 = _world()
    _area(world2, HALL)
    _place(world2, "Filler", YARD)
    for i in range(population):
        _place(world2, f"Extra {i}", HALL)

    roster = _CountingRoster(world2.player_manager.players)
    world2.player_manager.players = roster
    world2.tick_manager.tick_turn(skip_npcs=True)
    return roster.scans


def test_tick_turn_does_not_scan_the_roster_per_character():
    """A co-present lookup per character used to mean a roster scan per character.

    The number of wholesale roster passes must not grow with the population:
    that is the difference between O(n) and O(n^2) per tick.
    """
    small = _scan_count_for(_world(), 2)
    large = _scan_count_for(_world(), 30)

    assert large == small, (
        f"roster scans grew from {small} to {large} when the population went "
        "from 3 to 31 characters — something is scanning per character again"
    )
    assert small <= 12, f"a single tick should not need {small} roster passes"
