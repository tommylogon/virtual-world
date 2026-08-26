"""Character spatial position — relations to ways, items, and characters (task-135)."""

import re
from typing import Any, Dict, List, Optional, Tuple

from graph import (
    EDGE_AT,
    EDGE_BESIDE,
    EDGE_BEHIND,
    EDGE_CONNECTION,
    EDGE_IN,
    EDGE_ON,
    EDGE_UNDER,
    SPATIAL_EDGE_TYPES,
    Edge,
)

_CHARACTER_POSITION_TYPES = tuple(SPATIAL_EDGE_TYPES)


# ── Duck-typed helpers (combat tests patch methods, not attributes) ──────────

def _pm_get_player(player_manager, name: str):
    """Look up a player by name — prefer ``get_player`` (tests patch it)."""
    getter = getattr(player_manager, "get_player", None)
    if callable(getter):
        return getter(name)
    players = getattr(player_manager, "players", None)
    if isinstance(players, dict):
        return players.get(name)
    return None


def _pm_get_player_node_id(player_manager, name: str) -> Optional[str]:
    getter = getattr(player_manager, "get_player_node_id", None)
    if callable(getter):
        return getter(name)
    getter = getattr(player_manager, "player_node_id", None)
    if callable(getter):
        return getter(name)
    helper = getattr(player_manager, "_player_node_id", None)
    if callable(helper):
        return helper(name)
    from engine.node_ids import NodeIDHelper
    return NodeIDHelper.player_node_id(name)


def _pm_active_player(player_manager) -> Optional[str]:
    active = getattr(player_manager, "active_player", None)
    if active is not None:
        return active
    pm = getattr(player_manager, "player_manager", None)
    if pm is not None:
        return getattr(pm, "active_player", None)
    return None


def _pm_current_area_name(player_manager) -> Optional[str]:
    """Return the current area *name* (not node id) for the active player."""
    area = getattr(player_manager, "current_area", None)
    if area is not None:
        name = getattr(area, "name", None)
        if name:
            return name
        if isinstance(area, str):
            return area
    helper = getattr(player_manager, "_get_current_area_id", None)
    if callable(helper):
        area_id = helper()
        if area_id:
            return area_id.replace("area_", "").replace("_", " ")
    active_name = _pm_active_player(player_manager)
    if active_name:
        player = _pm_get_player(player_manager, active_name)
        if player is not None:
            current = getattr(player, "current_area", None)
            if current:
                return current
    return None

_RELATION_PHRASES = (
    ("from below", EDGE_UNDER),
    ("on top of", EDGE_ON),
    ("next to", EDGE_BESIDE),
    ("underneath", EDGE_UNDER),
    ("under", EDGE_UNDER),
    ("beneath", EDGE_UNDER),
    ("below", EDGE_UNDER),
    ("behind", EDGE_BEHIND),
    ("beside", EDGE_BESIDE),
    ("near", EDGE_AT),
    ("at", EDGE_AT),
    ("on", EDGE_ON),
)


def _normalize_tags(node) -> List[str]:
    if not node:
        return []
    props = getattr(node, "properties", None) or {}
    return [str(t).lower().strip() for t in props.get("tags", []) or []]


def is_transit_area(area_node) -> bool:
    if not area_node or area_node.type != "area":
        return False
    props = area_node.properties or {}
    if props.get("transit"):
        return True
    tags = _normalize_tags(area_node)
    return "transit" in tags or "passage" in tags


def clear_character_position_edges(graph, player_node_id: str) -> None:
    for edge_type in _CHARACTER_POSITION_TYPES:
        for edge in list(graph.get_edges_for_source(player_node_id, edge_type)):
            graph.remove_edge(edge.source, edge.target, edge.type)


