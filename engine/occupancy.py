"""Per-area occupancy computed from the SIZE of what is standing in it (task-653).

A headcount cannot express a room. "Four occupants" is no answer to "can the
tarrasque come in?", and it is equally wrong for a fairy's house as for a throne
room. Occupancy here is a **sum of footprints**, and each footprint comes from
the size tier that way ``max_size`` passage gating already reads
(:mod:`engine.size`) — a second reader of the same axis, not a new concept.

Two things make it more than a scaled headcount:

* **Zero space is not "tiny".** A 1 cm spider is tiny and takes up one unit. A
  ghost is *intangible* and takes up nothing at all, no matter how large it was
  authored. Those are different facts and they get different representations: a
  size tier and the ``ghost`` tag that ``PlayerManager.is_incorporeal`` already
  owns (task-309). Collapsing them would either let a crowd of ghosts shove a
  living orc out of a latrine, or make every ghost block a doorway.
* **An entity larger than the room still fits alone.** Capacity is a *budget*,
  not a gate on identity: a titanic dragon in a small hall is over budget on
  arrival, which is a legitimate state for the room to be in (that is what
  "the dragon is in the hall" looks like) and a fact worth reporting rather than
  a reason to refuse the world a scene. Callers that want a gate ask
  :func:`fits`.

Authoring:

* An area's ``max_occupancy`` property is its budget. Absent, an area gets
  :data:`DEFAULT_MAX_OCCUPANCY`, which is deliberately generous — this is a
  *narrative* pressure ("the room is packed"), not a collision system, and a
  world whose every corridor jams is a world nobody can move in.
* A size tier's footprint is a named scale (:data:`TIER_SPACE`) rather than a
  formula, so "a normal creature fills a quarter of a small room" is a tunable
  number an author can reason about, not an emergent result.

This module reads a ``Player`` roster and/or the graph, exactly like
:mod:`engine.relief` beside it, so the background tier and the foreground agree
about how full a room is.
"""

from __future__ import annotations

import logging

from engine.size import SIZE_TIERS

logger = logging.getLogger(__name__)

#: How much of a room's budget one creature of each tier fills. Relative
#: (non-linear) on purpose: a titanic thing is not six normals, it does not fit
#: beside them. Tunable rather than derived — see the module docstring.
TIER_SPACE: dict[str, int] = {
    "tiny": 1,      # a rat, a sprite
    "small": 2,     # a goblin
    "normal": 4,    # a person: a quarter of a default room
    "huge": 16,     # an ogre
    "giant": 40,    # a hill giant
    "titanic": 200,  # an ancient dragon
}

#: Budget for an area that declares no ``max_occupancy``. Generous on purpose:
#: 100 units is four ogres, ten people, or a hundred rats. The point is to make
#: a packed room *legible*, not to police every doorway.
DEFAULT_MAX_OCCUPANCY = 100

#: Tags that make an entity take up no space at all, distinct from being small.
#: ``ghost`` is the one that already means "intangible" in the engine (task-309,
#: `PlayerManager.is_incorporeal`); the rest are synonyms an author may reach for
#: and are listed here so the question has one answer rather than a guess per
#: call site.
ZERO_SPACE_TAGS = frozenset({
    "ghost", "incorporeal", "intangible", "ethereal", "phasing",
})

#: Area properties that may carry the budget, most specific first. An author who
#: writes ``max_occupancy`` gets it; older areas that were described with a
#: ``capacity`` word are not silently given one, because guessing a room's size
#: from its name is how a corridor ends up holding a dragon.
AREA_BUDGET_PROPERTIES = ("max_occupancy", "occupancy_limit")


def _tag_source(entity):
    """Where an entity's tags live, for either kind of object.

    A ``Player`` carries ``tags`` directly. A **bare graph character node does
    not** — it is created with id/type/name and nothing else, which is exactly
    the trap that made ``engine/fear.py`` match against the wrong object. So a
    node's tags come from its ``properties``, and both are accepted here rather
    than guessing which one was handed in.
    """
    if entity is None:
        return ()
    tags = getattr(entity, "tags", None)
    if tags is None:
        props = getattr(entity, "properties", None)
        if props is None:
            props = (getattr(entity, "properties", None) or {})
        tags = (props or {}).get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return tags or ()


def takes_no_space(entity) -> bool:
    """True when *entity* is intangible and occupies no room at all.

    Reads the ``Player`` **or** the node's ``properties`` — never a bare graph
    node's attributes, which carry no tags at all.
    """
    return bool(ZERO_SPACE_TAGS & {str(t).lower() for t in _tag_source(entity)})


