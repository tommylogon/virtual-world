"""Biome resource/hostile distribution consumers (tasks 569/570)."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import world_compile, world_grid as wg
from engine.population import LibraryIndex
from engine.world import spawner
from graph import EDGE_IN, Node

SCOPE = "wild"


def _index():
    # Every tag the real sparse_forest distribution uses, so whichever weighted
    # entry is picked resolves (the spawner never substitutes a partial match).
    return LibraryIndex({
        "wild_berries": {"name": "Wild Berries", "tags": ["berry", "fruit"]},
        "healing_herb": {"name": "Healing Herb", "tags": ["herb", "medicinal"]},
        "edible_root": {"name": "Edible Root", "tags": ["root", "food"]},
        "old_sock": {"name": "Old Sock", "tags": ["junk", "scrap"]},
    })


def _area(area_id, biome):
    return Node(id=area_id, type="area", name=area_id,
                properties={"biome": biome})


def _distribution():
    return {
        "sparse_forest": [
            {"tags": ["berry", "fruit"], "weight": 1},
            {"tags": ["herb", "medicinal"], "weight": 1},
        ],
    }


# ── resources (task-569) ────────────────────────────────────────────────


def test_spawn_resources_places_a_resolved_item_with_provenance():
    nodes, edges, unresolved = spawner.spawn_resources(
        [_area("area_forest", "sparse_forest")], _index(),
        scope_id=SCOPE, seed="s", per_area=1,
        distribution=_distribution(), rng=random.Random(1))

    assert unresolved == {}
    assert len(nodes) == 1 and nodes[0].type == "item"
    assert nodes[0].properties["generated"]["scope_id"] == SCOPE
    # Placed in the area by a normal `in` edge.
    assert any(e.type == EDGE_IN and e.target == "area_forest" for e in edges)


def test_same_seed_yields_the_same_spawn():
    first = spawner.spawn_resources(
        [_area("area_forest", "sparse_forest")], _index(),
        scope_id=SCOPE, seed="s", per_area=2,
        distribution=_distribution(), rng=random.Random(7))
    second = spawner.spawn_resources(
        [_area("area_forest", "sparse_forest")], _index(),
        scope_id=SCOPE, seed="s", per_area=2,
        distribution=_distribution(), rng=random.Random(7))
    assert [n.id for n in first[0]] == [n.id for n in second[0]]


def test_a_tag_that_resolves_to_nothing_is_reported_not_substituted():
    nodes, edges, unresolved = spawner.spawn_resources(
        [_area("area_forest", "sparse_forest")], _index(),
        scope_id=SCOPE, seed="s", per_area=1,
        distribution={"sparse_forest": [{"tags": ["phlogiston"], "weight": 1}]},
        rng=random.Random(1))

    assert nodes == [] and edges == []
    assert unresolved == {"phlogiston": 1}


def test_a_pooled_resource_keeps_its_pool_shape():
    index = LibraryIndex({
        "berry_bush": {"name": "Berry Bush", "tags": ["berry", "fruit"],
                       "quantity": 5, "harvest": {"item": "wild_berries", "size": 1}},
    })
    nodes, _edges, _unresolved = spawner.spawn_resources(
        [_area("area_forest", "sparse_forest")], index,
        scope_id=SCOPE, seed="s", per_area=1,
        distribution={"sparse_forest": [{"tags": ["berry", "fruit"], "weight": 1}]},
        rng=random.Random(0))

    pool = nodes[0]
    assert pool.properties["quantity"] == 5
    assert pool.properties["harvest"]["item"] == "wild_berries"


def test_an_area_without_a_biome_places_nothing():
    nodes, _edges, unresolved = spawner.spawn_resources(
        [Node(id="area_x", type="area", name="X", properties={})], _index(),
        scope_id=SCOPE, seed="s", distribution=_distribution())
    assert nodes == [] and unresolved == {}


def test_compile_grid_invokes_the_spawner_and_reports_tags():
    manifest = {"root": {"id": "root", "name": "Root", "children": [SCOPE]},
                SCOPE: {"id": SCOPE, "name": "Wild"}}
    wg.ensure_grid(manifest[SCOPE], 1, 1, mode="world")
    wg.paint(manifest[SCOPE], "biome", 0, 0, "sparse_forest")

    patch = world_compile.compile_grid(manifest, SCOPE, spawn_index=_index())

    assert isinstance(patch.report.unresolved_tags, dict)
    spawned = [n for n in patch.nodes if n.type == "item"]
    assert spawned, "a biome with resources must place at least one item"
    assert all(n.properties["generated"]["scope_id"] == SCOPE for n in spawned)
    assert patch.report.to_dict()["unresolved_tags"] == \
        {k: v for k, v in patch.report.unresolved_tags.items()}


def test_compile_without_an_index_places_no_items():
    manifest = {"root": {"id": "root", "name": "Root", "children": [SCOPE]},
                SCOPE: {"id": SCOPE, "name": "Wild"}}
    wg.ensure_grid(manifest[SCOPE], 1, 1, mode="world")
    wg.paint(manifest[SCOPE], "biome", 0, 0, "sparse_forest")
    patch = world_compile.compile_grid(manifest, SCOPE)
    assert not [n for n in patch.nodes if n.type == "item"]
    assert patch.report.unresolved_tags == {}


# ── hostiles (task-570) ─────────────────────────────────────────────────


def test_hostile_chance_rises_with_distance_and_caps():
    entries = [{"kind": "bandit", "base_chance": 0.1,
                "per_area_from_settlement": 0.1, "max_chance": 0.25}]
    assert spawner.hostile_chance("sparse_forest", 0, entries)["bandit"] == 0.1
    assert spawner.hostile_chance("sparse_forest", 1, entries)["bandit"] == 0.2
    # Capped, not unbounded.
    assert spawner.hostile_chance("sparse_forest", 100, entries)["bandit"] == 0.25


def test_roll_hostiles_is_deterministic_and_chance_gated():
    entries = [{"kind": "monster", "base_chance": 1.0,
                "per_area_from_settlement": 0, "max_chance": 1.0},
               {"kind": "bandit", "base_chance": 0.0,
                "per_area_from_settlement": 0, "max_chance": 0.0}]
    assert spawner.roll_hostiles("dense_forest", 0, random.Random(0), entries) == ["monster"]


def test_hostile_character_node_is_tagged_and_stamped():
    node = spawner.hostile_character_node("predator", "npc_wild_1",
                                          scope_id=SCOPE, seed="s")
    assert node.type == "character"
    assert {"predator", "hostile"} <= set(node.properties["tags"])
    assert node.properties["generated"]["scope_id"] == SCOPE


# ── library-backed loot tables (task-718) ────────────────────────────────


def test_spawn_resources_reads_from_library_when_bundled_key_is_gone():
    import tempfile, json, os
    from engine import biomes as bio

    with tempfile.TemporaryDirectory() as tmp:
        lib_dir = os.path.join(tmp, "resource_distribution")
        os.makedirs(lib_dir)
        with open(os.path.join(lib_dir, "test_basin.json"), "w", encoding="utf-8") as f:
            json.dump({
                "id": "test_basin",
                "name": "Test Basin",
                "biome_tags": ["test_basin"],
                "location_tags": [],
                "item_tags": ["berry", "fruit"],
                "weight": 2,
                "conditions": {},
            }, f)

        old_resource_dir = bio._resource_dir
        bio._resource_dir = lib_dir
        try:
            old_cache = bio._cache.copy()
            bio._cache.clear()
            try:
                dist = bio.resource_distribution()
                assert "test_basin" in dist
                assert dist["test_basin"] == [{"tags": ["berry", "fruit"], "weight": 2}]
                nodes, edges, unresolved = spawner.spawn_resources(
                    [_area("area_basin", "test_basin")], _index(),
                    scope_id=SCOPE, seed="s", per_area=1,
                    distribution=dist, rng=random.Random(1))
                assert len(nodes) == 1
                assert unresolved == {}
            finally:
                bio._cache = old_cache
        finally:
            bio._resource_dir = old_resource_dir
