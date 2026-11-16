"""tools/autoswarm/auditor.py - Automated invariant auditor for ViWo AutoSwarm.

Verifies:
1. Zero em-dashes across all strings (unicode 0x2014 banned).
2. Unique area display names (no ambiguous perception lookups).
3. Complete 5-property environment blocks on all areas.
4. Pass messages on all ways.
5. Key-Lock Solvability: any locked door's key is placed in an area reachable BEFORE that door.
6. Scenario disk persistence and node/edge count matches.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

BANNED_EM_DASH = chr(0x2014)


class ScenarioAuditReport:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.em_dash_violations: List[str] = []

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0 and len(self.em_dash_violations) == 0

    def summary(self) -> str:
        lines = [
            f"Audit Status: {'PASSED' if self.passed else 'FAILED'}",
            f"Errors: {len(self.errors)}",
            f"Em-dash violations: {len(self.em_dash_violations)}",
            f"Warnings: {len(self.warnings)}",
        ]
        if self.em_dash_violations:
            lines.append("Em-dash Violations:")
            for v in self.em_dash_violations:
                lines.append(f"  - {v}")
        if self.errors:
            lines.append("Errors:")
            for e in self.errors:
                lines.append(f"  - {e}")
        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        return "\n".join(lines)


def _scan_for_em_dashes(obj: Any, path: str, violations: List[str]):
    """Recursively search for em-dash characters."""
    if isinstance(obj, str):
        if BANNED_EM_DASH in obj:
            violations.append(f"Found em-dash at '{path}': {obj[:60]}...")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _scan_for_em_dashes(v, f"{path}.{k}", violations)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _scan_for_em_dashes(item, f"{path}[{idx}]", violations)


def audit_scenario(scenario_data: Dict[str, Any], file_path: Optional[Path] = None) -> ScenarioAuditReport:
    """Run full invariant audit against scenario dictionary."""
    report = ScenarioAuditReport()

    # 1. Banned em-dash check
    _scan_for_em_dashes(scenario_data, "scenario", report.em_dash_violations)

    graph = scenario_data.get("graph", {})
    raw_nodes = graph.get("nodes", [])
    if isinstance(raw_nodes, list):
        nodes = {n["id"]: n for n in raw_nodes if "id" in n}
    elif isinstance(raw_nodes, dict):
        nodes = raw_nodes
    else:
        nodes = {}

    edges = graph.get("edges", [])

    # 2. Check Area Nodes & Environments
    area_nodes = [n for n in nodes.values() if n.get("type") == "area"]
    if not area_nodes:
        report.errors.append("No area nodes found in scenario.")

    name_counts: Dict[str, List[str]] = {}
    for area_id, n in nodes.items():
        if n.get("type") != "area":
            continue
        name = (n.get("name") or "").strip().lower()
        if not name:
            report.errors.append(f"Area '{area_id}' has an empty display name.")
        else:
            name_counts.setdefault(name, []).append(area_id)

        # Environment check
        props = n.get("properties", {})
        env = props.get("environment", {})
        for req in ("light", "temperature", "air", "smell", "noise"):
            if req not in env or env[req] is None or env[req] == "":
                report.errors.append(f"Area '{area_id}' missing required environment field '{req}'.")
        if "temperature" in env:
            try:
                float(env["temperature"])
            except (ValueError, TypeError):
                report.errors.append(f"Area '{area_id}' environment.temperature must be numeric float, got '{env['temperature']}'.")

    # Duplicate names check
    for name, ids in name_counts.items():
        if len(ids) > 1:
            report.errors.append(f"Duplicate area display name '{name}' shared by IDs: {ids}.")

    # 3. Check Ways
    ways = {nid: n for nid, n in nodes.items() if n.get("type") == "way"}
    area_ids = set(nodes.keys())

    for way_id, n in ways.items():
        props = n.get("properties", {})
        if not props.get("pass_message"):
            report.errors.append(f"Way '{way_id}' has no pass_message.")
        af = props.get("area_from")
        at = props.get("area_to")
        if not af or af not in area_ids:
            report.errors.append(f"Way '{way_id}' area_from '{af}' does not exist.")
        if not at or at not in area_ids:
            report.errors.append(f"Way '{way_id}' area_to '{at}' does not exist.")

    # 4. Key-Lock Reachability Solver
    locked_ways = {}
    for way_id, n in ways.items():
        props = n.get("properties", {})
        if props.get("locked"):
            req_key = props.get("requires_key") or props.get("key_id")
            if req_key:
                locked_ways[way_id] = {
                    "key_id": req_key,
                    "from": props.get("area_from"),
                    "to": props.get("area_to"),
                }

    if locked_ways:
        # Find player spawn points
        players = scenario_data.get("players", [])
        spawn_areas = set()
        if isinstance(players, list):
            for p in players:
                ca = p.get("current_area")
                if ca:
                    spawn_areas.add(ca)
        elif isinstance(players, dict):
            for p in players.values():
                ca = p.get("current_area")
                if ca:
                    spawn_areas.add(ca)

        if not spawn_areas:
            # Fallback to scenario current_area
            ca = scenario_data.get("current_area")
            if ca:
                spawn_areas.add(ca)

        if spawn_areas:
            # Breadth-first search traversing only UNLOCKED ways
            reachable_unlocked: Set[str] = set(spawn_areas)
            queue = list(spawn_areas)
            while queue:
                curr = queue.pop(0)
                # Find outgoing edges/ways from curr
                for way_id, wn in ways.items():
                    if way_id in locked_ways:
                        continue  # Cannot traverse locked way yet
                    wprops = wn.get("properties", {})
                    af = wprops.get("area_from")
                    at = wprops.get("area_to")
                    dest = None
                    if af == curr:
                        dest = at
                    elif at == curr and not wprops.get("one_way"):
                        dest = af
                    if dest and dest not in reachable_unlocked:
                        reachable_unlocked.add(dest)
                        queue.append(dest)

            # Map where keys are located
            items = {nid: n for nid, n in nodes.items() if n.get("type") == "item"}
            key_locations: Dict[str, Set[str]] = {}
            for item_id, item_node in items.items():
                kid = item_node.get("properties", {}).get("key_id")
                if kid:
                    # Find which area this item is in via edges (source=item_id, type in ("location", "in"))
                    for edge in edges:
                        esrc = edge.get("source") or edge.get("from")
                        etgt = edge.get("target") or edge.get("to")
                        etype = edge.get("type")
                        if esrc == item_id and etype in ("location", "in"):
                            key_locations.setdefault(kid, set()).add(etgt)

            # Verify each locked door has its key in reachable_unlocked
            for way_id, lock_info in locked_ways.items():
                req_k = lock_info["key_id"]
                possible_areas = key_locations.get(req_k, set())
                # Check intersection
                solvable = any(loc in reachable_unlocked for loc in possible_areas)
                if not solvable:
                    report.errors.append(
                        f"Unsolvable lock: Way '{way_id}' requires key '{req_k}', but the key is at {possible_areas}, which is unreachable without opening '{way_id}'."
                    )
                else:
                    report.info.append(f"Lock verified: Way '{way_id}' is solvable (key '{req_k}' is in reachable area).")

    # 5. Disk persistence check
    if file_path:
        if not file_path.exists():
            report.errors.append(f"Persistence error: Scenario file {file_path} does not exist on disk.")
        else:
            try:
                disk_data = json.loads(file_path.read_text(encoding="utf-8"))
                disk_nodes = disk_data.get("graph", {}).get("nodes", [])
                mem_count = len(nodes)
                disk_count = len(disk_nodes)
                if disk_count != mem_count:
                    report.errors.append(
                        f"Persistence desync: Memory has {mem_count} nodes, disk has {disk_count} nodes."
                    )
            except Exception as e:
                report.errors.append(f"Error reading scenario from disk: {e}")

    return report
