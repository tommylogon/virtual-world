#!/usr/bin/env python3
"""Measure production scope persistence and focused snapshot loading on Kraktooth."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from engine.world.store import configure_scope_store


SCENARIO = ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"


def main():
    with SCENARIO.open("r", encoding="utf-8-sig") as stream:
        scenario = json.load(stream)

    with tempfile.TemporaryDirectory(prefix="vw-scope-benchmark-") as data_dir:
        app = create_app({"TESTING": True, "DATA_DIR": data_dir})
        world = app.world
        world.load_from_dict(scenario)
        world._scenario_name = (
            scenario.get("_scenario_name") or scenario.get("name") or SCENARIO.stem)
        store = configure_scope_store(world, data_dir)

        selected = None
        for player_key, player in world.player_manager.players.items():
            node_id = world.player_manager.get_player_node_id(player_key)
            area_id = (world.graph.area_of(node_id)
                       or world.world_index.character_location(node_id))
            scope_id = world.world_index.scope_for_area(area_id) if area_id else None
            if scope_id:
                selected = (player.id, scope_id)
                break
        if selected is None:
            raise RuntimeError("Kraktooth has no located character in an owned scope")

        character_id, selected_scope = selected
        total_areas = sum(
            getattr(node, "type", "") == "area"
            for node in world.graph.nodes.values())
        total_nodes = len(world.graph.nodes)
        total_edges = len(world.graph.edges)
        scope_ids = sorted(world.graph.scope_owners())

        client = app.test_client()
        started = time.perf_counter()
        whole_response = client.get("/api/state")
        whole_state_ms = (time.perf_counter() - started) * 1000
        if whole_response.status_code != 200:
            raise RuntimeError(
                f"Whole-world state returned {whole_response.status_code}")

        started = time.perf_counter()
        for scope_id in scope_ids:
            world.world_index.unload(world.graph, scope_id)
        unload_ms = (time.perf_counter() - started) * 1000
        stored_files = list(store.root.glob("*.json"))
        stored_bytes = sum(path.stat().st_size for path in stored_files)

        started = time.perf_counter()
        response = client.get(
            f"/api/runtime/state?character_id={character_id}")
        reload_ms = (time.perf_counter() - started) * 1000
        if response.status_code != 200:
            raise RuntimeError(
                f"Focused scope reload returned {response.status_code}: "
                f"{response.get_data(as_text=True)}")
        payload = response.get_json()
        graph_data = payload["graph"]

        print(json.dumps({
            "scenario": SCENARIO.name,
            "initial": {
                "areas": total_areas,
                "nodes": total_nodes,
                "edges": total_edges,
                "scopes": len(scope_ids),
                "whole_state_bytes": len(whole_response.data),
                "whole_state_ms": round(whole_state_ms, 2),
            },
            "persistence": {
                "saved_scope_files": len(stored_files),
                "saved_bytes": stored_bytes,
                "unload_all_ms": round(unload_ms, 2),
            },
            "focused_reload": {
                "character_id": character_id,
                "scope_id": selected_scope,
                "http_status": response.status_code,
                "elapsed_ms": round(reload_ms, 2),
                "response_bytes": len(response.data),
                "returned_nodes": len(graph_data["nodes"]),
                "returned_edges": len(graph_data["edges"]),
                "materialized_scopes": sorted(world.graph.scope_owners()),
            },
        }, indent=2))


if __name__ == "__main__":
    main()
