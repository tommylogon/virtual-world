"""Room perception invariants — ONE source of truth for what a character
can perceive in an area.

Two renderers present the same perception:

- the AGENT path: ``area_description.py`` → LLM prompt prose
- the PANEL path: ``scene_snapshot.py`` → ``/api/scene`` (turn composer)

The only allowed difference between them is PRESENTATION. Every time one
path re-implemented a shared rule, it drifted from the other (task-333
area-id crash, bug-23 hidden-way leak, bug-24 requires:"none" gate,
bug-26 empty panel). Renderers must call THESE functions instead of
re-implementing the rules.
"""

from typing import Optional

from graph import EDGE_IN


def normalize_name(value) -> str:
    """Comparison form for node/area names: lowercase, apostrophes dropped,
    underscores/hyphens read as spaces (project rule: id/name checks must
    lowercase everything so case never mismatches)."""
    return (str(value or "").lower()
            .replace("_", " ").replace("-", " ").replace("'", "").strip())


def resolve_area_node(graph, area_name: str) -> Optional[object]:
    """The area node for *area_name* — by NAME first (hand-authored ids
    strip punctuation: "Taco Bell Men's Restroom" lives at
    ``area_tacobell_mens_room``), then the canonical constructed id,
    validated against the graph. None when the area doesn't exist."""
    if graph is None or not area_name:
        return None
    wanted = normalize_name(area_name)
    for node in graph.nodes.values():
        if getattr(node, "type", "") == "area" and normalize_name(node.name) == wanted:
            return node
    from engine.node_ids import NodeIDHelper
    candidate = graph.get_node(NodeIDHelper.area_node_id(area_name))
    if candidate is not None and getattr(candidate, "type", "") == "area":
        return candidate
    return None


def normalize_requires(value) -> str:
    """Legacy data stores the literal "none" for walk-through ways;
    movement.py always special-cased it. none/nothing/no → ""."""
    req = str(value or "").strip().lower()
    if req in ("none", "nothing", "no"):
        return ""
    return str(value or "").strip()


def way_visible_to(player, player_manager, viewer_name: str,
                   way_node, area_name: str, direction: str) -> bool:
    """Hidden ways stay invisible until discovered: the slasher sees every
    hidden exit, anyone else needs the (area name, raw direction) key in
    ``discovered_exits`` — search/fumble discovery writes it (narration.py)."""
    if way_node.properties.get("current_state") != "hidden":
        return True
    try:
        if viewer_name and player_manager.is_slasher(viewer_name):
            return True
    except Exception:
        pass
    discovered = getattr(player, "discovered_exits", None) or set()
    return (str(area_name), str(direction)) in discovered


def visible_area_items(graph, area_id, include_hidden: bool = False) -> list:
    """Non-hidden item nodes in the area (``get_edges_for_target`` already
    expands spatial edges, so surface items count)."""
    items = []
    if graph is None or not area_id:
        return items
    for edge in graph.get_edges_for_target(area_id, EDGE_IN):
        node = graph.get_node(edge.source)
        if node and node.type == "item":
            if include_hidden or node.properties.get("current_state") != "hidden":
                items.append(node)
    return items


def characters_in_area(graph, area_id, exclude_name: Optional[str] = None) -> list:
    """Character nodes present in the area (EDGE_IN), optionally excluding
    the viewer by name."""
    people = []
    if graph is None or not area_id:
        return people
    for edge in graph.get_edges_for_target(area_id, EDGE_IN):
        node = graph.get_node(edge.source)
        if node and node.type == "character":
            if exclude_name is not None and node.name == exclude_name:
                continue
            people.append(node)
    return people
