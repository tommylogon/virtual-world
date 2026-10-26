"""Per-agent fog of war, and what a character is told (task-499).

`player.known` already exists and `engine/room_perception.py` already gates on it
- a way or area in the viewer's known set is visible even when hidden. **Nothing
ever wrote to it.** That is the whole gap: the gate is sound and has no key.

So this module supplies the three halves the task names:

* **reveal** - walking into a place, examining it, or seeing down a sightline
  (:mod:`engine.beyond_visibility`) teaches the area;
* **teach** - a map's use/read teaches the known entries through that same
  ``known`` registry, so a map and a walk end up in one place rather than two;
* **fog** - what a character may be *told*, which is the part that is easy to get
  wrong. :func:`only_known` is the filter agent prompts and map views go through,
  and it is a filter on names, not a redaction of a prompt string.

**The ids and the names both matter, and the registry stores both.** The
perception gate matches on ``way.id``, ``area_name`` and a derived id guess,
because hand-authored ways predate the id convention. A known set holding only one
of those forms would leak through the other two, so :meth:`Known.reveal` writes
every form it can derive and :meth:`Known.has` accepts any of them. One
authoritative store, no second copy to drift.

**Unknown is not the same as absent.** :meth:`Known.has` returning False means
"not known", not "does not exist" - so a prompt filter can only ever *withhold*,
never assert. That is the honest bound: a character can be told less than the
player knows, and never more.

@module fog
@contributes the per-character known set, reveal verbs, and map teaching
@docs docs/virtualWorld/Gameplay/Per-Agent Knowledge (Fog of War).md
"""

from __future__ import annotations

import re
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


def _upgrade_supporting_beliefs(player, forms: Iterable[str]) -> List[Dict[str, Any]]:
    """Link newly learned place forms to any belief memories they support (task-467).

    When a character learns a place from a map, a spoken direction, or walking in,
    only a belief memory that actually names that place is upgraded (`upgraded_to_known`
    and `confidence = 1.0`). Unrelated beliefs stay untouched.
    """
    memories = getattr(player, "memories", None) or []
    if not memories:
        return []
    clean_forms = [str(f).strip() for f in forms if str(f or "").strip()]
    if not clean_forms:
        return []
    upgraded: List[Dict[str, Any]] = []
    for mem in memories:
        if not isinstance(mem, dict):
            continue
        mtype = str(mem.get("type") or "").lower()
        mcat = str(mem.get("category") or "").lower()
        tags = {str(t).lower() for t in (mem.get("tags") or [])}
        if mtype != "belief" and mcat != "belief" and "belief" not in tags:
            continue
        text = str(mem.get("text") or "").lower()
        matched_form = None
        for form in clean_forms:
            fl = form.lower()
            if fl in tags or re.search(r"(?<!\w)" + re.escape(fl) + r"(?!\w)", text):
                matched_form = form
                break
        if matched_form:
            mem["upgraded_to_known"] = matched_form
            mem["confidence"] = 1.0
            upgraded.append(mem)
    return upgraded