def _size_source(entity):
    """The size name for either a ``Player`` (``.size``) or a node (properties)."""
    if entity is None:
        return "normal"
    prop = getattr(entity, "size", None)
    if prop is None:
        props = getattr(entity, "properties", None) or {}
        prop = (props or {}).get("size")
    name = str(prop or "").strip().lower()
    if name in SIZE_TIERS:
        return name
    # Fall back to a `size_*` trait, which is what a hand-authored world that
    # predates the `size` property (task-605) will have instead.
    traits = getattr(entity, "traits", None)
    if traits is None:
        traits = ((getattr(entity, "properties", None) or {}) or {}).get("traits") or {}
    for trait_id in traits:
        if str(trait_id).startswith("size_"):
            candidate = str(trait_id)[len("size_"):]
            if candidate in SIZE_TIERS:
                return candidate
    return "normal"


def space_of(entity) -> int:
    """Footprint of *entity* in room-budget units. Zero when it takes no space.

    This is the single place a size becomes an occupancy number. It deliberately
    does **not** call ``engine.size.size_name``: that reads ``player.size``, which
    a graph node does not have, so a graph-only resident would silently be
    counted as ``normal`` — a dragon read as a person.
    """
    if takes_no_space(entity):
        return 0
    return TIER_SPACE.get(_size_source(entity), TIER_SPACE["normal"])


def area_budget(area_node, default: int = DEFAULT_MAX_OCCUPANCY) -> int:
    """The occupancy budget declared by an area node, or *default*.

    A non-positive authored value is treated as "no limit" rather than as "nobody
    may enter", because ``0`` is the obvious way to write "unbounded" in an
    editor and refusing every arrival on that reading would be a nasty surprise.
    """
    props = (getattr(area_node, "properties", None) or {}) if area_node else {}
    for key in AREA_BUDGET_PROPERTIES:
        if key not in props:
            continue
        try:
            value = int(props[key])
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return default


def normalize_area_id(area, graph) -> str:
    """Resolve an area given as a display name or an id to the **node id**.

    Every entry point funnels through here so a caller can say
    ``world.area_occupancy("Kitchen")`` and still get an id-keyed count.
    """
    if area in (None, ""):
        return ""
    if graph is not None:
        slug = f"area_{str(area).lower().replace(' ', '_')}"
        for candidate in (str(area), f"area_{area}", slug):
            try:
                node = graph.get_node(candidate)
            except Exception:
                node = None
            if node is not None and getattr(node, "type", None) == "area":
                return candidate
        try:
            for node in graph.nodes.values():
                if getattr(node, "type", None) == "area" and node.name == area:
                    return node.id
        except Exception:
            pass
    return str(area)


def _entity_in_area(entity, area_id, graph) -> bool:
    """True when *entity* is standing in *area_id*.

    *area_id* is always an area **node id** here — the callers resolve it first.
    A ``Player`` knows its own room by display name (``current_area``), so that
    is resolved through the graph and compared as an id. A node reached *via* the
    area's ``in`` edges is standing there by definition, but it is recognised by
    being a ``Node`` with type ``character``, never by a loose attribute test that
    a Player could satisfy too.
    """
    if not area_id:
        return False
    resolved = _area_id_of(entity, graph)
    return bool(resolved) and resolved == str(area_id)


def _area_id_of(entity, graph) -> str:
    """Resolve an entity's ``current_area`` (a display name) to the area node id.

    ``current_area`` is prose — "Kitchen", "Blizzard Forest Clearing" — while every
    graph edge is keyed by the slug ``area_kitchen``. So this tries the raw name,
    then the slug form, then a by-name scan as a last resort; falling back to the
    raw name when nothing matches keeps a character with an unslotted area
    countable rather than invisible.
    """
    name = getattr(entity, "current_area", None)
    if not name:
        return ""
    if graph is not None:
        slug = f"area_{str(name).lower().replace(' ', '_')}"
        for candidate in (name, f"area_{name}", slug):
            try:
                if graph.get_node(candidate) is not None:
                    return candidate
            except Exception:
                continue
        try:
            for node in graph.nodes.values():
                if getattr(node, "type", None) == "area" and node.name == name:
                    return node.id
        except Exception:
            pass
    return str(name)


