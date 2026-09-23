"""Fear-driven reactions (task-469).

A character reacts to what *they* fear, not to a global "hostile" flag. Every
character carries ``fear_tags`` (mirroring ``interest_tags``); meeting a
co-located character, item, or an area whose tags intersect them applies the
existing source-gated :data:`frightened` condition, and callers (the timeskip,
and later the attended tier) can use that as an interrupt to hand control back.

This is what lets a camp of goblins exist without panicking at itself: goblins
simply do not list ``goblin`` among their fears, while a farmer does.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: How long a fear reaction lasts, in game minutes.
FEAR_DURATION_MINUTES = 30

#: Spatial relations an area holds things by (same set the background runner uses).
SPATIAL_RELATIONS = ("in", "on", "under", "behind", "beside", "at")


def _tags(node) -> set:
    props = getattr(node, "properties", {}) or {}
    return {str(t).lower().strip() for t in (props.get("tags") or [])}


def _normalise(tags) -> set:
    return {str(t).lower().strip() for t in (tags or ()) if str(t).strip()}


def fear_sources(gs, player) -> list:
    """Co-located things whose tags intersect *player*'s ``fear_tags``.

    Returns a list of ``{kind, id, name, tags}`` dicts (kind: character | item |
    area). Empty when the character has no fears or nothing feared is present.
    """
    fears = _normalise(getattr(player, "fear_tags", []))
    if not fears:
        return []

    graph = getattr(gs, "graph", None)
    area = getattr(player, "current_area", None)
    try:
        area_id = gs.area_node_id(area) if area else None
    except Exception:
        area_id = None

    out = []

    # the area itself (a haunted wood, a battlefield)
    if area_id and graph is not None:
        area_node = graph.get_node(area_id)
        matched = fears & _tags(area_node) if area_node is not None else set()
        if matched:
            out.append({"kind": "area", "id": area_id,
                        "name": getattr(area_node, "name", area) or area,
                        "tags": sorted(matched)})

    # co-located characters
    for name, other in (getattr(gs, "players", None) or {}).items():
        if other is player:
            continue
        if getattr(other, "current_area", None) != area:
            continue
        other_tags = _normalise(getattr(other, "traits", {}).keys())   # traits is a dict
        if graph is not None:
            try:
                node = graph.get_node(gs._player_node_id(name))
            except Exception:
                node = None
            if node is not None:
                other_tags |= _tags(node)
        matched = fears & other_tags
        if matched:
            out.append({"kind": "character",
                        "id": getattr(other, "id", name) or name,
                        "name": name, "tags": sorted(matched)})

    # items the area holds by a spatial relation
    if area_id and graph is not None:
        for rel in SPATIAL_RELATIONS:
            for edge in graph.get_edges_for_target(area_id, rel):
                node = graph.get_node(edge.source)
                if node is None or getattr(node, "type", "") != "item":
                    continue
                matched = fears & _tags(node)
                if matched:
                    out.append({"kind": "item", "id": node.id, "name": node.name,
                                "tags": sorted(matched)})

    return out


def apply_frightening(gs, player, sources, duration_minutes=FEAR_DURATION_MINUTES):
    """Apply the ``frightened`` condition from the strongest fear source.

    The instance keeps the source's name and kind, so the existing gates work:
    combat refuses to attack a feared character and movement refuses a feared
    way. Returns the source dict that was applied, or None.
    """
    if not sources:
        return None
    primary = sources[0]
    try:
        per_tick = max(0.001, float(getattr(gs, "time_per_tick_minutes", 1) or 1))
    except (TypeError, ValueError):
        per_tick = 1.0
    duration = max(1, int(round(duration_minutes / per_tick)))
    source = primary.get("name") or primary.get("id")
    try:
        gs.conditions.apply_condition(
            player.name, "frightened", duration=duration, source=source,
            source_type=primary.get("kind"))
    except Exception as e:
        logger.warning("[fear] could not apply frightened to %s: %s", player.name, e)
        return None
    return primary


def react(gs, player):
    """Detect and apply fear for *player*; returns the applied source or None."""
    return apply_frightening(gs, player, fear_sources(gs, player))
