"""Targeted tests for WorldPainter way description and visible-in-direction generator (task-887).

Verifies:
1. Biome narrative phrase pools have >= 3-5 variations per transition.
2. engine/way_narratives produces valid descriptions and directional views.
3. Variation is deterministic and non-uniform across adjacent ways.
4. Compiled grids produce ways with non-empty descriptions and visible_in_direction.
5. TriggerValidator reports zero way_missing_description and zero way_missing_view_direction.
"""

from __future__ import annotations

import json
import os
import pytest

from engine import way_narratives, world_grid as wg
from engine.trigger_validator import TriggerValidator
from engine.world_compile import compile_grid
from graph import EDGE_CONNECTION, WorldGraph


def test_narrative_pools_structure_and_counts():
    """Verify narrative pools json has >= 3-5 variations per major transition."""
    data = way_narratives.load_narratives()
    assert "kinds" in data
    assert "transitions" in data

    # Check structural kinds
    for kind in ("door", "stairs", "entrance"):
        assert kind in data["kinds"], f"Missing kind pool for {kind}"
        pool = data["kinds"][kind]
        assert len(pool.get("descriptions", [])) >= 3, f"Kind {kind} descriptions < 3"
        assert len(pool.get("forward_views", [])) >= 3, f"Kind {kind} forward_views < 3"
        assert len(pool.get("reverse_views", [])) >= 3, f"Kind {kind} reverse_views < 3"

    # Check key major biome transitions
    required_transitions = [
        "road:road", "road:woods", "road:water", "road:rock",
        "woods:woods", "woods:water", "woods:rock", "woods:open",
        "rock:rock", "rock:water", "rock:open",
        "water:water", "water:open",
        "cultivated:cultivated", "cultivated:open",
        "urban:urban", "urban:open", "urban:woods",
        "open:open", "default",
        "dense_forest:dense_forest", "dense_forest:river",
        "sparse_forest:hills", "cliff:dungeon", "ruin:woods",
    ]
    for key in required_transitions:
        assert key in data["transitions"], f"Missing transition pool for {key}"
        pool = data["transitions"][key]
        assert len(pool.get("descriptions", [])) >= 3, f"Transition {key} descriptions < 3"
        assert len(pool.get("forward_views", [])) >= 3, f"Transition {key} forward_views < 3"
        assert len(pool.get("reverse_views", [])) >= 3, f"Transition {key} reverse_views < 3"


def test_get_way_narrative_structural_kinds():
    """Door and stairs ways receive structural descriptions and view cues."""
    desc_door, view_a_door, view_b_door = way_narratives.get_way_narrative(
        biome_from=None, biome_to=None, kind="door",
        direction="north", seed="seed42", scope_id="test_scope", way_id="way_door_1",
    )
    assert "door" in desc_door.lower() or "entrance" in desc_door.lower()
    assert len(view_a_door) > 0
    assert len(view_b_door) > 0

    desc_stairs, view_a_stairs, view_b_stairs = way_narratives.get_way_narrative(
        biome_from=None, biome_to=None, kind="stairs",
        direction="up", seed="seed42", scope_id="test_scope", way_id="way_stairs_1",
    )
    assert any(w in desc_stairs.lower() for w in ("stair", "step", "stairway", "flight"))
    assert len(view_a_stairs) > 0
    assert len(view_b_stairs) > 0


def test_get_way_narrative_biome_transitions():
    """Biome transitions generate perspective-correct views for either direction."""
    # Forest to water transition
    desc, view_woods_to_water, view_water_to_woods = way_narratives.get_way_narrative(
        biome_from="dense_forest", biome_to="river", kind="open",
        direction="east", seed="seed100", scope_id="s1", way_id="w_fw",
    )
    assert len(desc) > 10
    # From woods towards water: should mention water / river
    assert any(w in view_woods_to_water.lower() for w in ("water", "river", "current", "shore", "bank"))
    # From water towards woods: should mention woods / forest / trees / trunks
    assert any(w in view_water_to_woods.lower() for w in ("wood", "forest", "tree", "bough", "canopy", "trunk", "timber"))

    # Reverse direction query produces perspective-correct view assignments
    desc_rev, view_rev_a, view_rev_b = way_narratives.get_way_narrative(
        biome_from="river", biome_to="dense_forest", kind="open",
        direction="west", seed="seed100", scope_id="s1", way_id="w_fw",
    )
    assert any(w in view_rev_a.lower() for w in ("wood", "forest", "tree", "bough", "canopy", "trunk", "timber"))
    assert any(w in view_rev_b.lower() for w in ("water", "river", "current", "shore", "bank"))


