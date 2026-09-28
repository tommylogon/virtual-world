"""Per-agent fog of war, and what a character is told (task-499).

`player.known` already exists and `engine/room_perception.py` already gates on it
— a way or area in the viewer's known set is visible even when hidden. **Nothing
ever wrote to it.** That is the whole gap: the gate is sound and has no key.

So this module supplies the three halves the task names:

* **reveal** — walking into a place, examining it, or seeing down a sightline
  (:mod:`engine.beyond_visibility`) teaches the area;
* **teach** — a map's use/read teaches the known entries through that same
  ``known`` registry, so a map and a walk end up in one place rather than two;
* **fog** — what a character may be *told*, which is the part that is easy to get
  wrong. :func:`only_known` is the filter agent prompts and map views go through,
  and it is a filter on names, not a redaction of a prompt string.

**The ids and the names both matter, and the registry stores both.** The
perception gate matches on ``way.id``, ``area_name`` and a derived id guess,
because hand-authored ways predate the id convention. A known set holding only one
of those forms would leak through the other two, so :meth:`Known.reveal` writes
every form it can derive and :meth:`Known.has` accepts any of them. One
authoritative store, no second copy to drift.

**Unknown is not the same as absent.** :meth:`Known.has` returning False means
"not known", not "does not exist" — so a prompt filter can only ever *withhold*,
never assert. That is the honest bound: a character can be told less than the
player knows, and never more.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set


def _registry(player) -> List[str]:
    """The player's known list, created on first use.

    `player.known` is a plain list on the `Player` object today, and it is
    serialised with it. Replacing it with a set here would silently change the
    save format, so it stays a list and is de-duplicated on write instead.
    """
    known = getattr(player, "known", None)
    if known is None:
        known = []
        try:
            player.known = known
        except AttributeError:
            return []
    return known


def _add(known: List[str], value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if any(str(existing).strip() == text for existing in known):
        return False
    known.append(text)
    return True


class Known:
    """One character's known set, over an area or scope.

    Constructed per character per call; it holds no state of its own, so two
    characters can never share a set by accident.
    """

    def __init__(self, player):
        self.player = player
        self.known = _registry(player)

    # ── reading ──────────────────────────────────────────────────────────

    def has(self, *candidates: Any) -> bool:
        """True when the character knows **any** of the given forms.

        Accepts an area id, an area name, a way node, or an area node, because the
        three callers that need this (perception, prompts, the map view) each hold
        a different one and a mismatch must not read as "unknown".
        """
        for candidate in candidates:
            if candidate is None:
                continue
            if isinstance(candidate, str):
                if _add_present(self.known, candidate):
                    return True
                continue
            node_id = getattr(candidate, "id", None)
            name = getattr(candidate, "name", None)
            if _add_present(self.known, node_id) or _add_present(self.known, name):
                return True
        return False

    def entries(self) -> List[str]:
        return [str(k) for k in self.known]

    def __len__(self) -> int:
        return len(self.known)

    def __contains__(self, value) -> bool:
        return self.has(value)

    # ── writing ──────────────────────────────────────────────────────────

    def reveal(self, *candidates: Any) -> List[str]:
        """Teach everything derivable from these forms. Returns what was new.

        Writes the area id *and* the area name, because the perception gate
        matches on either and a set holding one form leaks through the other.
        """
        added: List[str] = []
        for candidate in candidates:
            for form in _forms(candidate):
                if _add(self.known, form):
                    added.append(form)
        return added

    def forget(self, *candidates: Any) -> List[str]:
        """Drop what is known about these forms. For a rewrite, not a mechanic.

        A **string** drops exactly that string. A **node** drops every form
        derived from it, which is the only way to remove a place completely —
        knowing the id and the name are two entries, and removing one leaves the
        perception gate still matching on the other.
        """
        dropped = []
        for candidate in candidates:
            for form in _forms(candidate):
                if form in [str(k) for k in self.known]:
                    self.known[:] = [k for k in self.known
                                     if str(k) != form]
                    dropped.append(form)
        return dropped


def _add_present(known, value) -> bool:
    text = str(value or "").strip()
    return bool(text) and any(str(k).strip() == text for k in known)


def _forms(candidate: Any) -> List[str]:
    """Every spelling of *candidate* worth storing."""
    if candidate is None:
        return []
    if isinstance(candidate, str):
        return [candidate.strip()] if candidate.strip() else []
    out = []
    for attr in ("id", "name"):
        value = getattr(candidate, attr, None)
        if value:
            out.append(str(value))
    props = getattr(candidate, "properties", None)
    if isinstance(props, dict):
        for key in ("area_from_id", "area_to_id", "world_scope_id"):
            value = props.get(key)
            if value:
                out.append(str(value))
    return [v for v in dict.fromkeys(out) if v]


# ── the reveal verbs ───────────────────────────────────────────────────────


def reveal_area(player, area_node) -> List[str]:
    """Standing in a place teaches it. The walk path."""
    if area_node is None:
        return []
    return Known(player).reveal(area_node)


def reveal_examined(player, target) -> List[str]:
    """Examining a thing teaches the place it is in or points at.

    A way teaches the area on the far side, because a way is only ever described
    in terms of where it goes. An area teaches itself.
    """
    if target is None:
        return []
    known = Known(player)
    if getattr(target, "type", None) == "way":
        from engine.beyond_visibility import _area_across

        far = _area_across(_graph_of(player), target, None)
        return known.reveal(far)
    return known.reveal(target)


def reveal_sightline(player, graph, run) -> List[str]:
    """Seeing down a corridor teaches the rooms at the end of it (task-498).

    Reuses the sightline rather than re-deciding what is visible: one place that
    knows how far you can see, so the map and the prose cannot disagree.
    """
    if not run:
        return []
    known = Known(player)
    added = []
    for step in run:
        added.extend(known.reveal(step.get("area_id"), step.get("area_name")))
    return added


def _graph_of(player):
    """The graph a player is attached to, if it exposes one."""
    manager = getattr(player, "player_manager", None)
    for holder in (manager, getattr(manager, "gs", None), player):
        graph = getattr(holder, "graph", None)
        if graph is not None and hasattr(graph, "nodes"):
            return graph
    return _EMPTY_GRAPH


class _Empty:
    nodes = {}
    edges = []

    def get_edges_for_source(self, *_args, **_kwargs):
        return []


_EMPTY_GRAPH = _Empty()


# ── a map teaches ──────────────────────────────────────────────────────────


def teach_from_map(player, map_item, *, graph=None, areas=None) -> Dict[str, Any]:
    """A map's use/read teaches the areas it charts.

    The task's wording is "via the existing teach path", and the existing teach
    path is ``player.known`` — the same registry a walk writes. Two paths would
    mean two places to look and one of them would be forgotten.

    *areas* is the chart's own list when the item declares one, and otherwise
    every area in the world, which is what an item with no list means: it is a map
    of the place you are in. A map with an explicit empty list teaches nothing,
    which is different from a map with no list and is the difference between a
    blank prop and an absent one.
    """
    props = (getattr(map_item, "properties", None) or {}) if map_item else {}
    known = Known(player)
    # `in`, not a truthiness test: an explicit empty chart is a map of nowhere and
    # must teach nothing, while an ABSENT chart is a map of wherever you are. The
    # difference is a blank prop and an absent one, and a truthiness test reads
    # both as "no list" and hands out the whole world.
    if areas is not None:
        candidates: List[Any] = list(areas)
    elif "charted_areas" in props:
        candidates = list(props.get("charted_areas") or [])
    else:
        source = graph if graph is not None else _graph_of(player)
        candidates = [n for n in (getattr(source, "nodes", {}) or {}).values()
                      if getattr(n, "type", None) == "area"]

    # A chart entry is usually an area id, but a hand-authored one is often a
    # display name. Resolving a name to its node means both end up teaching the
    # *same* set of forms, so a map that charts "Room 1" and a walk that reaches
    # `area_1` agree instead of holding two half-entries.
    source = graph if graph is not None else _graph_of(player)
    by_name: Dict[str, Any] = {}
    by_id: Dict[str, Any] = {}
    for node in (getattr(source, "nodes", {}) or {}).values():
        if getattr(node, "type", None) != "area":
            continue
        node_id = getattr(node, "id", None)
        name = getattr(node, "name", None)
        if node_id:
            by_id[str(node_id)] = node
        if name:
            by_name.setdefault(str(name), node)

    added: List[str] = []
    places: List[str] = []
    for candidate in candidates:
        if isinstance(candidate, str):
            text = candidate.strip()
            candidate = by_id.get(text) or by_name.get(text, text)
        node_id = getattr(candidate, "id", None)
        if node_id and str(node_id) not in places:
            places.append(str(node_id))
        elif node_id is None and str(candidate) not in places:
            # A chart entry that resolves to nothing still taught that literal
            # string, so it belongs in the count rather than vanishing from it.
            places.append(str(candidate))
        added.extend(known.reveal(candidate))
    return {"taught": added, "places": places, "count": len(places),
            "entries": len(added), "total_known": len(known)}


# ── what a character may be told ────────────────────────────────────────────


def only_known(player, names: Iterable[str]) -> List[str]:
    """The subset of *names* this character knows.

    The honesty boundary, and deliberately the **only** place the world is filtered
    for a prompt. A filter on a list is auditable; a filter on a rendered prompt
    string is not, and a prompt that forgot to call this is how an unaware agent
    gets told about a room it has never been in.
    """
    known = Known(player)
    return [str(n) for n in names or () if known.has(str(n))]


def fog_view(player, area_ids: Iterable[str], *, zones: bool = False) -> Dict[str, Any]:
    """The map payload: what is drawn, and what is fog.

    Unknown entries are **present but marked**, not omitted. An omitted cell is
    indistinguishable from a cell that was never painted, so the map could not
    tell "you have not been there" from "there is nothing there" — and fog of war
    that looks like empty space is a fog of war nobody explores.
    """
    known = Known(player)
    seen: Set[str] = set()
    fog: Set[str] = set()
    for area_id in area_ids or ():
        text = str(area_id)
        if not text:
            continue
        # A set, so a duplicated cell in the world list is drawn once — a map
        # that lists the same cell twice is a map with a bug in it, and a caller
        # counting `known_count` to draw a legend would be off.
        (seen if known.has(text) else fog).add(text)
    view: Dict[str, Any] = {
        "known": sorted(seen),
        "fog": sorted(fog),
        "known_count": len(seen),
        "fog_count": len(fog),
    }
    if zones:
        view["known_zones"] = sorted({
            str(form) for form in known.entries()
            if str(form).startswith(("zone_", "deep_woods", "west_woods", "world"))
        })
    return view


def unknown_are_hidden(player, area_name: str) -> bool:
    """Whether an unvisited area should be withheld from a prompt entirely.

    Kept as a named predicate so the call sites read as a decision rather than an
    `if not in known(...)`, and so there is exactly one place to change it if the
    rule ever becomes "a rough bearing is allowed".
    """
    return not Known(player).has(area_name)
