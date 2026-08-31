"""Proximity detection for items with a ``proximity_effect`` config (task-10).

An item that declares::

  "proximity_effect": {
      "max_areas": 3,
      "detects": ["character", "item"],   # character | item | way
      "tags": ["haunted"]                  # optional item/way tag filter
  }

reports a narrative reading on examine/use: how far the nearest matching
presence is (same room = sharp, adjacent = jumping needle, farther = faint
blip). Room distance = BFS over area→way→area connections. No numbers are
emitted — the reading is prose only.
"""

from collections import deque


def _area_neighbors(graph, area_id):
    """Areas directly reachable from *area_id* via way connections.

    Edges run area → way → area, so the way is the TARGET of both.
    """
    neighbors = []
    for edge in graph.get_edges_for_source(area_id, "connection"):
        way_id = edge.target
        for edge2 in graph.get_edges_for_target(way_id, "connection"):
            if edge2.source == area_id:
                continue
            node = graph.get_node(edge2.source)
            if node and node.type == "area":
                neighbors.append(edge2.source)
    return neighbors


def _resolve_area_id(graph, area):
    """Accept an area node id OR an area name (player.current_area stores names)."""
    if not area:
        return None
    if graph.get_node(area):
        return area
    low = str(area).strip().lower()
    for node in graph.nodes.values():
        if node.type == "area" and (str(node.name).strip().lower() == low or node.id == str(area)):
            return node.id
    return None


def room_distance(graph, area_a, area_b):
    """BFS room-to-room distance (0 = same area, 1 = adjacent, None = unreachable)."""
    area_a = _resolve_area_id(graph, area_a)
    area_b = _resolve_area_id(graph, area_b)
    if not area_a or not area_b:
        return None
    if area_a == area_b:
        return 0
    visited = {area_a}
    queue = deque([(area_a, 0)])
    while queue:
        current, dist = queue.popleft()
        for neighbor in _area_neighbors(graph, current):
            if neighbor in visited:
                continue
            if neighbor == area_b:
                return dist + 1
            visited.add(neighbor)
            queue.append((neighbor, dist + 1))
    return None


def _item_area_id(graph, node_id, depth=0):
    """Walk an item's edges upward (in/on/.../carrying/equipped) to the area id."""
    if depth > 6:
        return None
    for edge in graph.edges:
        if edge.source != node_id or edge.type not in ("in", "on", "under", "behind", "beside", "at", "carrying", "equipped"):
            continue
        parent = graph.get_node(edge.target)
        if parent is None:
            continue
        if parent.type == "area":
            return parent.id
        if parent.type == "item":
            nested = _item_area_id(graph, parent.id, depth=depth + 1)
            if nested:
                return nested
    return None


def proximity_report(player_manager, item_node, graph, game_state=None) -> str:
    """Build the narrative reading for *item_node* from the active player's room."""
    cfg = (item_node.properties or {}).get("proximity_effect", {}) or {}
    if not cfg:
        return ""
    max_areas = int(cfg.get("max_areas", 3) or 3)
    detects = [str(d).lower() for d in (cfg.get("detects", []) or [])]
    tags_filter = [str(t).lower() for t in (cfg.get("tags", []) or [])]

    player = player_manager.players.get(player_manager.active_player)
    if not player or not player.current_area:
        return ""
    player_area = player.current_area

    # (distance, label) findings
    findings = []
    if "character" in detects:
        for pname, other in player_manager.players.items():
            if pname == player_manager.active_player:
                continue
            if not getattr(other, "current_area", None):
                continue
            dist = room_distance(graph, player_area, other.current_area)
            if dist is not None and dist <= max_areas:
                label = "a living presence" if other.state != "dead" else "a presence"
                findings.append((dist, label))
    if "item" in detects or "way" in detects:
        for node in graph.nodes.values():
            props = node.properties or {}
            tag_match = (not tags_filter) or any(
                str(t).lower() in tags_filter for t in (props.get("tags", []) or [])
            )
            if not tag_match:
                continue
            if "item" in detects and node.type == "item" and node.id != item_node.id:
                area_id = _item_area_id(graph, node.id)
                if area_id:
                    dist = room_distance(graph, player_area, area_id)
                    if dist is not None and dist <= max_areas:
                        findings.append((dist, f"the {node.name}"))
            if "way" in detects and node.type == "way":
                area_id = None
                for edge in graph.edges:
                    if edge.target == node.id and edge.type == "connection":
                        area_id = edge.source
                        break
                if area_id:
                    dist = room_distance(graph, player_area, area_id)
                    if dist is not None and dist <= max_areas:
                        findings.append((dist, f"a way ({node.properties.get('current_state', 'closed')})"))

    if not findings:
        return ""
    strong = [label for d, label in findings if d == 0]
    near = [label for d, label in findings if d == 1]
    far = [label for d, label in findings if d >= 2]

    lines = []
    if strong:
        lines.append(f"The device reads sharply — {', '.join(strong)} is right here.")
    if near:
        lines.append("The needle jumps — something is close by.")
    if far:
        lines.append("A faint blip — something drifts a few rooms away, direction unclear.")
    return " ".join(lines)
