"""Way/area effect handlers (spawn_way, spawn_area, set_way_target, set_way_view).

Ways are the only node type with connection edges (area <-> way). The edge
topology mirrors ``movement.connect_areas`` exactly so spawned ways behave
like hand-built doors from the first tick.

task-357 (spawn_way), task-356 (spawn_area), task-192 (set_way_target),
task-193 (set_way_view).
"""

import time

from graph import Node, Edge, EDGE_CONNECTION
from engine.node_ids import NodeIDHelper

_OPPOSITE = {
    "north": "south", "south": "north",
    "east": "west", "west": "east",
    "up": "down", "down": "up",
    "in": "out", "out": "in",
    "left": "right", "right": "left",
    "inside": "outside", "outside": "inside",
    "forward": "back", "back": "forward",
}


def _opposite(direction: str) -> str:
    d = str(direction or "").lower().strip()
    return _OPPOSITE.get(d, d)


def _resolve_area(graph, name):
    """Resolve an area node by name: id-guess first, then case-insensitive scan."""
    if not name:
        return None
    aid = NodeIDHelper.area_node_id(str(name))
    node = graph.get_node(aid)
    if node is not None and node.type == "area":
        return node
    low = str(name).lower()
    for n in graph.nodes.values():
        if n.type == "area" and str(n.name).lower() == low:
            return n
    return None


def handle_spawn_way(self, params, context, item_node=None, game_state=None):
    """Materialize a way node + connection edges at runtime.

    params:
      area_from / from_area — area name the door is IN (required)
      target / area_to / to_area — area name the door leads TO (required)
      direction — exit direction on the from side (default "north")
      reverse_direction — direction on the target side (defaults to the
                          opposite cardinal)
      way_id — explicit node id (defaults to ``way_<from>_<direction>``)
      state — open / locked / hidden / closed (default "open")
      description, pass_message, cost, see_through, tags, insulation,
      prevent_close, max_size, requires, one_way
      message — narration; ``{target_name}`` supported

    Idempotent: an existing way_id is a no-op (returns the default message).
    """
    from_area = params.get("area_from") or params.get("from_area")
    target_area = params.get("target") or params.get("area_to") or params.get("to_area")
    if not from_area or not target_area:
        return []
    n_from = _resolve_area(self.graph, from_area)
    n_to = _resolve_area(self.graph, target_area)
    if not n_from or not n_to:
        return [params.get("fail_message") or
                f"spawn_way: unknown area ({from_area or target_area})."]
    direction = str(params.get("direction", "north")).lower().strip() or "north"
    rev_dir = str(params.get("reverse_direction") or _opposite(direction)).lower().strip()
    if params.get("way_id"):
        way_id = str(params["way_id"])
    elif game_state is not None and hasattr(game_state, "_way_node_id"):
        way_id = game_state._way_node_id(f"{n_from.name}_{direction}")
    else:
        way_id = NodeIDHelper.way_node_id(n_from.name, direction)
    if self.graph.get_node(way_id) is not None:
        return [params.get("message") or
                f"The {direction} passage is already there."]
    one_way = bool(params.get("one_way"))

    props = {
        "current_state": params.get("state", "open"),
        "description": params.get("description", ""),
        "pass_message": params.get("pass_message", ""),
        "cost": params.get("cost", {}) or {},
        "area_from": n_from.name,
        "area_to": n_to.name,
    }
    for key in ("see_through", "tags", "insulation", "prevent_close",
                "max_size", "requires", "auto_close"):
        if key in params:
            props[key] = params[key]
    if one_way:
        props["one_way"] = True

    way_node = Node(id=way_id, type="way", name=f"{n_from.name}-{direction}",
                    properties=props)
    self.graph.add_node(way_node)

    # Link from -> way (direction) and way -> target (target-side direction).
    self.graph.add_edge(Edge(source=n_from.id, target=way_id,
                             type=EDGE_CONNECTION, properties={"direction": direction}))
    self.graph.add_edge(Edge(source=way_id, target=n_to.id,
                             type=EDGE_CONNECTION, properties={"direction": rev_dir}))
    if not one_way:
        # Link target -> way and way -> from so passage works both ways.
        self.graph.add_edge(Edge(source=n_to.id, target=way_id,
                                 type=EDGE_CONNECTION, properties={"direction": rev_dir}))
        self.graph.add_edge(Edge(source=way_id, target=n_from.id,
                                 type=EDGE_CONNECTION, properties={"direction": direction}))

    msg = params.get("message") or f"A {direction} passage opens toward {n_to.name}."
    return [self._render_template_fn(msg, context)]


