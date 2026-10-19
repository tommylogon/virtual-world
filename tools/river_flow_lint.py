"""river_flow_lint.py - validate hydrological gradient and flow consistency (task-745).

Inspects contiguous river runs across grid scopes to verify physical plausibility:
1. Uphill flow: water current flowing uphill without pressure.
2. Unclassified cataracts: drops >= 4 storeys (>=12m) missing waterfall/cataract classification.
3. Dead-end outflows: inland river channels terminating without a sink, basin, or map edge.

Usage:
    python tools/river_flow_lint.py --check
    python tools/river_flow_lint.py --report [path/to/scenario.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import world_grid  # noqa: E402


DEFAULT_SCENARIO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "scenarios", "kraktooth_goblin_camp.json",
)


def lint_grid_river_flow(record: dict, scope_id: str = "grid") -> List[dict]:
    """Inspect all water cells in a scope record and return detected problems."""
    problems: List[dict] = []
    layers = record.get("layers") or {}
    biomes_layer = layers.get("biome") or {}
    grid = record.get("grid") or {}
    w = int(grid.get("w") or 0)
    h = int(grid.get("h") or 0)

    # Collect all water cells
    water_cells = set()
    for key in biomes_layer.keys():
        try:
            xs, ys = key.split(",")
            x, y = int(xs), int(ys)
        except (ValueError, TypeError):
            continue
        if world_grid.is_water_cell(record, x, y):
            water_cells.add((x, y))

    if not water_cells:
        return problems

    for x, y in sorted(water_cells):
        z0 = world_grid.cell_elevation(record, x, y)
        b_id = world_grid.cell_biome(record, x, y) or ""
        curr = world_grid.derive_water_current(record, x, y)
        if not curr:
            continue

        # 1. Check for manual current layer uphill flow
        if curr.get("manual_override"):
            dir_idx = curr.get("direction", 0)
            dx, dy = world_grid.COMPASS_8_OFFSETS[dir_idx]
            nx, ny = x + dx, y + dy
            if (nx, ny) in water_cells:
                nz = world_grid.cell_elevation(record, nx, ny)
                if nz > z0:
                    problems.append({
                        "scope": scope_id,
                        "x": x,
                        "y": y,
                        "type": "uphill_flow",
                        "message": (
                            f"water at ({x}, {y}) elevation {z0} has manual current "
                            f"pointing uphill to ({nx}, {ny}) elevation {nz}"
                        ),
                    })

        # 2. Check for unclassified sheer cataract (drop >= 4 storeys without waterfall tag/biome)
        drop = curr.get("drop", 0)
        if drop >= 4:
            is_cataract = "waterfall" in b_id.lower() or "cataract" in b_id.lower()
            if not is_cataract:
                problems.append({
                    "scope": scope_id,
                    "x": x,
                    "y": y,
                    "type": "unclassified_cataract",
                    "message": (
                        f"steep drop of {drop} storeys ({drop * 3}m) from ({x}, {y}) "
                        f"to downstream reach lacks waterfall classification (biome '{b_id}')"
                    ),
                })

        # 3. Check for inland dead ends (river cell with no reachable downstream outflow or basin/boundary)
        is_basin = any(term in b_id.lower() for term in ("lake", "ocean", "sea", "deep_water"))
        is_boundary = (x <= 0 or x >= w - 1 or y <= 0 or y >= h - 1)
        if not is_basin and not is_boundary:
            queue = [(x, y)]
            visited = {(x, y)}
            reaches_outflow = False
            while queue and not reaches_outflow:
                cx, cy = queue.pop(0)
                cz = world_grid.cell_elevation(record, cx, cy)
                cb_id = str(world_grid.cell_biome(record, cx, cy) or "").lower()
                c_basin = any(term in cb_id for term in ("lake", "ocean", "sea", "deep_water"))
                c_boundary = (cx <= 0 or cx >= w - 1 or cy <= 0 or cy >= h - 1)
                if (cx, cy) != (x, y) and cz < z0:
                    reaches_outflow = True
                    break
                if c_basin or c_boundary:
                    reaches_outflow = True
                    break
                for dx, dy in world_grid.COMPASS_8_OFFSETS:
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) in water_cells and (nx, ny) not in visited:
                        nz = world_grid.cell_elevation(record, nx, ny)
                        if nz <= cz:
                            visited.add((nx, ny))
                            queue.append((nx, ny))
            if not reaches_outflow:
                problems.append({
                    "scope": scope_id,
                    "x": x,
                    "y": y,
                    "type": "dead_end_outflow",
                    "message": (
                        f"river channel at ({x}, {y}) elevation {z0} dead-ends inland "
                        f"without an outflow sink, lake basin, or map edge"
                    ),
                })

    return problems


def lint_scenario(scenario_path: str) -> Dict[str, List[dict]]:
    """Lint river runs in all grid-bearing scopes within a scenario file."""
    if not os.path.exists(scenario_path):
        return {}
    with open(scenario_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    manifest = data.get("world_scopes") or {}
    results: Dict[str, List[dict]] = {}
    for scope_id, scope_rec in manifest.items():
        if isinstance(scope_rec, dict) and scope_rec.get("layers"):
            probs = lint_grid_river_flow(scope_rec, scope_id)
            if probs:
                results[scope_id] = probs
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", nargs="?", default=DEFAULT_SCENARIO,
                        help="path to scenario JSON file")
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if physical hydrology problems are found")
    parser.add_argument("--report", action="store_true",
                        help="print detailed river flow linting report")
    args = parser.parse_args()

    results = lint_scenario(args.scenario)
    total_problems = sum(len(p) for p in results.values())

    if args.report or not args.check:
        print(f"Hydrology Lint Report: {args.scenario}")
        print(f"Total problems found: {total_problems}")
        for scope_id, problems in sorted(results.items()):
            print(f"\n--- Scope: {scope_id} ({len(problems)} issues) ---")
            for p in problems:
                print(f"  [{p['type']}] ({p['x']},{p['y']}): {p['message']}")

    if args.check and total_problems > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