def set_character_position(
    graph,
    player_node_id: str,
    target_id: str,
    relation: str = EDGE_AT,
) -> None:
    if not player_node_id or not target_id:
        return
    if relation not in SPATIAL_EDGE_TYPES:
        relation = EDGE_AT
    target = graph.get_node(target_id)
    if not target or target.type not in ("way", "item", "character", "player"):
        return
    clear_character_position_edges(graph, player_node_id)
    graph.add_edge(Edge(source=player_node_id, target=target_id, type=relation))


def set_character_at_way(graph, player_node_id: str, way_id: str) -> None:
    set_character_position(graph, player_node_id, way_id, EDGE_AT)


def get_character_position(graph, player_node_id: str) -> Optional[Dict[str, str]]:
    """Return {relation, target_id} for the player's spatial anchor, if any."""
    for edge_type in _CHARACTER_POSITION_TYPES:
        for edge in graph.get_edges_for_source(player_node_id, edge_type):
            target = graph.get_node(edge.target)
            if not target:
                continue
            if target.type in ("way", "item", "character", "player"):
                return {"relation": edge.type, "target_id": edge.target}
    return None


def get_character_at_way(graph, player_node_id: str) -> Optional[str]:
    pos = get_character_position(graph, player_node_id)
    if not pos or pos["relation"] != EDGE_AT:
        return None
    way = graph.get_node(pos["target_id"])
    if way and way.type == "way":
        return pos["target_id"]
    return None


def approach_way(graph, player_node_id: str, way_id: str) -> None:
    """Walk up to a way — physical open/close/go/use implies stepping to it."""
    set_character_at_way(graph, player_node_id, way_id)


def default_relation_for_item(item_node) -> str:
    tags = set(_normalize_tags(item_node))
    if tags & {"in_roof", "on_ceiling", "ceiling"}:
        return EDGE_UNDER
    if tags & {"in_floor", "on_ground", "floor"}:
        return EDGE_ON
    return EDGE_AT


def default_relation_for_character() -> str:
    return EDGE_BESIDE


def parse_spatial_target(text: str, default_relation: str = EDGE_AT) -> Tuple[str, str]:
    """Infer relation from phrasing; return (relation, original text)."""
    lower = (text or "").lower().strip()
    relation = default_relation
    for phrase, rel in _RELATION_PHRASES:
        if re.search(rf"(?:^|\s){re.escape(phrase)}(?:\s|$)", lower):
            relation = rel
            break
    return relation, (text or "").strip()


def _item_in_area(graph, item_id: str, area_id: str) -> bool:
    if not item_id or not area_id:
        return False
    for edge_type in (EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT):
        for edge in graph.get_edges_for_target(area_id, edge_type):
            if edge.source.lower() == item_id.lower():
                return True
    for edge in graph.get_edges_for_source(item_id, EDGE_IN):
        if edge.target.lower() == area_id.lower():
            return True
    return False


def _way_connects_area(graph, way_id: str, area_id: str) -> bool:
    area_lower = area_id.lower()
    for edge in graph.get_edges_for_source(area_id, EDGE_CONNECTION):
        if edge.target.lower() == way_id.lower():
            return True
    for edge in graph.get_edges_for_source(way_id, EDGE_CONNECTION):
        if edge.target.lower() == area_lower:
            return True
    return False


def _relation_phrase(relation: str, label: str) -> str:
    article = "the "
    if relation == EDGE_ON:
        return f" on {article}{label}"
    if relation == EDGE_UNDER:
        return f" under {article}{label}"
    if relation == EDGE_BEHIND:
        return f" behind {article}{label}"
    if relation == EDGE_BESIDE:
        return f" beside {article}{label}"
    return f" at {article}{label}"


def _display_target_name(target, viewer_player=None, player_manager=None) -> str:
    if not target:
        return "something"
    if target.type in ("character", "player") and player_manager and viewer_player:
        pname = target.name or target.id.replace("player_", "").replace("_", " ")
        subject = _pm_get_player(player_manager, pname)
        if subject and pname != viewer_player:
            return subject.unknown_display_name()
        return pname
    name = (target.properties or {}).get("name") or target.name or target.id
    return str(name).replace("_", " ")


