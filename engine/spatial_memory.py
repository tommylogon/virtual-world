"""Spatial memory - BFS route discovery from known_areas + real graph.

Replaces the browser-side EntityIndex.buildSpatialContext / buildRoutesFrom.
Reads the real graph directly - no extraction, no junk.

@module spatial_memory
@contributes SpatialMemory, known_route_areas
@docs docs/virtualWorld/Gameplay/Per-Agent Knowledge (Fog of War).md
"""

from collections import deque
from typing import Any, Dict, List, Optional, Set

from engine.fog import only_known, resolve_known_area
from graph import EDGE_CONNECTION, WorldGraph


def known_route_areas(player, graph) -> Set[str]:
    """Area names a character may route through.

    The union of what the character has observed (``visited_area_names``) and
    any **area** in the authored/known registry. ``player.known`` also holds way
    and item ids for the perception gate, so only entries that resolve to an area
    node count as a place; an entry that resolves to nothing is a known thing,
    not a known destination, and must not widen the route search.

    This is the bridge task-467 needs: authored ``known``/``known_areas`` becomes
    route knowledge without a second store. ``visited_area_names`` stays the
    source for what was walked.
    """
    names: Set[str] = set()
    visited = getattr(player, "visited_area_names", None)
    if callable(visited):
        try:
            names.update(visited(graph) or ())
        except TypeError:
            names.update(visited() or ())

    for entry in only_known(player, getattr(player, "known", []) or []):
        node = resolve_known_area(graph, entry)
        if node is not None and getattr(node, "name", None):
            names.add(str(node.name))

    for entry in (getattr(player, "known_areas", None) or ()):
        node = resolve_known_area(graph, entry)
        if node is not None and getattr(node, "name", None):
            names.add(str(node.name))
        elif entry:
            names.add(str(entry))
    return names


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
        built by traversing real graph edges (area -> way -> area).
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
            steps = " \u2192 ".join(r["path"])
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

    def build_cognitive_map(self, player) -> Dict[str, Any]:
        """Project the character's belief-based cognitive map (task-736).
        Returns only the areas and ways that this character knows/remembers,
        derived from spatial memory, not the full world graph.
        """
        known_areas = set(known_route_areas(player, self.graph))
        current_area = getattr(player, "current_area", None)
        if current_area:
            known_areas.add(current_area)

        area_nodes = []
        known_area_ids = set()
        for aname in sorted(known_areas):
            aid = self._area_id(aname)
            if aid and aid in self.graph.nodes:
                known_area_ids.add(aid)
                visited_fn = getattr(player, "visited_area_names", None)
                is_visited = False
                if callable(visited_fn):
                    try:
                        is_visited = aname in (visited_fn(self.graph) or ())
                    except TypeError:
                        is_visited = aname in (visited_fn() or ())
                area_nodes.append({
                    "id": aid,
                    "name": aname,
                    "is_current": (aname == current_area or aid == current_area),
                    "visited": is_visited,
                })

        ways = []
        known_aspects = getattr(player, "known_way_aspects", None) or {}
        seen_ways = set()

        for aid in known_area_ids:
            aname = self._id_to_name(aid) or ""
            for edge in self.graph.get_edges_for_source(aid, EDGE_CONNECTION):
                wid = edge.target
                wnode = self.graph.get_node(wid)
                if not wnode or wnode.type != "way":
                    continue
                dir_label = edge.properties.get("direction", "")
                for inner in self.graph.get_edges_for_source(wid, EDGE_CONNECTION):
                    tid = inner.target
                    if tid in known_area_ids and tid != aid:
                        way_key = tuple(sorted([aid, tid]))
                        if way_key not in seen_ways:
                            seen_ways.add(way_key)
                            aspects = list(known_aspects.get((aname, dir_label), ()))
                            ways.append({
                                "id": wid,
                                "from_id": aid,
                                "to_id": tid,
                                "from_name": aname,
                                "to_name": self._id_to_name(tid) or "",
                                "direction": dir_label,
                                "aspects": aspects,
                            })

        return {
            "character": getattr(player, "name", ""),
            "current_area": current_area,
            "areas": area_nodes,
            "ways": ways,
            "known_area_count": len(area_nodes),
            "known_way_count": len(ways),
        }

    def recall_route(self, player, target_name: str) -> Optional[List[Dict[str, str]]]:
        """Recall a known route to target_name within the character's known cognitive map."""
        known_areas = set(known_route_areas(player, self.graph))
        current_area = getattr(player, "current_area", None)
        if not current_area or not target_name:
            return None
        return self.find_route(current_area, target_name, known_areas)

    # ── helpers ──────────────────────────────────────────────────────────

    def _area_id(self, area_name: str) -> Optional[str]:
        """Convert area name or id to graph node ID."""
        if not area_name:
            return None
        resolved = resolve_known_area(self.graph, area_name)
        if resolved is not None and getattr(resolved, "id", None):
            return str(resolved.id)
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
