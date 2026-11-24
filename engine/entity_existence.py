"""Authored entity existence windows across scenario chronology (task-1009).

Any character (Player or character Node), item Node, or way Node may carry optional
ISO-8601 bounds ``exists_from`` / ``exists_until`` (or ``spawn_datetime`` /
``despawn_datetime``) on its attributes or ``properties`` dict. When the world clock
moves outside that window, the entity is phased out of room prompts, ticks, and
marked ``exists_now: False`` in ``/api/state``.
"""
from __future__ import annotations

from typing import Any, Optional, Tuple


def _norm_iso(val: Any) -> Optional[str]:
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    # Normalize YYYY-MM-DD to start-of-day ISO so lexicographical comparison is exact
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return f"{s}T00:00:00"
    if len(s) == 16 and "T" in s:
        return f"{s}:00"
    return s


def _norm_iso_end(val: Any) -> Optional[str]:
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    # Date-only upper bound includes the entire day
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return f"{s}T23:59:59"
    if len(s) == 16 and "T" in s:
        return f"{s}:59"
    return s


def extract_existence_window(entity: Any) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(exists_from_iso, exists_until_iso)`` for a Player, Node, or dict."""
    if entity is None:
        return None, None
    props = {}
    if isinstance(entity, dict):
        props = entity.get("properties") if isinstance(entity.get("properties"), dict) else {}
        raw_from = entity.get("exists_from") or entity.get("spawn_datetime") or props.get("exists_from") or props.get("spawn_datetime")
        raw_until = entity.get("exists_until") or entity.get("despawn_datetime") or props.get("exists_until") or props.get("despawn_datetime")
    else:
        raw_props = getattr(entity, "properties", None)
        if isinstance(raw_props, dict):
            props = raw_props
        raw_from = (
            getattr(entity, "exists_from", None)
            or getattr(entity, "spawn_datetime", None)
            or props.get("exists_from")
            or props.get("spawn_datetime")
        )
        raw_until = (
            getattr(entity, "exists_until", None)
            or getattr(entity, "despawn_datetime", None)
            or props.get("exists_until")
            or props.get("despawn_datetime")
        )
    return _norm_iso(raw_from), _norm_iso_end(raw_until)


def world_current_datetime(world: Any) -> Optional[str]:
    if world is None:
        return None
    if hasattr(world, "datetime_for_tick"):
        try:
            return _norm_iso(world.datetime_for_tick())
        except Exception:
            return None
    return None


def entity_exists_at(entity: Any, current_datetime: Optional[str], *, world: Any = None) -> bool:
    """Return True if ``entity`` exists at ``current_datetime`` (default True when unbounded)."""
    cur_dt = _norm_iso(current_datetime) or world_current_datetime(world)
    if not cur_dt:
        return True
    start_iso, end_iso = extract_existence_window(entity)
    if start_iso and cur_dt < start_iso:
        return False
    if end_iso and cur_dt > end_iso:
        return False
    return True


def player_exists_now(world: Any, player_name: str, player: Any = None) -> bool:
    """Check both the Player object and its backing character graph Node."""
    cur_dt = world_current_datetime(world)
    if not cur_dt:
        return True
    p = player or (getattr(world, "players", None) or {}).get(player_name)
    if p is not None and not entity_exists_at(p, cur_dt):
        return False
    graph = getattr(world, "graph", None)
    if graph is not None and hasattr(graph, "get_node"):
        pm = getattr(world, "player_manager", None)
        nid = pm.player_node_id(player_name) if (pm and hasattr(pm, "player_node_id")) else f"player_{player_name.lower().replace(' ', '_')}"
        node = graph.get_node(nid)
        if node is not None and not entity_exists_at(node, cur_dt):
            return False
    return True