def spatial_position_phrase(
    graph,
    player_node_id: str,
    area_id: str,
    area_name: str = "",
    viewer_player: str = "",
    player_manager=None,
) -> str:
    """Return e.g. ' under the chandelier' / ' beside the man' / ' at the north'."""
    pos = get_character_position(graph, player_node_id)
    if not pos:
        return ""

    target = graph.get_node(pos["target_id"])
    if not target:
        return ""

    relation = pos["relation"]

    if target.type == "way":
        if not _way_connects_area(graph, target.id, area_id):
            return ""
        from engine.matching import NameMatching

        for edge in graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            if edge.target.lower() != target.id.lower():
                continue
            handle = NameMatching.way_handle(
                target, edge.properties.get("direction", ""), area_name or "",
            )
            return _relation_phrase(EDGE_AT, handle)

    if target.type == "item":
        if not _item_in_area(graph, target.id, area_id):
            return ""
        label = _display_target_name(target)
        return _relation_phrase(relation, label)

    if target.type in ("character", "player") and player_manager:
        pname = target.name or target.id.replace("player_", "").replace("_", " ")
        subject = _pm_get_player(player_manager, pname)
        if not subject or subject.current_area != _pm_current_area_name(player_manager):
            return ""
        label = _display_target_name(target, viewer_player, player_manager)
        return _relation_phrase(relation, label)

    return ""


def at_opening_phrase(graph, player_node_id: str, area_id: str, area_name: str = "") -> str:
    """Backward-compatible alias — any spatial phrase in this area."""
    return spatial_position_phrase(graph, player_node_id, area_id, area_name)


def get_spatial_position_data(graph, player_node_id: str, player_manager=None, viewer_player: str = "") -> Optional[Dict[str, Any]]:
    pos = get_character_position(graph, player_node_id)
    if not pos:
        return None
    target = graph.get_node(pos["target_id"])
    if not target:
        return None
    target_type = "way" if target.type == "way" else (
        "character" if target.type in ("character", "player") else target.type
    )
    return {
        "relation": pos["relation"],
        "target_id": pos["target_id"],
        "target_type": target_type,
        "target_name": _display_target_name(target, viewer_player, player_manager),
    }


def approach_item(
    graph,
    player_manager,
    target_name: str,
    item_node,
    relation: str = None,
) -> None:
    """Walk up to a room item — used by examine, use-on, put/place."""
    if not _pm_active_player(player_manager) or not item_node:
        return
    current_area_name = _pm_current_area_name(player_manager)
    area_id = None
    if current_area_name:
        area_id = "area_" + current_area_name.lower().replace(" ", "_")
    if not area_id or not _item_in_area(graph, item_node.id, area_id):
        return
    pid = _pm_get_player_node_id(player_manager, _pm_active_player(player_manager))
    if not pid:
        return
    if not relation:
        relation, _ = parse_spatial_target(target_name, default_relation_for_item(item_node))
    set_character_position(graph, pid, item_node.id, relation)


def approach_character(graph, player_manager, target_pname: str, actor_name: str = None) -> None:
    """Walk up to another character — grab, give, steal, use-on, examine."""
    actor = actor_name or _pm_active_player(player_manager)
    if not actor or not target_pname or actor == target_pname:
        return
    target = _pm_get_player(player_manager, target_pname)
    if not target or target.current_area != _pm_current_area_name(player_manager):
        return
    pid = _pm_get_player_node_id(player_manager, actor)
    target_pid = _pm_get_player_node_id(player_manager, target_pname)
    if not pid or not target_pid:
        return
    set_character_position(graph, pid, target_pid, default_relation_for_character())


def set_position_examining_character(graph, player_manager, target_pname: str) -> None:
    approach_character(graph, player_manager, target_pname)


def set_position_examining_item(graph, player_manager, target_name: str, item_node) -> None:
    approach_item(graph, player_manager, target_name, item_node)