def occupants(area_id, players=None, graph=None, include_dead: bool = False):
    """Every entity standing in *area_id*, as ``(name, entity)`` pairs.

    ``entity`` is the live ``Player`` where one exists, and the graph **node**
    where the area only has graph residents — never ``None``, because both carry
    a size and a tag list and a missing one would silently read as `normal`.
    The dead are excluded by default: a corpse on the floor is not occupying the
    room.
    """
    area_id = normalize_area_id(area_id, graph)
    found = {}
    for key, player in (players or {}).items():
        if not include_dead and getattr(player, "state", "") == "dead":
            continue
        if _entity_in_area(player, area_id, graph):
            found[str(getattr(player, "name", key))] = player
    if graph is not None:
        try:
            for edge in graph.get_edges_for_target(area_id, "in"):
                node = graph.get_node(edge.source)
                if node is None or getattr(node, "type", None) != "character":
                    continue
                if not include_dead:
                    known = players.get(node.name) if players else None
                    if known is not None and getattr(known, "state", "") == "dead":
                        continue
                # Hand back the NODE, not None. A graph-only resident still has a
                # size and a tag list on its properties, and returning None would
                # make every such occupant cost a default `normal` — a dragon
                # read as a person, which is the bug this module exists to stop.
                found.setdefault(str(node.name), node)
        except Exception as e:
            logger.debug("occupancy: graph walk failed for %s: %s", area_id, e)
    return sorted(found.items())


def occupancy_used(area_id, players=None, graph=None, include_dead: bool = False) -> int:
    """Total room-budget units currently taken up in *area_id*."""
    return sum(space_of(entity) for _name, entity in occupants(
        area_id, players, graph, include_dead))


def occupancy_report(area_id, players=None, graph=None, include_dead: bool = False,
                     area_node=None) -> dict:
    """Everything a caller (or the UI) needs to explain how full a room is.

    ``full`` is True at *or over* budget — an area holding a dragon it was never
    sized for is over capacity, and reporting that as "full" is more useful than
    a separate concept the caller has to invent.
    """
    area_id = normalize_area_id(area_id, graph)
    if area_node is None and graph is not None and area_id:
        try:
            area_node = graph.get_node(area_id)
        except Exception:
            area_node = None
    budget = area_budget(area_node)
    present = occupants(area_id, players, graph, include_dead)
    used = sum(space_of(entity) for _name, entity in present)
    return {
        "area": area_id,
        "budget": budget,
        "used": used,
        "remaining": max(0, budget - used),
        "full": used >= budget,
        "headcount": len(present),
        "occupants": [
            {"name": name, "size": _size_source(entity),
             "space": space_of(entity),
             "intangible": takes_no_space(entity)}
            for name, entity in present
        ],
    }


def fits(area_id, entity, players=None, graph=None, area_node=None,
         include_dead: bool = False) -> bool:
    """Would *entity* fit in *area_id* right now?

    Intangible entities always fit — that is the whole point of the zero-space
    flag. An entity is also always allowed to be the *only* thing in a room, so a
    leviathan is never refused a hall; what is refused is the leviathan arriving
    into a room that is already full.
    """
    if takes_no_space(entity):
        return True
    area_id = normalize_area_id(area_id, graph)
    if area_node is None and graph is not None and area_id:
        try:
            area_node = graph.get_node(area_id)
        except Exception:
            area_node = None
    budget = area_budget(area_node)
    used = occupancy_used(area_id, players, graph, include_dead)
    if used <= 0:
        return True
    return used + space_of(entity) <= budget


#: Prose for how full a room is, as a fraction of its budget. Deliberately
#: coarse — the reader wants "cramped" vs "empty", not a percentage — and the
#: over-capacity band is a separate phrase because "the room cannot hold what is
#: in it" is a scene, not a percentage.
_CROWDED_AT = 0.75


def describe_occupancy(report: dict) -> str:
    """One clause describing how full an area is, or "" if it is not worth saying.

    Empty rooms say nothing at all. That matters: a phrase on every area in a
    world trains the reader to skip the sentence, and the one time it does fire is
    the time it means something.
    """
    used = int(report.get("used", 0))
    budget = int(report.get("budget", 0) or 0)
    if used <= 0:
        return ""
    if budget <= 0 or used > budget:
        # Over capacity — say what is in there rather than abstracting it.
        biggest = sorted(
            (o for o in report.get("occupants", []) if o.get("space", 0) > 0),
            key=lambda o: -o["space"],
        )
        if biggest and biggest[0]["size"] in ("giant", "titanic"):
            return f"The room cannot properly hold the {biggest[0]['size']} {biggest[0]['name']}."
        return "The room is packed past its limits."
    fraction = used / budget
    if fraction >= 1.0:
        return "The room is full."
    if fraction >= _CROWDED_AT:
        return "The room is crowded."
    if fraction >= 0.4:
        return "The room is busy."
    return ""
