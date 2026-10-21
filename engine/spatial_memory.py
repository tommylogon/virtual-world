"""Spatial memory - BFS route discovery from known_areas + real graph.

Replaces the browser-side EntityIndex.buildSpatialContext / buildRoutesFrom.
Reads the real graph directly - no extraction, no junk.
"""

from collections import deque
from typing import Dict, List, Optional, Set

from graph import EDGE_CONNECTION, WorldGraph


class SpatialMemory:
    """BFS route builder seeded from a player's known_areas."""

    def __init__(self, graph: WorldGraph):
        self.graph = graph

    def build_known_routes(
        self,
        current_area: str,
        known_areas: Set[str],
        max_depth: int = 2,
    ) -> str:
        """Return a formatted ``=== KNOWN ROUTES FROM HERE ===`` block.

        Only areas in *known_areas* appear in the results.  Routes are
        built by traversing real graph edges (area → way → area).
        """
        current_id = self._area_id(current_area)
        if not current_id or current_id not in self.graph.nodes:
            return ""

        routes: List[Dict] = []
        visited: Set[str] = set()
        queue: deque = deque()
        queue.append((current_id, [], 0))

        while queue:
            node_id, path, depth = queue.popleft()
            if depth > max_depth:
                continue
            if depth > 0 and node_id != current_id:
                node = self.graph.get_node(node_id)
                area_name = node.name if node else self._id_to_name(node_id)
                if area_name and area_name in known_areas:
                    routes.append({
                        "area": area_name,
                        "path": list(path),
                        "depth": depth,
                    })
            if depth >= max_depth:
                continue
            visited.add(node_id)

            for edge in self.graph.get_edges_for_source(node_id, EDGE_CONNECTION):
                way_id = edge.target
                way_node = self.graph.get_node(way_id)
                if not way_node or way_node.type != "way":
                    continue
                direction = edge.properties.get("direction", "")
                for inner in self.graph.get_edges_for_source(way_id, EDGE_CONNECTION):
                    target_id = inner.target
                    if target_id not in visited:
                        queue.append((target_id, path + [direction], depth + 1))

        if not routes:
            return ""

        lines = ["", "=== KNOWN ROUTES FROM HERE ==="]
        for r in routes[:4]:
            steps = " → ".join(r["path"])
            lines.append(f"{r['area']}: {steps}")
        return "\n".join(lines)

    def find_route(
        self,
        current_area: str,
        target_name: str,
        known_areas: Set[str],
        max_depth: int = 15,
    ) -> Optional[List[Dict[str, str]]]:
        """Find a route from current_area to target_name traversing visited areas (task-882).

        Returns a list of steps [{'direction': dir, 'to': area_name}, ...] or None if unreachable.
        """
        current_id = self._area_id(current_area)
        if not current_id or current_id not in self.graph.nodes:
            return None

        target_norm = target_name.strip().lower()
        if not any(v.lower() == target_norm for v in known_areas):
            return None

        queue: deque = deque()
        queue.append((current_id, []))
        visited: Set[str] = {current_id}

        while queue:
            node_id, path = queue.popleft()
            node = self.graph.get_node(node_id)
            area_name = node.name if node else (self._id_to_name(node_id) or "")
            if len(path) > 0 and (area_name.lower() == target_norm or self._area_id(area_name) == self._area_id(target_name)):
                return path

            if len(path) >= max_depth:
                continue

            for edge in self.graph.get_edges_for_source(node_id, EDGE_CONNECTION):
                way_id = edge.target
                way_node = self.graph.get_node(way_id)
                if not way_node or way_node.type != "way":
                    continue
                direction = edge.properties.get("direction", "")
                for inner in self.graph.get_edges_for_source(way_id, EDGE_CONNECTION):
                    target_id = inner.target
                    if target_id not in visited:
                        t_node = self.graph.get_node(target_id)
                        t_name = t_node.name if t_node else (self._id_to_name(target_id) or "")
                        if t_name in known_areas or t_name.lower() == target_norm or target_id == self._area_id(target_name):
                            visited.add(target_id)
                            step = {"direction": direction or "forward", "to": t_name}
                            queue.append((target_id, path + [step]))

        return None

    # ── helpers ──────────────────────────────────────────────────────────

    def _area_id(self, area_name: str) -> Optional[str]:
        """Convert area name to graph node ID."""
        if not area_name:
            return None
        return f"area_{area_name.lower().replace(' ', '_')}"

    def _id_to_name(self, node_id: str) -> Optional[str]:
        """Convert graph area node ID back to display name."""
        node = self.graph.get_node(node_id)
        if node:
            return node.name
        # Fallback: strip area_ prefix and underscores
        if node_id.startswith("area_"):
            return node_id[5:].replace("_", " ").title()
        return None