def set_position_using_target(graph, player_manager, target_name: str, target_node) -> None:
    if not _pm_active_player(player_manager) or not target_node:
        return
    pid = _pm_get_player_node_id(player_manager, _pm_active_player(player_manager))
    if not pid:
        return
    if target_node.type == "way":
        set_character_at_way(graph, pid, target_node.id)
    elif target_node.type == "item":
        current_area_name = _pm_current_area_name(player_manager)
        area_id = None
        if current_area_name:
            area_id = "area_" + current_area_name.lower().replace(" ", "_")
        if area_id and _item_in_area(graph, target_node.id, area_id):
            relation, _ = parse_spatial_target(target_name, default_relation_for_item(target_node))
            set_character_position(graph, pid, target_node.id, relation)
    elif target_node.type in ("character", "player"):
        pname = target_node.name
        if pname and pname != _pm_active_player(player_manager):
            set_position_examining_character(graph, player_manager, pname)


def _collect_area_ways(graph, area_id: str, area_name: str = "") -> List[Dict[str, Any]]:
    from engine.matching import NameMatching

    rows = []
    seen = set()
    for edge in graph.get_edges_for_source(area_id, EDGE_CONNECTION):
        way_id = edge.target
        if way_id in seen:
            continue
        way = graph.get_node(way_id)
        if not way or way.type != "way":
            continue
        seen.add(way_id)
        target_name = ""
        for conn in graph.get_edges_for_source(way_id, EDGE_CONNECTION):
            if conn.target.lower() != area_id.lower():
                target = graph.get_node(conn.target)
                if target:
                    target_name = target.name
                    break
        rows.append({
            "edge": edge,
            "way": way,
            "way_id": way_id,
            "handle": NameMatching.way_handle(
                way, edge.properties.get("direction", ""), area_name or "",
            ),
            "target_name": target_name,
        })
    return rows


def get_transit_roles(
    graph,
    area_id: str,
    player_node_id: str,
    area_name: str = "",
) -> Optional[Dict[str, Any]]:
    """When in a transit area and AT a way, return back/forward exit info."""
    area_node = graph.get_node(area_id)
    if not is_transit_area(area_node):
        return None
    at_way_id = get_character_at_way(graph, player_node_id)
    if not at_way_id:
        return None
    ways = _collect_area_ways(graph, area_id, area_name)
    if len(ways) < 2:
        return None
    back = next((row for row in ways if row["way_id"].lower() == at_way_id.lower()), None)
    if not back:
        return None
    forward_candidates = [row for row in ways if row["way_id"].lower() != at_way_id.lower()]
    if len(forward_candidates) != 1:
        return None
    forward = forward_candidates[0]
    return {
        "back_edge": back["edge"],
        "back_way": back["way"],
        "back_handle": "back",
        "back_real_handle": back["handle"],
        "forward_edge": forward["edge"],
        "forward_way": forward["way"],
        "forward_handle": "forward",
        "forward_real_handle": forward["handle"],
        "forward_target": forward["target_name"],
    }


def resolve_transit_movement(
    graph,
    game_state,
    area_id: str,
    direction: str,
) -> Optional[Tuple[Any, Any, str]]:
    """Resolve go back / go forward in transit areas. Returns (edge, way, handle)."""
    direction_lower = (direction or "").lower().strip()
    if direction_lower not in ("back", "forward"):
        return None
    player_name = getattr(game_state, "active_player", None)
    if not player_name:
        return None
    player_node_id = game_state._player_node_id(player_name)
    area_name = ""
    if getattr(game_state, "current_area", None):
        area_name = game_state.current_area.name or ""
    roles = get_transit_roles(graph, area_id, player_node_id, area_name)
    if not roles:
        return None
    if direction_lower == "back":
        return roles["back_edge"], roles["back_way"], roles["back_real_handle"]
    return roles["forward_edge"], roles["forward_way"], roles["forward_real_handle"]
