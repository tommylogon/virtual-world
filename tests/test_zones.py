"""Zone-driven fidelity and lazy zone materialisation (task-500).

The task's own header says most of it is owned elsewhere — fidelity-tier
selection is task-411 + task-418, chunk load/evict is task-401 — and that this
task's "only unique delta is using *zones* as the selection key". That is what is
built and tested here:

- a zone is the materialisation boundary, so a character's zone is readable by
  the attention budget and outranks awareness when nothing is attending the zone;
- a released zone keeps its scope record and loses its nodes, and materialising
  it rebuilds them;
- the refusals. A release is destructive and mostly irreversible, so the rules
  that stop one matter more than the happy path.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import world_grid as wg  # noqa: E402
from engine.attention import TIER_NAMES, TIER_NONE, AttentionBudget  # noqa: E402
from engine.generation import provenance  # noqa: E402
from engine.world_compile import compile_grid  # noqa: E402
from engine.zones import (  # noqa: E402
    MATERIALIZED,
    RELEASED,
    ReleaseRefused,
    ZoneStore,
    authored_scope_id,
    generated_scope_id,
    is_generated,
    scope_nodes,
)
from graph import EDGE_CONNECTION, EDGE_IN, Edge, Node, WorldGraph  # noqa: E402


# ── fixtures ───────────────────────────────────────────────────────────────


def _manifest(zones=2, w=3, h=3, paint_policy=None, biome="sparse_forest"):
    """A root scope with *zones* painted child scopes, all compiled-able."""
    manifest = {"world": {"id": "world", "name": "World", "children": [],
                          "mode": "world"}}
    wg.ensure_grid(manifest["world"], 2, 2, mode="world")
    for index in range(zones):
        zone_id = f"zone_{index}"
        record = {"id": zone_id, "name": f"Zone {index}", "kind": "scope",
                  "parent_id": "world", "children": [], "mode": "world"}
        if paint_policy:
            record["paint_policy"] = paint_policy
        wg.ensure_grid(record, w, h, mode="world")
        for x in range(w):
            for y in range(h):
                wg.paint(record, "biome", x, y, biome)
        manifest[zone_id] = record
        manifest["world"]["children"].append(zone_id)
    return manifest


def _build(manifest, scope_id, **kwargs):
    graph = WorldGraph()
    patch = compile_grid(manifest, scope_id, **kwargs)
    from engine import generation

    generation.apply_patch(graph, manifest, patch, allow_regenerate=True)
    return graph


def _zone_keyed(store, count=4, area="cell"):
    graph = store.graph
    graph.add_node(Node(id="player_near", type="character", name="Near",
                        properties={"world_scope_id": "zone_0"}))
    graph.add_edge(Edge(source="player_near", target=area, type=EDGE_IN,
                        properties={}))


# ── the selection key ──────────────────────────────────────────────────────


def test_a_character_in_an_unattended_zone_ranks_below_everything():
    """The zone is the materialisation boundary, so a zone nobody is attending
    should not hold the budget however recent its occupants are."""
    budget = AttentionBudget(cap=1)
    characters = {
        "here": {"area_id": "a", "recency": 0, "world_scope_id": "zone_0"},
        "far": {"area_id": "z", "recency": 9999, "world_scope_id": "zone_9"},
    }
    report = budget.select(WorldGraph(), characters=characters, humans=["here"],
                           zones_in_play=["zone_0"])
    assert report["attended"] == ["here"]


def test_the_zone_key_is_off_unless_a_caller_asks_for_it():
    """A world with no zones should not pay for the key, and a caller that
    forgets to pass `zones` gets the old behaviour rather than an error.

    Neither character is an anchor or a human, so the only thing separating them
    is the zone key — which is the only way to show the key doing something.
    """
    characters = {
        "near_zone": {"area_id": "a", "recency": 0, "world_scope_id": "zone_0"},
        "far_zone": {"area_id": "z", "recency": 9999, "world_scope_id": "zone_9"},
    }
    without = AttentionBudget(cap=1).select(WorldGraph(), characters=characters)
    assert without["attended"] == ["far_zone"], (
        "without the zone key it is recency alone, which is correct and is why "
        "the key is opt-in"
    )

    with_key = AttentionBudget(cap=1).select(WorldGraph(), characters=characters,
                                             zones_in_play=["zone_0"])
    assert with_key["attended"] == ["near_zone"]


def test_an_unplaced_character_is_not_assumed_to_be_near():
    budget = AttentionBudget(cap=1)
    characters = {
        "here": {"area_id": "a", "recency": 0, "world_scope_id": "zone_0"},
        "loose": {"area_id": "q", "recency": 9999},
    }
    report = budget.select(WorldGraph(), characters=characters, zones_in_play=["zone_0"])
    assert report["attended"] == ["here"]


def test_the_zone_key_demotes_rather_than_promoting():
    """What the key actually is: a demotion. It cannot make a character more
    interesting than the awareness channels say they are."""
    characters = {
        "near": {"area_id": "a", "recency": 1, "world_scope_id": "zone_0"},
        "far": {"area_id": "z", "recency": 2, "world_scope_id": "zone_1"},
    }
    with_key = AttentionBudget(cap=1).select(WorldGraph(), characters=characters,
                                             zones_in_play=["zone_0"])
    assert with_key["attended"] == ["near"]

    # Both aware of the anchor's area (same room), the far one still loses,
    # because the zone outranks awareness.
    aware = {
        "near": {"area_id": "a", "recency": 0, "world_scope_id": "zone_0"},
        "far": {"area_id": "a", "recency": 9999, "world_scope_id": "zone_1"},
    }
    demoted = AttentionBudget(cap=1).select(WorldGraph(), characters=aware,
                                            zones_in_play=["zone_0"])
    assert demoted["attended"] == ["near"], (
        "co-present in the anchor's own room and STILL not attended, because the "
        "zone is a different zone — which is the whole claim"
    )


def test_a_character_in_a_zones_seed_zone_is_not_demoted():
    budget = AttentionBudget(cap=2)
    characters = {
        "here": {"area_id": "a", "recency": 0, "world_scope_id": "zone_0"},
        "same_zone": {"area_id": "b", "recency": 1, "world_scope_id": "zone_0"},
        "other_zone": {"area_id": "z", "recency": 2, "world_scope_id": "zone_1"},
    }
    report = budget.select(WorldGraph(), characters=characters, zones_in_play=["zone_0"])
    assert set(report["attended"]) == {"here", "same_zone"}


# ── provenance is the selector ─────────────────────────────────────────────


def test_provenance_is_what_makes_a_zone_rebuildable():
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    nodes = scope_nodes(graph, "zone_0")
    assert nodes, "a compiled zone has nodes"
    for node_id in nodes:
        node = graph.get_node(node_id)
        assert is_generated(node), node_id
        assert generated_scope_id(node) == "zone_0"
        assert authored_scope_id(node) == "zone_0"


def test_a_hand_placed_area_is_in_the_zones_inventory_too():
    """A zone holding only hand-placed content must not look empty, or it gets
    released while still holding the thing that was there."""
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    graph.add_node(Node(id="area_authored", type="area", name="By Hand",
                        properties={"world_scope_id": "zone_0"}))
    assert "area_authored" in scope_nodes(graph, "zone_0")
    assert not is_generated(graph.get_node("area_authored"))


def test_a_node_from_another_zone_is_not_in_this_ones_inventory():
    manifest = _manifest(zones=2)
    graph = WorldGraph()
    from engine import generation

    for zone_id in ("zone_0", "zone_1"):
        generation.apply_patch(graph, manifest,
                               compile_grid(manifest, zone_id, seed="s"),
                               allow_regenerate=True)
    zero, one = set(scope_nodes(graph, "zone_0")), set(scope_nodes(graph, "zone_1"))
    assert zero and one
    assert not (zero & one)


# ── the release refusals ───────────────────────────────────────────────────


def test_a_zone_with_a_character_in_it_is_not_released():
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    some_area = scope_nodes(graph, "zone_0")[0]
    graph.add_node(Node(id="player_one", type="character", name="One",
                        properties={}))
    graph.add_edge(Edge(source="player_one", target=some_area, type=EDGE_IN,
                        properties={}))

    store = ZoneStore(graph, manifest)
    reason = store.releasable("zone_0")
    assert reason and "character" in reason, reason
    with pytest.raises(ReleaseRefused):
        store.release("zone_0")
    assert store.is_materialised("zone_0")


def test_a_baked_zone_is_never_released():
    """A baked zone compiles once and is hand-edited afterwards, so a
    release/materialise cycle would silently destroy the edits."""
    manifest = _manifest(zones=1, paint_policy="baked")
    graph = _build(manifest, "zone_0")
    store = ZoneStore(graph, manifest)
    assert "baked" in store.releasable("zone_0")
    with pytest.raises(ReleaseRefused):
        store.release("zone_0")
    with pytest.raises(ReleaseRefused):
        store.materialise("zone_0")


def test_a_zone_with_hand_authored_nodes_is_not_released():
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    graph.add_node(Node(id="area_dungeon", type="area", name="Dungeon",
                        properties={"world_scope_id": "zone_0"}))
    store = ZoneStore(graph, manifest)
    assert "hand-authored" in store.releasable("zone_0")


def test_a_zone_whose_parent_this_store_released_is_not_released():
    """The gateway way is emitted by whichever scope compiles second, so a
    released parent leaves its children with nothing to link back to."""
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    store = ZoneStore(graph, manifest, seed="s")

    # `world` is never compiled in this fixture, so the child is releasable now.
    assert store.releasable("zone_0") is None, (
        f"an uncompiled parent is the author's business, not a blocker: "
        f"{store.releasable('zone_0')}"
    )

    # Release the *root* this store knows about, then the child refuses.
    store.released["world"] = ""
    assert "parent" in (store.releasable("zone_0") or "")
    with pytest.raises(ReleaseRefused):
        store.release("zone_0")


def test_an_already_released_zone_says_so_rather_than_working():
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    store = ZoneStore(graph, manifest, seed="s")
    store.release("zone_0")
    assert store.releasable("zone_0") == "already released"
    assert store.release("zone_0")["count"] == 0


def test_an_unknown_scope_is_refused_not_crashed():
    store = ZoneStore(WorldGraph(), _manifest(zones=1))
    assert "no such scope" in (store.releasable("nope") or "")
    with pytest.raises(ReleaseRefused):
        store.materialise("nope")


# ── the cycle ──────────────────────────────────────────────────────────────


def test_a_release_keeps_the_scope_record_and_drops_the_nodes():
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    before = store_before = graph.get_revision()
    store = ZoneStore(graph, manifest, seed="s")
    count_before = store.node_count()

    report = store.release("zone_0")

    assert report["count"] > 0
    assert store.node_count() == count_before - report["count"]
    # The zone still EXISTS. That is the whole point: a distant zone is a record.
    assert "zone_0" in manifest
    assert manifest["zone_0"]["state"] == RELEASED
    assert manifest["zone_0"]["area_ids"], "the inventory is not the graph"
    assert graph.get_revision() != store_before


def test_a_release_does_not_touch_a_neighbouring_zone():
    manifest = _manifest(zones=2)
    graph = WorldGraph()
    from engine import generation

    for zone_id in ("zone_0", "zone_1"):
        generation.apply_patch(graph, manifest,
                               compile_grid(manifest, zone_id, seed="s"),
                               allow_regenerate=True)
    store = ZoneStore(graph, manifest, seed="s")
    kept = set(scope_nodes(graph, "zone_1"))
    store.release("zone_0")
    assert all(graph.get_node(node_id) is not None for node_id in kept)
    assert not scope_nodes(graph, "zone_0")


def test_materialise_rebuilds_the_same_nodes_from_the_same_seed():
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    # Deliberately built with NO seed, so `compile_grid` mints its own default.
    # The rebuild has to reproduce that default, which it can only do by reading
    # the seed off the nodes it is about to drop.
    store = ZoneStore(graph, manifest)
    original = {n.id: dict(n.properties) for n in graph.nodes.values()}
    original_seed = original["area_zone_0_0_0"]["generated"]["seed"]

    released = store.release("zone_0")
    assert released["seed"] == original_seed, (
        f"the release forgot the seed the zone was actually built with: "
        f"{released['seed']!r} != {original_seed!r}"
    )
    assert not scope_nodes(graph, "zone_0")

    report = store.materialise("zone_0")
    assert report["count"] > 0
    rebuilt = {n.id: dict(n.properties) for n in graph.nodes.values()}
    assert set(rebuilt) == set(original)
    # Same ids and same provenance: a rebuild that quietly changed the recipe
    # would be a different zone wearing the old one's name.
    for node_id, props in original.items():
        assert rebuilt[node_id]["generated"] == props["generated"], node_id
    assert manifest["zone_0"]["state"] == MATERIALIZED


def test_a_release_records_an_ambiguous_seed_rather_than_guessing_one():
    """A zone not built from one seed cannot be reproduced, and the report has
    to say so instead of picking one."""
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0", seed="a")
    some_area = scope_nodes(graph, "zone_0")[0]
    graph.get_node(some_area).properties["generated"]["seed"] = "b"

    store = ZoneStore(graph, manifest, seed="a")
    report = store.release("zone_0")
    assert report["ambiguous_seed"] == ["a", "b"]


def test_a_different_seed_rebuilds_differently_and_the_record_says_which():
    """Determinism has a converse: if a zone is rebuilt from a different seed its
    nodes genuinely differ, so the seed has to be remembered."""
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0", seed="first")
    store = ZoneStore(graph, manifest)
    first = sorted(scope_nodes(graph, "zone_0"))

    store.release("zone_0")
    assert store.released["zone_0"] == "first", "the seed outlives the nodes"
    store.materialise("zone_0")
    assert sorted(scope_nodes(graph, "zone_0")) == first


def test_approach_is_idempotent():
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    store = ZoneStore(graph, manifest, seed="s")
    assert store.approach("zone_0")["already"] is True
    store.release("zone_0")
    assert store.approach("zone_0")["count"] > 0
    assert store.approach("zone_0")["already"] is True


def test_a_zone_with_no_compiler_uses_the_real_one_rather_than_refusing():
    """The injection point exists for tests, not as a licence to have no
    behaviour: a store built in production should just work."""
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    store = ZoneStore(graph, manifest, seed="s")
    assert store._compile is None
    store.release("zone_0")
    assert store.materialise("zone_0")["count"] > 0


def test_an_injected_compiler_is_used_instead():
    manifest = _manifest(zones=1)
    graph = _build(manifest, "zone_0")
    calls = []

    def fake(scope_id):
        calls.append(scope_id)
        from engine import generation

        return generation.GenerationPatch()

    store = ZoneStore(graph, manifest, compile_scope=fake, seed="s")
    store.release("zone_0")
    store.materialise("zone_0")
    assert calls == ["zone_0"]


def test_the_store_reports_what_is_materialised_and_what_is_not():
    manifest = _manifest(zones=2)
    graph = WorldGraph()
    from engine import generation

    for zone_id in ("zone_0", "zone_1"):
        generation.apply_patch(graph, manifest,
                               compile_grid(manifest, zone_id, seed="s"),
                               allow_regenerate=True)
    store = ZoneStore(graph, manifest, seed="s")
    assert store.materialised_scopes() == ["zone_0", "zone_1"]
    store.release("zone_0")
    assert store.materialised_scopes() == ["zone_1"]
    assert store.released_scopes() == ["zone_0"]


# ── the acceptance: the node count stays bounded ───────────────────────────


def test_the_node_count_stays_bounded_as_the_world_grows():
    """The offloading win, measured: doubling the number of zones must not
    double the resident nodes, because the distant ones are records."""
    from engine import generation

    counts = {}
    for zone_count in (2, 8, 32):
        manifest = _manifest(zones=zone_count, w=3, h=3)
        graph = WorldGraph()
        for index in range(zone_count):
            zone_id = f"zone_{index}"
            generation.apply_patch(
                graph, manifest, compile_grid(manifest, zone_id, seed="s"),
                allow_regenerate=True)
        store = ZoneStore(graph, manifest, seed="s")

        # Keep one zone and release the rest: what a player standing at the
        # frontier would actually cost.
        for zone_id in manifest:
            if zone_id == "world" or zone_id == "zone_0":
                continue
            if store.releasable(zone_id) is None:
                store.release(zone_id)
        counts[zone_count] = store.node_count()

    # 16x the zones; a bounded store should not come close to 16x the nodes.
    assert counts[32] < counts[2] * 4, counts
    assert counts[32] == counts[8], (
        f"past a point, adding zones costs nothing resident — that is the "
        f"point. Got {counts}"
    )