def handle_spawn_area(self, params, context, item_node=None, game_state=None):
    """Create a whole new area node (with environment) at runtime.

    params:
      name — area name (required; node id = ``area_<slug>``)
      description, environment {light, temperature, air, smell, noise},
      tags, floor
      message — narration
    Also useful as the partner of ``spawn_way`` to add reachable space.
    """
    name = str(params.get("name") or "").strip()
    if not name:
        return []
    aid = NodeIDHelper.area_node_id(name)
    if self.graph.get_node(aid) is not None:
        return [params.get("message") or f"{name} already exists."]
    env = params.get("environment") or {}
    props = {
        "description": params.get("description", ""),
        "environment": {
            "light": env.get("light", 80),
            "temperature": env.get("temperature", 21),
            "air": env.get("air", "fresh"),
            "smell": env.get("smell", "neutral"),
            "noise": env.get("noise", "quiet"),
        },
    }
    for key in ("tags", "floor"):
        if key in params:
            props[key] = params[key]
    area_node = Node(id=aid, type="area", name=name, properties=props)
    self.graph.add_node(area_node)
    msg = params.get("message") or f"{name} materializes."
    return [self._render_template_fn(msg, context)]


def handle_set_way_target(self, params, context, item_node=None, game_state=None):
    """Rewire where a way's connection leads (elevators, portals, cars).

    params:
      way_id / node_id — the way to repoint (item_node may be the way)
      target / area_to — the NEW area name the way leads to
      direction — from-side exit direction (defaults to the way's current)
      reverse_direction — target-side direction (defaults to the opposite)

    The way keeps its identity/state/description and the from-side edge;
    all other connection edges are rebuilt toward the new target.
    """
    way_id = params.get("way_id") or params.get("node_id")
    if not way_id and item_node is not None and item_node.type == "way":
        way_id = item_node.id
    target_name = params.get("target") or params.get("area_to")
    if not way_id or not target_name:
        return []
    way_node = self.graph.get_node(way_id)
    n_to = _resolve_area(self.graph, target_name)
    if way_node is None or way_node.type != "way" or n_to is None:
        return [params.get("fail_message") or
                f"set_way_target: nothing to repoint ({way_id or target_name})."]
    if str(way_node.properties.get("area_to", "")).lower() == str(n_to.name).lower():
        return [params.get("message") or
                f"The passage already leads to {n_to.name}."]

    # Keep the from-side edge pair; drop every other connection edge first.
    n_from = _resolve_area(self.graph, way_node.properties.get("area_from", ""))
    keep_from_id = n_from.id if n_from is not None else None
    from_dir = str(params.get("direction", "")).lower().strip()
    if not from_dir:
        if keep_from_id:
            for edge in self.graph.get_edges_for_source(keep_from_id, EDGE_CONNECTION):
                if edge.target == way_id:
                    from_dir = str(edge.properties.get("direction", "")).lower().strip()
                    break
    from_dir = from_dir or "north"

    for edge in list(self.graph.edges):
        if edge.type != EDGE_CONNECTION:
            continue
        if edge.source != way_id and edge.target != way_id:
            continue
        other = edge.target if edge.source == way_id else edge.source
        if keep_from_id is not None and other == keep_from_id:
            continue  # keep the from-side area->way edge
        self.graph.edges.remove(edge)

    rev_dir = str(params.get("reverse_direction") or _opposite(from_dir)).lower().strip()
    self.graph.add_edge(Edge(source=way_id, target=n_to.id,
                             type=EDGE_CONNECTION, properties={"direction": rev_dir}))
    self.graph.add_edge(Edge(source=n_to.id, target=way_id,
                             type=EDGE_CONNECTION, properties={"direction": rev_dir}))
    if keep_from_id is not None:
        self.graph.add_edge(Edge(source=way_id, target=keep_from_id,
                                 type=EDGE_CONNECTION, properties={"direction": from_dir}))
    way_node.properties["area_to"] = n_to.name
    way_node.updated = time.time()
    self.graph.nodes[way_id] = way_node

    msg = params.get("message") or f"The passage now leads to {n_to.name}."
    return [self._render_template_fn(msg, context)]


def handle_set_way_view(self, params, context, item_node=None, game_state=None):
    """Mutate the way metadata that drives what you see through it.

    params:
      way_id / node_id — the way (item_node may be the way)
      description — view text shown when looking through
      see_through — bool: light/vision pass through
      state — current_state (open/locked/hidden/closed)
      message — narration

    Coordinates with task-192: both mutate the way node so prompts and
    area descriptions pick up the change immediately (they read the way
    node live, not a serialized view).
    """
    way_id = params.get("way_id") or params.get("node_id")
    if not way_id and item_node is not None and item_node.type == "way":
        way_id = item_node.id
    way_node = self.graph.get_node(way_id) if way_id else None
    if way_node is None or way_node.type != "way":
        return []
    changes = {}
    if "description" in params:
        changes["description"] = params["description"]
    if "see_through" in params:
        changes["see_through"] = bool(params["see_through"])
    if "state" in params:
        changes["current_state"] = params["state"]
    if not changes:
        return []
    way_node.properties.update(changes)
    way_node.updated = time.time()
    self.graph.nodes[way_id] = way_node
    msg = params.get("message") or "The view through the passage shifts."
    return [self._render_template_fn(msg, context)]


HANDLERS = {
    "spawn_way": handle_spawn_way,
    "spawn_area": handle_spawn_area,
    "set_way_target": handle_set_way_target,
    "set_way_view": handle_set_way_view,
}