def test_way_narratives_determinism_and_variation():
    """Same seed and ids produce identical text; different ways produce variation."""
    # Determinism
    r1 = way_narratives.get_way_narrative("dense_forest", "dense_forest", kind="open",
                                          direction="north", seed="seedA", scope_id="s", way_id="w1")
    r2 = way_narratives.get_way_narrative("dense_forest", "dense_forest", kind="open",
                                          direction="north", seed="seedA", scope_id="s", way_id="w1")
    assert r1 == r2

    # Variation across multiple different ways in the same biome
    descriptions = set()
    views_a = set()
    for i in range(10):
        d, va, vb = way_narratives.get_way_narrative(
            "dense_forest", "dense_forest", kind="open",
            direction="north", seed="seedA", scope_id="s", way_id=f"way_tile_{i}",
        )
        descriptions.add(d)
        views_a.add(va)

    assert len(descriptions) >= 3, f"Expected varied descriptions, got {len(descriptions)}"
    assert len(views_a) >= 3, f"Expected varied views, got {len(views_a)}"


def test_compiled_grid_ways_carry_descriptions_and_views():
    """compile_grid assigns description to ways and visible_in_direction to edges."""
    scope_id = "wild"
    manifest = {
        "root": {"id": "root", "name": "Root", "children": [scope_id]},
        scope_id: {"id": scope_id, "name": "Wild"},
    }
    wg.ensure_grid(manifest[scope_id], 3, 3, mode="world")
    for x in range(3):
        wg.paint(manifest[scope_id], "biome", x, 0, "dense_forest")
        wg.paint(manifest[scope_id], "biome", x, 1, "river")
    wg.paint(manifest[scope_id], "road", 1, 0, "dirt_road")
    wg.paint(manifest[scope_id], "road", 1, 1, "dirt_road")

    patch = compile_grid(manifest, scope_id, seed="test_seed_123")

    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) > 0, "Compiler should have minted ways"

    g = WorldGraph()
    for n in patch.nodes:
        g.add_node(n)
    for e in patch.edges:
        g.add_edge(e)

    # Verify every way node has a non-empty description
    for w in ways:
        props = w.properties or {}
        desc = str(props.get("description") or "").strip()
        assert len(desc) > 0, f"Way {w.id} is missing description"
        assert len(str(props.get("pass_message") or "").strip()) > 0, f"Way {w.id} is missing pass_message"

    # Verify every incoming connection edge to a way has visible_in_direction and cardinal
    incoming_edges = [e for e in patch.edges if e.type == EDGE_CONNECTION and any(w.id == e.target for w in ways)]
    assert len(incoming_edges) > 0

    for e in incoming_edges:
        eprops = e.properties or {}
        vid = str(eprops.get("visible_in_direction") or "").strip()
        cardinal = str(eprops.get("cardinal") or "").strip()
        assert len(vid) > 0, f"Edge {e.source} -> {e.target} has empty visible_in_direction"
        assert len(cardinal) > 0, f"Edge {e.source} -> {e.target} has empty cardinal"

    # Run TriggerValidator and assert zero way description/direction issues
    validator = TriggerValidator(g)
    issues = validator.validate()
    way_issues = [i for i in issues if i.get("code") in ("way_missing_description", "way_missing_view_direction")]
    assert len(way_issues) == 0, f"Expected 0 way description/view issues, got {len(way_issues)}: {way_issues}"


def test_generated_interior_ways_carry_indoor_narratives():
    """Interiors compiled from templates carry indoor doorways, stairs, and doors."""
    from engine import interior_gen

    scope_id = "cottage_interior"
    manifest = {
        "root": {"id": "root", "name": "Root", "children": [scope_id]},
        scope_id: {"id": scope_id, "name": "Cottage Interior", "biome": "cottage"},
    }
    wg.ensure_grid(manifest[scope_id], 5, 5, mode="interior")
    interior_gen.generate_interior(manifest, scope_id, "cottage")
    patch = compile_grid(manifest, scope_id, seed="interior_seed_77")

    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) > 0, "Interior should have compiled ways"

    g = WorldGraph()
    for n in patch.nodes:
        g.add_node(n)
    for e in patch.edges:
        g.add_edge(e)

    for w in ways:
        props = w.properties or {}
        desc = str(props.get("description") or "").strip()
        assert len(desc) > 0, f"Interior way {w.id} missing description"
        # Ensure indoor ways do not talk about outdoor cobblestone streets or wagon tracks
        assert "cobblestone lane" not in desc.lower()
        assert "wagon track" not in desc.lower()

    # Incoming edges check
    for e in patch.edges:
        if e.type == EDGE_CONNECTION and any(w.id == e.target for w in ways):
            vid = str((e.properties or {}).get("visible_in_direction") or "").strip()
            assert len(vid) > 0
            assert "cobblestone street" not in vid.lower()

    # Validator check
    validator = TriggerValidator(g)
    issues = validator.validate()
    way_issues = [i for i in issues if i.get("code") in ("way_missing_description", "way_missing_view_direction")]
    assert len(way_issues) == 0

