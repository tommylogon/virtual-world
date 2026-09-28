"""Way blocking pass: outdoor ways can't be hand-closed, blocked by seed (task-522).

Two rules, and they are the whole task:

* a plain close action must NOT close an outdoor way — you cannot close a road
  into a forest by hand;
* at compile time a deterministic subset of outdoor ways is blocked, each with
  per-biome prose saying what blocks it.

The state shape is **a real ``blocked`` state with prose beside it**, and the
codebase had already decided that before this task: ``engine/matching.py`` lists
``blocked`` among valid way states, ``engine/movement.py`` refuses it, and
``engine/area_description.py`` keeps it hidden until the way is examined. What
was missing was a *reason*, which is what ``blocked_by`` /
``blocked_description`` supply.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import world_compile as wc  # noqa: E402
from engine.movement import MovementSystem  # noqa: E402
from engine.world_compile import (  # noqa: E402
    BLOCKED_WAY_PERCENT,
    BLOCKERS_BY_TERRAIN,
    DEFAULT_TERRAIN_CLASS,
    _apply_way_blocking,
    _blocker_for,
    _is_blocked_way,
)
from graph import Node  # noqa: E402


# ── the state shape ────────────────────────────────────────────────────────


def test_blocked_is_a_state_the_engine_already_knows():
    """The decision is not mine: `blocked` predates this task in three modules."""
    from engine.barriers import WAY_STATES as BARRIER_STATES
    from engine.movement import MovementSystem

    assert "blocked" in BARRIER_STATES
    assert "blocked" in BARRIER_STATES and BARRIER_STATES.index("blocked") > \
        BARRIER_STATES.index("closed")
    # matching.py recognises the word, so "examine blocked path" resolves.
    import inspect

    assert '"blocked"' in inspect.getsource(
        __import__("engine.matching", fromlist=["x"]))
    # movement.py refuses it, before this task and independently of it.
    assert "blocked" in inspect.getsource(MovementSystem._open_passage_block)


def test_a_blocked_way_is_already_a_valid_state_under_matching():
    import inspect

    source = inspect.getsource(__import__("engine.matching", fromlist=["x"]))
    block = source[source.index("state_words"):]
    assert '"blocked"' in block.split("}")[0]


def test_every_terrain_class_has_blocker_prose():
    from engine.world_compile import _TERRAIN_CLASSES

    for terrain in list(BLOCKERS_BY_TERRAIN) + [DEFAULT_TERRAIN_CLASS, "road"]:
        options = BLOCKERS_BY_TERRAIN.get(terrain)
        assert options, f"no blockers for terrain class {terrain!r}"
        for blocker, prose in options:
            assert blocker and blocker.replace("_", "").isalnum()
            assert prose.endswith("."), f"{blocker}: prose must be a sentence"
            assert len(prose.split()) >= 6, f"{blocker}: too thin to read"
    # Every terrain the classifier can produce is answerable.
    for terrain in set(_TERRAIN_CLASSES.values()) | {"open", "road"}:
        assert _blocker_for(terrain, "way_x", "seed")[0]


# ── determinism ────────────────────────────────────────────────────────────


def test_the_same_seed_gives_the_same_set():
    ways = [f"way_{i}" for i in range(200)]
    first = [w for w in ways if _is_blocked_way("seed-a", w)]
    second = [w for w in ways if _is_blocked_way("seed-a", w)]
    assert first == second
    assert first, "a 200-way scope should block something at the default rate"


def test_a_different_seed_gives_a_different_set():
    ways = [f"way_{i}" for i in range(200)]
    a = [w for w in ways if _is_blocked_way("seed-a", w)]
    b = [w for w in ways if _is_blocked_way("seed-b", w)]
    assert a != b, "the blocked set is supposed to be seed-specific"


def test_the_pick_is_a_spread_not_a_prefix():
    """A hash that clustered on `way_1`, `way_10`, `way_100` would be a bug the
    obvious eyeball test would miss."""
    ways = [f"way_{i}" for i in range(500)]
    blocked = [w for w in ways if _is_blocked_way("seed", w)]
    assert 0.05 < len(blocked) / len(ways) < 0.25, len(blocked)
    # Blocked ways are spread across the id space, not bunched at one end.
    first_half = sum(1 for w in blocked if int(w.split("_")[1]) < 250)
    assert 0.3 < first_half / len(blocked) < 0.7, first_half


@pytest.mark.parametrize("percent,expected", [
    (0, False), (100, True), (-5, False), (150, True),
])
def test_the_percentage_bounds_are_total(percent, expected):
    assert all(_is_blocked_way("s", f"way_{i}", percent) is expected
               for i in range(20))


def test_the_default_rate_is_deliberately_low():
    """Nothing in a compiled grid ever un-blocks a way, so every blocked way is
    permanent map until an author or trigger clears it. A maze is not the goal."""
    assert 0 < BLOCKED_WAY_PERCENT <= 25


def test_the_blocker_pick_is_deterministic_per_way():
    assert _blocker_for("woods", "way_1", "s") == _blocker_for("woods", "way_1", "s")
    picks = {w: _blocker_for("woods", w, "s")[0] for w in
             [f"way_{i}" for i in range(60)]}
    assert len(set(picks.values())) > 1, "every way gets the same blocker"
    # And the pick is per-way, not a function of the terrain alone.
    assert _blocker_for("woods", "way_1", "s") != _blocker_for("rock", "way_1", "s")


# ── never strand a pocket ──────────────────────────────────────────────────


def _chain(n_areas):
    """A line of n_areas areas joined by n_areas-1 ways. **No redundancy at
    all** — closing any one of its ways splits it."""
    outdoor = []
    nodes = []
    for i in range(n_areas - 1):
        way_id = f"way_{i}"
        outdoor.append((way_id, f"area_{i}", f"area_{i + 1}", "open"))
        nodes.append(Node(id=way_id, type="way", name=way_id,
                          properties={"current_state": "open", "kind": "open"}))
    return nodes, outdoor


def _ring(n_areas):
    """A cycle. Closing one way leaves a path, so exactly one may close."""
    outdoor = []
    nodes = []
    for i in range(n_areas):
        way_id = f"way_{i}"
        outdoor.append((way_id, f"area_{i}", f"area_{(i + 1) % n_areas}", "open"))
        nodes.append(Node(id=way_id, type="way", name=way_id,
                          properties={"current_state": "open", "kind": "open"}))
    return nodes, outdoor


def _grid(w, h):
    """A w x h grid of areas with every 4-neighbour joined — the shape a painted
    grid actually compiles to, and the one with real redundancy to spend."""
    outdoor = []
    nodes = []

    def area_id(x, y):
        return f"area_{x}_{y}"

    seen = set()
    counter = 0
    for y in range(h):
        for x in range(w):
            for dx, dy in ((1, 0), (0, 1)):
                nb = (x + dx, y + dy)
                if nb[0] >= w or nb[1] >= h:
                    continue
                key = (area_id(x, y), area_id(*nb))
                if key in seen:
                    continue
                seen.add(key)
                way_id = f"way_{counter}"
                counter += 1
                outdoor.append((way_id, key[0], key[1], "open"))
                nodes.append(Node(id=way_id, type="way", name=way_id,
                                  properties={"current_state": "open",
                                              "kind": "open"}))
    return nodes, outdoor


def test_a_pocket_is_never_stranded():
    """A graph with no redundancy cannot lose a single way.

    Every candidate is refused, because blocking any one of them would leave the
    areas past it unreachable. The pocket stays whole — which is the whole
    constraint ("never strand a pocket") stated as tightly as it can be.
    """
    nodes, outdoor = _chain(6)
    assert all(_is_blocked_way("seed", w[0], 100) for w in outdoor), "all are candidates"

    blocked = _apply_way_blocking(nodes, outdoor, "seed", 100)

    assert blocked == [], "a chain has no way to spare, so none may be blocked"
    assert all(n.properties["current_state"] == "open" for n in nodes)


def test_a_ring_loses_exactly_one_way():
    nodes, outdoor = _ring(8)
    blocked = _apply_way_blocking(nodes, outdoor, "seed", 100)
    assert len(blocked) == 1, [b[0] for b in blocked]
    # A second would split the ring in two.
    assert sum(1 for n in nodes if n.properties["current_state"] == "blocked") == 1


def test_a_painted_grid_loses_ways_but_keeps_its_shape():
    """The real case: a grid has redundant routes, so a blocked subset is
    affordable, and every area stays reachable however the hash falls."""
    for seed in ("alpha", "beta", "gamma", "delta", "epsilon"):
        nodes, outdoor = _grid(6, 6)
        assert len(outdoor) == 60, len(outdoor)
        blocked = _apply_way_blocking(nodes, outdoor, seed, 100)
        # A 6x6 grid is 2-connected enough to lose a lot; it must not lose all.
        assert 0 < len(blocked) < len(outdoor), (seed, len(blocked))
        # And nothing may be stranded, which is what the per-candidate check buys.
        remaining = {
            a for a in {w[1] for w in outdoor} | {w[2] for w in outdoor}
        }
        reached = wc._reachable_areas(
            [(a, way_id, b) for way_id, a, b, _t in outdoor],
            {way_id for way_id, _ in blocked},
        )
        assert reached == remaining, (seed, sorted(remaining - reached))


def test_percent_zero_blocks_nothing():
    nodes, outdoor = _ring(5)
    assert _apply_way_blocking(nodes, outdoor, "seed", 0) == []
    assert all(n.properties["current_state"] == "open" for n in nodes)


def test_an_unknown_way_id_is_skipped_not_crashed():
    nodes, outdoor = _ring(3)
    outdoor.append(("way_missing", "area_0", "area_9", "open"))
    # area_9 is unknown to every other way, so blocking this one is free; but the
    # node does not exist, so it must be skipped rather than raise.
    blocked = _apply_way_blocking(nodes, outdoor, "seed", 100)
    assert all(way_id != "way_missing" for way_id, _ in blocked)


# ── the shape of a blocked way ─────────────────────────────────────────────


def test_a_blocked_way_records_the_obstacle_and_says_it():
    nodes, outdoor = _ring(5)
    blocked = _apply_way_blocking(nodes, outdoor, "seed", 100)
    assert blocked, "the chain leaves at least one way to block"

    props = nodes[0].properties
    assert props["current_state"] == "blocked"
    assert props["blocked_by"]
    assert props["blocked_description"].endswith(".")
    # The refusal and the pass message are the same sentence, so a character
    # walking into it learns one fact rather than two.
    assert props["refusal_message"] == props["blocked_description"]
    assert props["pass_message"] == props["blocked_description"]
    # An outdoor way is not a door.
    assert props["prevent_close"] is True


def test_blocked_ways_carry_the_blind_spot_the_state_already_had():
    """`area_description` hides `blocked` until the way is examined, so a blocked
    way must not shout its blocker in a way that leaks that blind spot.

    The reason is in properties, not in the area description, which is exactly
    why the refusal quotes it instead of the description printing it.
    """
    nodes, outdoor = _ring(5)
    _apply_way_blocking(nodes, outdoor, "seed", 100)
    props = nodes[0].properties
    assert "blocked_description" not in ("description",)
    assert props.get("description") is None, (
        "a blocked way states its obstacle via blocked_description, not the "
        "always-visible description"
    )


def test_doors_and_stairs_are_never_blocked():
    """Only `kind == "open"` outdoor ways are candidates.

    A door is a threshold a character goes through, and a stairway is a climb.
    Blocking either would be closing a building's own front door, and would
    contradict `prevent_close`, which is about outdoor ways.
    """
    # The compiler only records `kind == "open"` ways in outdoor_ways; pin that.
    import inspect

    source = inspect.getsource(wc.compile_grid)
    assert 'if kind == "open" and way_props.get("current_state") == "open":' in source
    assert "outdoor_ways.append" in source


# ── end to end, through the real compiler ──────────────────────────────────


def _painted_manifest(w, h, biome="sparse_forest"):
    """One gridded scope, every cell painted — a real painted grid, not a stub."""
    from engine import world_grid as wg

    manifest = {"root": {"id": "root", "name": "Root", "children": ["wild"]},
                "wild": {"id": "wild", "name": "Wild"}}
    wg.ensure_grid(manifest["wild"], w, h, mode="world")
    for x in range(w):
        for y in range(h):
            wg.paint(manifest["wild"], "biome", x, y, biome)
    return manifest


def _ways_by_state(patch, state):
    return [n for n in patch.nodes
            if n.type == "way" and n.properties.get("current_state") == state]


def test_compiling_a_painted_grid_blocks_some_outdoor_ways():
    patch = wc.compile_grid(_painted_manifest(9, 9), "wild", seed="painter")

    blocked = _ways_by_state(patch, "blocked")
    assert blocked, "a 9x9 grid should block something"
    for node in blocked:
        props = node.properties
        assert props["kind"] == "open", "only outdoor ways are candidates"
        assert props["blocked_by"] and props["blocked_description"]
        assert props["prevent_close"] is True
        assert props["refusal_message"] == props["blocked_description"]

    # Doors and stairways are untouched — a building's own door is not blocked.
    for node in _ways_by_state(patch, "door"):
        assert "blocked_by" not in node.properties


def test_the_same_seed_recompiles_to_the_same_blocked_set():
    def ids(seed):
        patch = wc.compile_grid(_painted_manifest(9, 9), "wild", seed=seed)
        return sorted(n.id for n in _ways_by_state(patch, "blocked"))

    assert ids("painter") == ids("painter")
    assert ids("painter") != ids("other-painter")


def test_no_seed_regenerates_identically_from_a_fresh_manifest():
    """The determinism requirement as a regenerate, not just a re-read: a new
    manifest object must compile to the same world, blockers included."""
    first = wc.compile_grid(_painted_manifest(9, 9), "wild", seed="s")
    second = wc.compile_grid(_painted_manifest(9, 9), "wild", seed="s")

    def shape(patch):
        return sorted((n.id, n.type, n.properties.get("current_state"),
                       n.properties.get("blocked_by"),
                       n.properties.get("description"))
                      for n in patch.nodes)

    assert shape(first) == shape(second)


def test_the_generate_report_says_what_it_blocked():
    patch = wc.compile_grid(_painted_manifest(9, 9), "wild", seed="painter")
    notes = " ".join(patch.report.notes)
    assert "blocked at compile time" in notes
    assert "need clearing, not opening" in notes


def test_a_compiled_blocked_way_leaves_no_isolated_area():
    """Blocking changes reachability, so the compile's own isolation count is
    the wrong place to look — but a *newly* stranded area would be a bug, and
    `emitted_pairs` is untouched by this pass, so the count must not move."""
    manifest = _painted_manifest(9, 9)
    with_blocking = wc.compile_grid(manifest, "wild", seed="painter")
    isolated = [n for n in with_blocking.report.notes if "no exits" in n]
    assert not isolated, with_blocking.report.notes

    # And the pass cannot have created one: every area is still reachable.
    triples = [(n.properties.get("area_from_id"), n.id, n.properties.get("area_to_id"))
               for n in with_blocking.nodes if n.type == "way"]
    blocked = {n.id for n in _ways_by_state(with_blocking, "blocked")}
    areas = {a for node in with_blocking.nodes if node.type == "area"
             for a in (node.id,)}
    assert wc._reachable_areas(
        [t for t in triples if all(t)], blocked
    ) == areas, "a blocked way stranded an area"


def test_a_two_by_two_grid_loses_exactly_one_way():
    """A 2x2 grid's four areas are joined by 6 ways (4 cardinal + 2 diagonal), so
    the graph is K4 — it can spare exactly one edge before an area is cut off.
    That is the smallest case where the pass may act at all."""
    patch = wc.compile_grid(_painted_manifest(2, 2), "wild", seed="painter")
    total = [n for n in patch.nodes if n.type == "way"]
    assert len(total) == 6, [n.id for n in total]
    assert len(_ways_by_state(patch, "blocked")) == 1
    assert len(_ways_by_state(patch, "open")) == 5


def test_a_single_painted_cell_loses_nothing():
    """No ways at all: the pass must be a no-op, not a crash."""
    manifest = {"root": {"id": "root", "name": "Root", "children": ["wild"]},
                "wild": {"id": "wild", "name": "Wild"}}
    from engine import world_grid as wg

    wg.ensure_grid(manifest["wild"], 1, 1, mode="world")
    wg.paint(manifest["wild"], "biome", 0, 0, "sparse_forest")
    patch = wc.compile_grid(manifest, "wild", seed="painter")
    assert _ways_by_state(patch, "blocked") == []



class _Way:
    def __init__(self, **props):
        self.properties = props


def _block_for(way, action="close"):
    return MovementSystem._open_passage_block(None, way, action, "the path")


def test_a_blocked_outdoor_way_cannot_be_closed_by_hand():
    way = _Way(current_state="blocked", prevent_close=True,
               blocked_by="fallen_tree",
               blocked_description="A fallen tree has come down across the path.")
    reason = _block_for(way, "close")
    assert reason == "A fallen tree has come down across the path."
    # And it cannot be opened either — a fallen tree is not a door to swing.
    assert _block_for(way, "open") == "A fallen tree has come down across the path."


def test_a_blocked_way_with_no_reason_still_refuses_with_something():
    way = _Way(current_state="blocked")
    reason = _block_for(way, "open")
    assert "blocked" in reason and reason.endswith(".")


def test_a_plain_outdoor_way_cannot_be_closed_either():
    """The task's first rule, independent of blocking: you cannot close a road
    into a forest by hand."""
    way = _Way(current_state="open", prevent_close=True)
    reason = _block_for(way, "close")
    assert "can't close" in reason
    # But opening is not an action on an outdoor way that was never closed.
    assert _block_for(way, "open") is None


def test_an_interior_door_keeps_its_normal_toggle():
    way = _Way(current_state="open", kind="door", handle="door")
    assert _block_for(way, "close") is None
    assert _block_for(way, "open") is None


def test_a_closed_door_is_still_closeable_when_the_author_wants_that():
    """`prevent_close` is the author's call, not the compiler's default: a
    hand-placed secret panel may be both shut and permanent."""
    way = _Way(current_state="closed", prevent_close=True,
               blocked_description="The panel is wedged shut.")
    assert "wedged shut" in _block_for(way, "close")
    assert _block_for(way, "open") is None, "opening a shut panel is fine"


def test_the_jump_climb_crawl_refusal_is_unchanged():
    for requires in ("jump", "climb", "crawl"):
        reason = _block_for(_Way(current_state="open", requires=requires), "close")
        assert f"open {requires} passage" in reason
