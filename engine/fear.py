"""Fear-driven reactions (task-469).

A character reacts to what *they* fear, not to a global "hostile" flag. Every
character carries ``fear_tags`` (mirroring ``interest_tags``); meeting a
co-located character, item, or an area whose tags intersect them applies the
existing source-gated :data:`frightened` condition, and callers (the timeskip,
and later the attended tier) can use that as an interrupt to hand control back.

This is what lets a camp of goblins exist without panicking at itself: goblins
simply do not list ``goblin`` among their fears, while a farmer does.

Fear is also **released**, not only applied (task-484). ``frightened`` gates
behaviour toward one named source, so it is a flag about a specific thing being
present; when that thing leaves, the flag has nothing left to be about. See
:func:`release_absent_fears`.
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


def character_tags(gs, other) -> set:
    """Every tag *other* presents to somebody's ``fear_tags``.

    Three sources, because they are populated by different authoring routes:

    1. ``other.tags`` — the list the shipped data actually fills. Every
       ``data/library/characters/*.json`` and the scenarios carry it
       (``"goblin"``, ``"teen"``, ``"female"``).
    2. ``other.traits`` keys — set by the trait system.
    3. the character's graph node's ``tags`` property.

    (3) alone is not enough and used to be the only source: a character node is
    created bare (``Node(id=..., type="character", name=...)``) on both the add
    and the load path, so it never carries ``tags`` and a node-only lookup
    matches nothing at all. Authoring ``fear_tags: ["goblin"]`` would have
    silently done nothing. The node is still consulted, because a world that
    does stamp tags onto the node deserves to be heard.
    """
    tags = _normalise(getattr(other, "tags", None))
    tags |= _normalise((getattr(other, "traits", None) or {}).keys())
    graph = getattr(gs, "graph", None)
    if graph is not None:
        try:
            node = graph.get_node(gs._player_node_id(getattr(other, "name", "")))
        except Exception:
            node = None
        if node is not None:
            tags |= _tags(node)
    return tags


def fear_sources_for_character(gs, player, other) -> dict | None:
    """The ``{kind: "character"}`` source *player* sees in *other*, or None.

    The single-co-present-character case of :func:`fear_sources`, split out so
    the threat pass can ask the same question about a specific pair without
    rebuilding the whole source list.
    """
    if other is None or other is player:
        return None
    if getattr(other, "current_area", None) != getattr(player, "current_area", None):
        return None
    fears = _normalise(getattr(player, "fear_tags", None))
    if not fears:
        return None
    matched = fears & character_tags(gs, other)
    if not matched:
        return None
    return {"kind": "character", "id": getattr(other, "id", None) or
            getattr(other, "name", ""), "name": getattr(other, "name", ""),
            "tags": sorted(matched)}


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
        source = fear_sources_for_character(gs, player, other)
        if source is not None:
            out.append(source)

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


def release_absent_fears(gs, player, sources=None) -> list:
    """End the ``frightened`` instances whose source is no longer here (task-484).

    ``frightened`` exists to gate behaviour toward one *specific* source:
    ``engine.conditions.frightened_block`` refuses an approach, a way, an area
    or an item **by name**. Gating toward something that has left the world is
    not fear, it is a stuck flag — and it expires on its timer whether or not
    the goblin is still standing there. So the flag lifts when the thing does.

    Precise, per instance: a character who fears two things and has lost one
    keeps the other fear, which is why this does not simply call
    ``end_instances`` for everyone.

    Returns the sources that were released.
    """
    if sources is None:
        sources = fear_sources(gs, player)
    present = {str(s.get("name") or s.get("id") or "") for s in sources}
    instances = list((getattr(player, "conditions", None) or {}).get("frightened") or [])
    if not instances:
        return []
    keep, released = [], []
    for inst in instances:
        source = inst.get("source")
        if source and str(source) not in present:
            released.append(str(source))
        else:
            keep.append(inst)
    if not released:
        return []
    try:
        player.conditions["frightened"] = keep
    except Exception as e:
        logger.warning("[fear] could not release a stale fear for %s: %s",
                       getattr(player, "name", "?"), e)
        return []
    return released


def react(gs, player):
    """Detect and apply fear for *player*; returns the applied source or None.

    Also releases any fear whose source has left, so detection and cleanup can
    never disagree about who is afraid of what.
    """
    sources = fear_sources(gs, player)
    release_absent_fears(gs, player, sources)
    return apply_frightening(gs, player, sources)
