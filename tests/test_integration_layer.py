"""Integration layer: the seams between systems (task-572).

The unit suite is strong; these cover the places where two subsystems meet and
neither one's tests look:

1. **Save/load with two same-named areas in different scopes.** The graph keys
   on id, so two areas may share a display name; the save layer's `areas`
   projection is still name-keyed (task-439), so the test asserts the graph is
   the source of truth and documents the projection's known collapse.
2. **Same-seed trace equality.** The tick path draws from the process-global
   `random` in ~19 places; run with a seeded RNG, two identical runs must be
   identical, and two different seeds must diverge.
3. **Compiled-region generation benchmark.** A deterministic compile with a
   published node/edge count, so a change that doubles the graph or breaks
   seed determinism is visible.

These need a world, not Flask: they exercise the engine seam directly.
"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node  # noqa: E402
from engine import generation, world_compile, world_grid as wg, world_scopes  # noqa: E402
from conftest import new_world  # noqa: E402


# ── 1. save/load round-trip: same name, different scopes ────────────────────


def _two_hollows():
    """A world with two areas both called 'Hollow' in different scopes."""
    world = new_world()
    manifest = world_scopes.normalise_manifest({
        "town": {"id": "town", "name": "Town"},
        "crypt": {"id": "crypt", "name": "Crypt"},
    })
    world.world_scopes = manifest
    for area_id, scope_id in (("area_town_hollow", "town"),
                              ("area_crypt_hollow", "crypt")):
        world.graph.add_node(Node(id=area_id, type="area", name="Hollow",
                                  properties={"world_scope_id": scope_id}))
        world_scopes.assign_area_membership(world.world_scopes, area_id, scope_id, None)
    return world


def test_two_same_named_areas_survive_a_save_load_round_trip():
    world = _two_hollows()
    data = world.to_dict()

    reloaded = new_world()
    reloaded.load_from_dict(data)

    hollows = [n for n in reloaded.graph.nodes.values()
               if n.type == "area" and n.name == "Hollow"]
    assert len(hollows) == 2, "a display name is not an identity: both must survive"
    assert {n.id for n in hollows} == {"area_town_hollow", "area_crypt_hollow"}
    assert {n.properties.get("world_scope_id") for n in hollows} == {"town", "crypt"}
    assert set(reloaded.world_scopes) >= {"town", "crypt"}

    # The scope membership cache survives too, so scope projection sees both.
    assert "area_town_hollow" in world_scopes.area_ids_in_scope(
        reloaded.world_scopes, reloaded.graph, "town")
    assert "area_crypt_hollow" in world_scopes.area_ids_in_scope(
        reloaded.world_scopes, reloaded.graph, "crypt")


def test_the_areas_projection_is_name_keyed_and_collapses_the_pair():
    """The documented task-439 defect, pinned so a fix updates this test rather
    than silently changing behaviour: `to_dict()["areas"]` keys by display name,
    so the pair collapses to one entry even though the graph keeps both. A save
    reloaded from the *graph* (which is what load_from_dict prefers) is correct;
    any consumer of the projection is not."""
    world = _two_hollows()
    data = world.to_dict()
    projected = data.get("areas") or {}
    assert sum(1 for key in projected if key == "Hollow") == 1
    # The graph, which is authoritative, still has both.
    graph_areas = [n for n in data["graph"]["nodes"].values()
                   if n.get("type") == "area" and n.get("name") == "Hollow"]
    assert len(graph_areas) == 2


# ── 2. same-seed trace equality ────────────────────────────────────────────


def _trace(seed, ticks=20):
    """Seed the process RNG, opt the rat's tree in, run, return a fingerprint."""
    random.seed(seed)
    world = new_world()
    rat = world.player_manager.players["rat"]
    rat.autonomy = True  # opt in: its behaviour tree is what draws from `random`

    rows = []
    for _ in range(ticks):
        world.tick_turn()
        rows.append((
            world.time_ticks,
            tuple((p.name, p.current_area) for p in
                  sorted(world.player_manager.players.values(), key=lambda p: p.name)),
            tuple((p.name, tuple(sorted(p.vitals.items()))) for p in
                  sorted(world.player_manager.players.values(), key=lambda p: p.name)),
        ))
    return rows, tuple(world.game_log)


def test_the_same_seed_replays_the_same_trace():
    first_positions, first_log = _trace(1234)
    second_positions, second_log = _trace(1234)
    assert first_positions == second_positions, "same seed, different positions/vitals"
    assert first_log == second_log, "same seed, different game log"


def test_different_seeds_diverge():
    """Proves the trace actually covers RNG-driven state: if this failed, the
    equality test above would be vacuous."""
    one, _ = _trace(1)
    two, _ = _trace(2)
    assert one != two


# ── 3. compiled-region generation benchmark (task-402) ─────────────────────


def _big_manifest(size=9, biome="sparse_forest"):
    manifest = {"root": {"id": "root", "name": "Root", "children": ["wild"]},
                "wild": {"id": "wild", "name": "Wild"}}
    wg.ensure_grid(manifest["wild"], size, size, mode="world")
    for x in range(size):
        for y in range(size):
            wg.paint(manifest["wild"], "biome", x, y, biome)
    return manifest


def test_a_compiled_region_has_a_published_and_deterministic_shape():
    size = 9
    expected_areas = size * size
    # Orthogonal (2*size*(size-1)) + diagonal (2*(size-1)**2) adjacencies.
    expected_ways = 2 * (size - 1) * (2 * size - 1)

    start = time.perf_counter()
    patch = world_compile.compile_grid(_big_manifest(size), "wild", seed="benchmark")
    elapsed = time.perf_counter() - start

    areas = [n for n in patch.nodes if n.type == "area"]
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(areas) == expected_areas
    assert len(ways) == expected_ways
    assert len(patch.edges) == len(ways) * 4
    # Published in the failure message and printed, per task-402's "publish the
    # fixture counts"; no arbitrary latency target is asserted.
    print(f"\nbenchmark: {size}x{size} -> {len(areas)} areas, {len(ways)} ways, "
          f"{len(patch.edges)} edges in {elapsed:.3f}s")

    # Same seed recompiles identically (the determinism task-402 depends on).
    again = world_compile.compile_grid(_big_manifest(size), "wild", seed="benchmark")
    assert [n.id for n in again.nodes] == [n.id for n in patch.nodes]
    assert [n.id for n in again.nodes if n.type == "way"] == \
           [n.id for n in patch.nodes if n.type == "way"]