def resolve_known_area(graph, ref: Any) -> Optional[Any]:
    """Resolve an area id or display name against *graph* without duplicating lookup rules.

    Delegates to :func:`engine.room_perception.resolve_area` when *graph* exposes
    ``get_node``, and falls back to scanning ``graph.nodes`` for lightweight test
    stubs.
    """
    if graph is None or not ref:
        return None
    text = str(ref).strip()
    if not text:
        return None
    if callable(getattr(graph, "get_node", None)):
        try:
            from engine.room_perception import resolve_area
            node = resolve_area(graph, text)
            if node is not None:
                return node
        except Exception:
            pass
    nodes = getattr(graph, "nodes", None) or {}
    text_lower = text.lower()
    for node in nodes.values():
        if getattr(node, "type", None) != "area":
            continue
        nid = str(getattr(node, "id", "") or "")
        nname = str(getattr(node, "name", "") or "")
        if nid == text or nname == text or nid.lower() == text_lower or nname.lower() == text_lower:
            return node
    return None


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
        if added:
            _upgrade_supporting_beliefs(self.player, added)
        return added

    def forget(self, *candidates: Any) -> List[str]:
        """Drop what is known about these forms. For a rewrite, not a mechanic.

        A **string** drops exactly that string. A **node** drops every form
        derived from it, which is the only way to remove a place completely -
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


def reveal_examined(player, target, *, graph=None, from_area_id=None) -> List[str]:
    """Examining a thing teaches the place it is in or points at.

    A way teaches the area on the far side, because a way is only ever described
    in terms of where it goes. An area teaches itself. ``graph`` lets a caller
    that already holds the graph (the examine verb) pass it in, so a way still
    resolves its far area when the player object carries no graph back-reference.
    ``from_area_id`` is the room the viewer is examining *from*; without it a way
    with two area edges resolves to whichever edge came first, which can be the
    room the viewer is already standing in.
    """
    if target is None:
        return []
    known = Known(player)
    if getattr(target, "type", None) == "way":
        from engine.beyond_visibility import _area_across

        source = graph if graph is not None else _graph_of(player)
        far = _area_across(source, target, from_area_id)
        if far:
            # `_area_across` returns an id; resolve it so the name is written too.
            getter = getattr(source, "get_node", None)
            far = (getter(far) if callable(getter) else None) or far
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
    path is ``player.known`` - the same registry a walk writes. Two paths would
    mean two places to look and one of them would be forgotten.

    *areas* is the chart's own list when the item declares one, and otherwise
    every area in the world, which is what an item with no list means: it is a map
    of the place you are in. A map with an explicit empty list teaches nothing,
    which is different from a map with no list and is the difference between a
    blank prop and an absent one.
    """
    props = (getattr(map_item, "properties", None) or {}) if map_item else {}
    known = Known(player)
    source = graph if graph is not None else _graph_of(player)
    # `in`, not a truthiness test: an explicit empty chart is a map of nowhere and
    # must teach nothing, while an ABSENT chart is a map of wherever you are. The
    # difference is a blank prop and an absent one, and a truthiness test reads
    # both as "no list" and hands out the whole world.
    if areas is not None:
        candidates: List[Any] = list(areas)
    elif "charted_areas" in props:
        candidates = list(props.get("charted_areas") or [])
    else:
        candidates = [n for n in (getattr(source, "nodes", {}) or {}).values()
                      if getattr(n, "type", None) == "area"]

    added: List[str] = []
    places: List[str] = []
    upgraded: List[str] = []
    for candidate in candidates:
        if isinstance(candidate, str):
            text = candidate.strip()
            candidate = resolve_known_area(source, text) or text
        node_id = getattr(candidate, "id", None)
        if node_id and str(node_id) not in places:
            places.append(str(node_id))
        elif node_id is None and str(candidate) not in places:
            # A chart entry that resolves to nothing still taught that literal
            # string, so it belongs in the count rather than vanishing from it.
            places.append(str(candidate))
        forms = _forms(candidate)
        added.extend(known.reveal(candidate))
        for m in _upgrade_supporting_beliefs(player, forms):
            u = m.get("upgraded_to_known")
            if u and u not in upgraded:
                upgraded.append(u)
    return {"taught": added, "places": places, "count": len(places),
            "entries": len(added), "total_known": len(known),
            "upgraded_beliefs": upgraded}


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
    tell "you have not been there" from "there is nothing there" - and fog of war
    that looks like empty space is a fog of war nobody explores.
    """
    known = Known(player)
    seen: Set[str] = set()
    fog: Set[str] = set()
    for area_id in area_ids or ():
        text = str(area_id)
        if not text:
            continue
        # A set, so a duplicated cell in the world list is drawn once - a map
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


def materialize_frontier(gs, player, area_or_id: Any, *,
                         heading: Optional[str] = None) -> List[str]:
    """Generate content on discovery when entering or stepping toward an unmade frontier (task-467).

    Uses the task-398 / task-496 generation contract (`generation.apply_patch`,
    `generation_recipes`, and `world_compile.compile_grid` with task-9's
    `LibraryIndex`) so frontier discovery never invents a second world format:
    1. Unmade child scopes attached to the current area (`child_scope_id`,
       `entry_area_id`, or a grid placement on the current or heading-adjacent cell).
    2. Uncompiled painted frontier cells on the current scope's grid in direction
       *heading* when the cell has paint in `world_scopes` that has not yet been
       compiled into an area node.
    Every newly materialized entry area is revealed in fog for *player* only.
    """
    graph = getattr(gs, "graph", None)
    manifest = getattr(gs, "world_scopes", None)
    if graph is None or not isinstance(manifest, dict) or not manifest:
        return []
    area_node = resolve_known_area(graph, area_or_id)
    if area_node is None:
        return []

    from pathlib import Path
    from engine import generation, generation_recipes, world_compile, world_grid

    props = getattr(area_node, "properties", None) or {}
    scope_id = props.get("world_scope_id")
    cell = props.get("cell") if isinstance(props.get("cell"), dict) else None
    cx = cell.get("x") if cell is not None else None
    cy = cell.get("y") if cell is not None else None

    adj_cell = None
    if isinstance(cx, int) and isinstance(cy, int) and heading:
        delta = world_compile.DIRECTIONS.get(str(heading).strip().lower())
        if delta:
            adj_cell = (cx + delta[0], cy + delta[1])

    # Collect (target_scope_id, allow_regenerate, entry_override) candidates
    candidates: List[ tuple ] = []
    seen_scopes: Set[str] = set()

    def _queue(sid: Optional[str], allow_regen: bool = False, entry_id: Optional[str] = None):
        if not sid or sid in seen_scopes or sid not in manifest:
            return
        seen_scopes.add(sid)
        candidates.append((sid, allow_regen, entry_id))

    # (a) Direct child_scope_id on the area node
    child_sid = props.get("child_scope_id")
    if child_sid and manifest.get(child_sid, {}).get("state", generation.UNMADE) == generation.UNMADE:
        _queue(str(child_sid), False, area_node.id)

    # (b) Any unmade scope whose entry_area_id names this area
    for sid, srec in list(manifest.items()):
        if not isinstance(srec, dict):
            continue
        if srec.get("state", generation.UNMADE) != generation.UNMADE:
            continue
        if srec.get("entry_area_id") in (area_node.id, area_node.name):
            _queue(str(sid), False, area_node.id)

    # (c) Parent scope placements or uncompiled painted frontier cells
    if scope_id and scope_id in manifest:
        parent_rec = manifest[scope_id]
        target_cells = {(cx, cy)} if (isinstance(cx, int) and isinstance(cy, int)) else set()
        if adj_cell is not None:
            target_cells.add(adj_cell)
        for cid, pos in (parent_rec.get("placements") or {}).items():
            if not isinstance(pos, dict):
                continue
            pcell = (pos.get("x"), pos.get("y"))
            if (pcell in target_cells or pos.get("area_id") == area_node.id) and cid in manifest:
                crec = manifest[cid]
                if crec.get("state", generation.UNMADE) == generation.UNMADE:
                    _queue(str(cid), False, area_node.id)

        # Check if adj_cell on parent_rec is painted but has no compiled area node yet
        if adj_cell is not None and world_grid.has_grid(parent_rec):
            ax, ay = adj_cell
            if world_grid.in_bounds(parent_rec, ax, ay):
                key = world_grid.cell_key(ax, ay)
                layers = parent_rec.get("layers") or {}
                has_paint = bool((layers.get("biome") or {}).get(key) or (layers.get("road") or {}).get(key))
                if has_paint:
                    already_compiled = any(
                        getattr(n, "type", None) == "area"
                        and (getattr(n, "properties", None) or {}).get("world_scope_id") == scope_id
                        and (
                            (getattr(n, "properties", None) or {}).get("cell") == {"x": ax, "y": ay}
                            or {"x": ax, "y": ay} in ((getattr(n, "properties", None) or {}).get("cells") or [])
                        )
                        for n in graph.nodes.values()
                    )
                    if not already_compiled:
                        _queue(str(scope_id), True, None)

    if not candidates:
        return []

    try:
        from engine.population import LibraryIndex
        root_dir = Path(__file__).resolve().parent.parent
        index = LibraryIndex.from_directory(root_dir / "data" / "library" / "items")
    except Exception:
        index = None

    tick = int(getattr(gs, "time_ticks", 0) or getattr(gs, "turn_number", 0) or 0)
    materialized_areas: List[str] = []
    pre_existing_areas = {
        n.id for n in graph.nodes.values() if getattr(n, "type", None) == "area"
    }

    for sid, allow_regen, entry_id in candidates:
        srec = manifest.get(sid) or {}
        seed = str(srec.get("seed") or sid)
        patch = None
        try:
            if srec.get("recipe"):
                recipe_fn = generation_recipes.get_recipe(str(srec["recipe"]))
                if recipe_fn is not None and index is not None:
                    patch = recipe_fn(
                        sid, seed=seed, index=index,
                        entry_area_id=entry_id or srec.get("entry_area_id") or area_node.id,
                        tick=tick,
                    )
            elif world_grid.has_grid(srec):
                patch = world_compile.compile_grid(
                    manifest, sid,
                    region_merge=bool(srec.get("region_merge", False)),
                    seed=seed, tick=tick, graph=graph,
                    spawn_index=index,
                )
            if patch is None:
                continue
            report = generation.apply_patch(
                graph, manifest, patch, allow_regenerate=allow_regen,
            )
            new_ids = [
                aid for aid in (report.area_ids or [])
                if aid not in pre_existing_areas or not allow_regen
            ]
            if not new_ids and report.area_ids:
                new_ids = list(report.area_ids)
            materialized_areas.extend(new_ids)
            if player is not None:
                entry_aid = (new_ids[0] if new_ids else None) or manifest.get(sid, {}).get("entry_area_id")
                if adj_cell is not None:
                    for aid in new_ids:
                        anode = graph.get_node(aid)
                        aprops = getattr(anode, "properties", None) or {}
                        if aprops.get("cell") == {"x": adj_cell[0], "y": adj_cell[1]}:
                            entry_aid = aid
                            break
                if entry_aid:
                    reveal_area(player, graph.get_node(entry_aid) or entry_aid)
        except Exception:
            continue

    return materialized_areas
