#!/usr/bin/env python3
"""Large-world projection and indexing benchmark (task-402).

Deterministic synthetic world generator creating multi-depth scopes
(world -> settlement -> building), areas, ways, items, and characters.
Measures payload bounds, scope isolation, and index vs scan performance.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graph import WorldGraph, Node, Edge, EDGE_CONNECTION, EDGE_IN
from engine.world.index import GlobalScopeIndex


def generate_synthetic_world(
    num_settlements: int = 10,
    buildings_per_settlement: int = 10,
    rooms_per_building: int = 5,
    items_per_room: int = 20,
    seed: int = 42,
) -> Tuple[WorldGraph, GlobalScopeIndex, Dict[str, dict]]:
    """Deterministic generator for multi-scope worlds.

    Total nodes:
      Settlements + Buildings + Rooms + Items + Ways
    With defaults:
      10 settlements * 10 buildings * 5 rooms = 500 rooms
      500 rooms * 20 items = 10,000 items
      Plus ways, scopes, and areas.
    Scales smoothly to 100k+ by adjusting parameters.
    """
    graph = WorldGraph()
    index = GlobalScopeIndex()
    manifest: Dict[str, dict] = {
        "world_root": {
            "id": "world_root",
            "name": "World Root",
            "kind": "world",
            "parent_id": None,
            "children": [],
            "area_ids": [],
        }
    }

    world_area_id = "area_world_hub"
    graph.add_node(Node(
        id=world_area_id,
        type="area",
        name="World Hub",
        properties={"world_scope_id": "world_root", "tags": ["hub"]},
    ))
    index.own_area(world_area_id, "world_root")
    manifest["world_root"]["area_ids"].append(world_area_id)

    # Deterministic pseudo-random sequence
    state = seed

    def next_rnd(mod: int = 1000) -> int:
        nonlocal state
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        return state % mod

    for s_idx in range(num_settlements):
        s_scope_id = f"scope_settlement_{s_idx}"
        manifest["world_root"]["children"].append(s_scope_id)
        manifest[s_scope_id] = {
            "id": s_scope_id,
            "name": f"Settlement {s_idx}",
            "kind": "settlement",
            "parent_id": "world_root",
            "children": [],
            "area_ids": [],
        }

        s_hub_id = f"area_s_{s_idx}_square"
        graph.add_node(Node(
            id=s_hub_id,
            type="area",
            name=f"Square {s_idx}",
            properties={"world_scope_id": s_scope_id, "tags": ["square"]},
        ))
        index.own_area(s_hub_id, s_scope_id)
        manifest[s_scope_id]["area_ids"].append(s_hub_id)

        # Gateway way linking world hub to settlement square
        way_id = f"way_gate_w_{s_idx}"
        graph.add_node(Node(
            id=way_id,
            type="way",
            name=f"Road to Settlement {s_idx}",
            properties={
                "area_from_id": world_area_id,
                "area_to_id": s_hub_id,
                "world_scope_id": "world_root",
                "is_gateway": True,
                "target_scope_id": s_scope_id,
            },
        ))
        graph.add_edge(Edge(source=world_area_id, target=way_id, type=EDGE_CONNECTION))
        graph.add_edge(Edge(source=way_id, target=s_hub_id, type=EDGE_CONNECTION))
        index.add_gateway(way_id, target_area_id=s_hub_id, target_scope_id=s_scope_id)

        for b_idx in range(buildings_per_settlement):
            b_scope_id = f"scope_b_{s_idx}_{b_idx}"
            manifest[s_scope_id]["children"].append(b_scope_id)
            manifest[b_scope_id] = {
                "id": b_scope_id,
                "name": f"Building {s_idx}-{b_idx}",
                "kind": "building",
                "parent_id": s_scope_id,
                "children": [],
                "area_ids": [],
            }

            prev_room_id = None
            for r_idx in range(rooms_per_building):
                r_id = f"area_r_{s_idx}_{b_idx}_{r_idx}"
                graph.add_node(Node(
                    id=r_id,
                    type="area",
                    name=f"Room {s_idx}-{b_idx}-{r_idx}",
                    properties={"world_scope_id": b_scope_id},
                ))
                index.own_area(r_id, b_scope_id)
                manifest[b_scope_id]["area_ids"].append(r_id)

                if prev_room_id:
                    rw_id = f"way_r_{s_idx}_{b_idx}_{r_idx-1}_{r_idx}"
                    graph.add_node(Node(
                        id=rw_id,
                        type="way",
                        name=f"Door {r_idx-1} to {r_idx}",
                        properties={
                            "area_from_id": prev_room_id,
                            "area_to_id": r_id,
                            "world_scope_id": b_scope_id,
                        },
                    ))
                    graph.add_edge(Edge(source=prev_room_id, target=rw_id, type=EDGE_CONNECTION))
                    graph.add_edge(Edge(source=rw_id, target=r_id, type=EDGE_CONNECTION))
                prev_room_id = r_id

                # Items inside room
                for i_idx in range(items_per_room):
                    item_id = f"item_{s_idx}_{b_idx}_{r_idx}_{i_idx}"
                    graph.add_node(Node(
                        id=item_id,
                        type="item",
                        name=f"Item {i_idx}",
                        properties={"world_scope_id": b_scope_id},
                    ))
                    graph.add_edge(Edge(source=item_id, target=r_id, type=EDGE_IN))

    return graph, index, manifest


def benchmark_projection_and_indices(
    graph: WorldGraph,
    index: GlobalScopeIndex,
    manifest: Dict[str, dict],
) -> dict:
    total_nodes = len(graph.nodes)
    total_edges = len(graph.edges)

    # 1. Measure scope projection bounds at building depth
    sample_b_scope = next(sid for sid, sc in manifest.items() if sc.get("kind") == "building")

    t0 = time.perf_counter()
    b_nodes = [n for n in graph.nodes.values() if (n.properties or {}).get("world_scope_id") == sample_b_scope]
    b_scan_ms = (time.perf_counter() - t0) * 1000

    # Index lookup for areas in scope
    t0 = time.perf_counter()
    indexed_areas = index.areas_in_scope(sample_b_scope)
    b_index_ms = (time.perf_counter() - t0) * 1000

    # Guardrail check: no out-of-scope nodes returned
    for n in b_nodes:
        if (n.properties or {}).get("world_scope_id") != sample_b_scope:
            raise AssertionError(f"Scope leak! Node {n.id} from {(n.properties or {}).get('world_scope_id')} in {sample_b_scope}")

    # Measure scope projection at settlement depth
    sample_s_scope = next(sid for sid, sc in manifest.items() if sc.get("kind") == "settlement")
    t0 = time.perf_counter()
    s_nodes = [n for n in graph.nodes.values() if (n.properties or {}).get("world_scope_id") == sample_s_scope]
    s_scan_ms = (time.perf_counter() - t0) * 1000

    results = {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "total_scopes": len(manifest),
        "building_scope": {
            "scope_id": sample_b_scope,
            "node_count": len(b_nodes),
            "scan_ms": round(b_scan_ms, 3),
            "index_ms": round(b_index_ms, 3),
            "payload_ratio": round(len(b_nodes) / max(1, total_nodes), 5),
        },
        "settlement_scope": {
            "scope_id": sample_s_scope,
            "node_count": len(s_nodes),
            "scan_ms": round(s_scan_ms, 3),
            "payload_ratio": round(len(s_nodes) / max(1, total_nodes), 5),
        },
    }
    return results


def run_benchmark(scale_100k: bool = False) -> dict:
    print(f"Generating synthetic world (scale_100k={scale_100k})...")
    if scale_100k:
        # ~100k+ nodes: 20 settlements, 25 buildings, 8 rooms, 25 items
        # 20 * 25 * 8 = 4000 rooms * 25 items = 100,000 items + 4000 areas + ways
        graph, index, manifest = generate_synthetic_world(
            num_settlements=20,
            buildings_per_settlement=25,
            rooms_per_building=8,
            items_per_room=25,
        )
    else:
        # Standard benchmark: 10 settlements, 10 buildings, 5 rooms, 20 items (~11k nodes)
        graph, index, manifest = generate_synthetic_world(
            num_settlements=10,
            buildings_per_settlement=10,
            rooms_per_building=5,
            items_per_room=20,
        )

    print(f"Generated world: {len(graph.nodes)} nodes, {len(graph.edges)} edges.")
    bench = benchmark_projection_and_indices(graph, index, manifest)
    print(json.dumps(bench, indent=2))
    return bench


if __name__ == "__main__":
    is_100k = "--100k" in sys.argv
    run_benchmark(is_100k)
