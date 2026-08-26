"""Dynamic people/items glimpsed through open or see-through ways (task-201)."""

from typing import Any, List, Optional

from graph import EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT

_SPATIAL = (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT)


def normalize_visible_items(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        text = raw.strip()
        return [text] if text else []
    if isinstance(raw, list):
        return [str(name).strip() for name in raw if str(name).strip()]
    return []


def collect_items_in_area(graph, area_id: str, allowed_names: Optional[List[str]] = None) -> List[str]:
    """Return item names present in *area_id* (direct, spatial, container contents)."""
    allowed = {n.lower() for n in allowed_names} if allowed_names else None
    items: List[str] = []
    seen = set()

    def maybe_add(node) -> None:
        if not node or node.type != "item":
            return
        if node.properties.get("current_state") == "hidden":
            return
        if node.id in seen:
            return
        if allowed is not None and node.name.lower() not in allowed:
            return
        seen.add(node.id)
        items.append(node.name)

    anchor_ids = set()
    for edge in graph.get_edges_for_target(area_id, EDGE_IN):
        node = graph.get_node(edge.source)
        if node and node.type == "item":
            maybe_add(node)
            anchor_ids.add(node.id)

    anchors = set(anchor_ids)
    anchors.add(area_id)
    for edge in graph.edges:
        if edge.type in _SPATIAL and edge.target in anchors:
            maybe_add(graph.get_node(edge.source))

    for item_id in list(seen):
        container = graph.get_node(item_id)
        if not container or container.type != "item":
            continue
        if container.properties.get("current_state") == "locked":
            continue
        for edge in graph.get_edges_for_target(item_id, EDGE_IN):
            maybe_add(graph.get_node(edge.source))

    return items


def _character_beyond_label(player_manager, pdata, active_player_obj) -> str:
    from engine.activities import activity_description

    pname = pdata["name"]
    pstate = pdata.get("state", "awake")
    known = active_player_obj is not None and active_player_obj.has_met(pname)
    if known:
        label = pname
    else:
        target_player = player_manager.players.get(pname)
        label = target_player.unknown_display_name() if target_player else pname
    if pstate in ("dead", "ghost"):
        return f"{label} (ghost)"
    activity = getattr(player_manager.players.get(pname), "activity", None)
    if activity and activity.get("visible", True):
        act_text = activity_description(activity)
        if act_text:
            return f"{label} ({act_text})"
    if pstate != "awake":
        return f"{label} ({pstate})"
    return label


def build_beyond_suffix(graph, player_manager, target_area_id, target_area_name, edge_props, active_player_obj) -> str:
    """Suffix for exit/examine lines, e.g. ' Beyond you can see: Lyrie, the clock.'"""
    allow_chars = bool(edge_props.get("allow_see_characters"))
    visible_items = normalize_visible_items(edge_props.get("visible_items"))
    if not allow_chars and not visible_items:
        return ""

    parts: List[str] = []
    if allow_chars and target_area_name:
        for pdata in player_manager.get_players_in_area(target_area_name):
            parts.append(_character_beyond_label(player_manager, pdata, active_player_obj))

    if visible_items and target_area_id:
        for name in collect_items_in_area(graph, target_area_id, visible_items):
            parts.append(f"the {name}")

    if not parts:
        return ""
    return f" Beyond you can see: {', '.join(parts)}."
