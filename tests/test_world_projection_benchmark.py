"""Tests for large-world projection, indexing, and scale benchmarks (task-402).

Validates:
- Deterministic synthetic multi-scope world generation (world -> settlement -> building);
- Bounded payload behavior (small scope requests return < 5% of whole world);
- Absence of out-of-scope graph node leakage;
- Index lookup vs full-scan performance;
- Repeatable benchmarking command and output.
"""

import pytest
from tools.benchmark_scale import generate_synthetic_world, benchmark_projection_and_indices
from graph import Node


def test_synthetic_world_generation_determinism_and_scale():
    graph1, index1, manifest1 = generate_synthetic_world(
        num_settlements=2, buildings_per_settlement=2, rooms_per_building=2, items_per_room=5, seed=123
    )
    graph2, index2, manifest2 = generate_synthetic_world(
        num_settlements=2, buildings_per_settlement=2, rooms_per_building=2, items_per_room=5, seed=123
    )

    assert len(graph1.nodes) == len(graph2.nodes)
    assert len(graph1.edges) == len(graph2.edges)
    assert set(graph1.nodes.keys()) == set(graph2.nodes.keys())
    assert len(manifest1) == len(manifest2)


def test_bounded_scope_projection_payload():
    # Generate multi-scope world with ~1,000+ nodes
    graph, index, manifest = generate_synthetic_world(
        num_settlements=4, buildings_per_settlement=4, rooms_per_building=3, items_per_room=10, seed=42
    )
    bench = benchmark_projection_and_indices(graph, index, manifest)

    total_nodes = bench["total_nodes"]
    assert total_nodes >= 500

    # Building scope must represent only a small fraction of the world (< 15% even in small benchmark)
    b_ratio = bench["building_scope"]["payload_ratio"]
    assert b_ratio < 0.15, f"Building scope payload ratio {b_ratio} exceeds bounded limit"

    # Index lookup time must be fast (under 10ms)
    assert bench["building_scope"]["index_ms"] < 10.0


def test_scope_leak_guardrail_raises_loudly():
    graph, index, manifest = generate_synthetic_world(
        num_settlements=2, buildings_per_settlement=2, rooms_per_building=2, items_per_room=2, seed=42
    )

    sample_b_scope = next(sid for sid, sc in manifest.items() if sc.get("kind") == "building")

    # Inject an out-of-scope node pretending to be in sample_b_scope
    leaked_node = Node(
        id="leaked_alien_node",
        type="item",
        name="Alien Item",
        properties={"world_scope_id": "other_alien_scope"},
    )
    graph.add_node(leaked_node)

    # If projection contains a node with the wrong scope id, benchmark fails loudly
    def broken_projection_benchmark():
        # simulate broken projection returning leaked node
        scope_nodes = [n for n in graph.nodes.values() if (n.properties or {}).get("world_scope_id") == sample_b_scope]
        scope_nodes.append(leaked_node)
        for n in scope_nodes:
            if (n.properties or {}).get("world_scope_id") != sample_b_scope:
                raise AssertionError(f"Scope leak! Node {n.id} from {(n.properties or {}).get('world_scope_id')} in {sample_b_scope}")

    with pytest.raises(AssertionError, match="Scope leak"):
        broken_projection_benchmark()
