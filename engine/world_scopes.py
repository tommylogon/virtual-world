"""World scope manifest and scoped projections (task-397).

A *scope* is a durable grouping/load boundary over the existing flat
area/way/item graph. Leaf areas stay normal ``area`` nodes; scopes never add
fake area nodes for buildings/floors/continents.

The manifest is a plain dict ``{scope_id: record}`` persisted on the world as
``world_scopes``. Everything here is pure over (manifest, graph, players) so it
is easily testable and safe for route handlers to call.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from engine import world_grid
from graph import EDGE_CONNECTION, Edge, Node

SPATIAL_TYPES = {"in", "on", "under", "behind", "beside", "at"}

DEFAULT_KIND = "scope"
DEFAULT_STATE = "materialized"


def normalise_manifest(raw) -> Dict[str, dict]:
    """Return a cleaned ``{id: record}`` manifest; tolerates legacy/missing data."""
    manifest: Dict[str, dict] = {}
    if not isinstance(raw, dict):
        return manifest
    for scope_id, record in raw.items():
        if not isinstance(record, dict):
            continue
        rec = dict(record)
        rec["id"] = str(rec.get("id") or scope_id)
        rec["kind"] = rec.get("kind") or DEFAULT_KIND
        rec["name"] = rec.get("name") or rec["id"]
        rec["parent_id"] = rec.get("parent_id")
        rec["children"] = [str(c) for c in (rec.get("children") or [])]
        rec["area_ids"] = [str(a) for a in (rec.get("area_ids") or [])]
        rec["state"] = rec.get("state") or DEFAULT_STATE
        # task-495: canonicalise any WorldPainter grid fields. A scope that
        # never had a grid is returned unchanged (no empty containers added).
        world_grid.normalise_grid(rec)
        manifest[str(scope_id)] = rec
    return manifest


def root_scope_ids(manifest: Dict[str, dict]) -> List[str]:
    """Scopes with no parent. Order is stable (manifest insertion order)."""
    return [sid for sid, rec in manifest.items() if not rec.get("parent_id")]


def direct_child_ids(manifest: Dict[str, dict], scope_id: str) -> List[str]:
    """Declared children plus any record whose ``parent_id`` is this scope."""
    out: List[str] = []
    seen = set()

    def add(sid: str):
        if sid in manifest and sid not in seen:
            seen.add(sid)
            out.append(sid)

    for sid in manifest.get(scope_id, {}).get("children", []):
        add(sid)
    for sid, rec in manifest.items():
        if rec.get("parent_id") == scope_id:
            add(sid)
    return out


def area_ids_in_scope(manifest: Dict[str, dict], graph, scope_id: str,
                      _seen: Optional[set] = None) -> set:
    """Leaf area ids belonging to a scope, including descendants."""
    _seen = _seen or set()
    if scope_id in _seen:
        return set()
    _seen.add(scope_id)

    areas = set(manifest.get(scope_id, {}).get("area_ids", []))
    for node_id, node in graph.nodes.items():
        if getattr(node, "type", "") == "area":
            if node.properties.get("world_scope_id") == scope_id:
                areas.add(node_id)
    for child in direct_child_ids(manifest, scope_id):
        areas |= area_ids_in_scope(manifest, graph, child, _seen)
    return areas


def own_area_ids(graph, scope_id: str) -> set:
    """Leaf area ids belonging to *exactly* this scope, ignoring descendants.

    The graph view loads a scope's **own level** (task-397 revision): a parent
    shows its own painted cells — a placed child is a single feature cell, not
    its whole interior. Use :func:`area_ids_in_scope` when the subtree is wanted.
    """
    return {node_id for node_id, node in graph.nodes.items()
            if getattr(node, "type", "") == "area"
            and (getattr(node, "properties", {}) or {}).get("world_scope_id") == scope_id}


def assign_area_membership(manifest: Dict[str, dict], area_id: str,
                           new_scope: Optional[str],
                           previous_scope: Optional[str] = None) -> str:
    """Mirror an area's scope change in the manifest (task-539).

    ``world_scope_id`` on the node is the single source of truth; a scope record's
    ``area_ids`` list is the denormalized mirror that :func:`area_ids_in_scope`
    also reads, so both ends have to move together or a moved area keeps showing
    up in the old scope's count and canvas. This only touches the manifest — the
    caller owns the node side, because only it knows whether the area exists and
    is hand-authored enough to move.

    Membership is not map placement. An area that was parked on a cell of the
    scope it is leaving is *released* (its ``area_placements`` entry is dropped),
    because that cell reservation belongs to the scope that owned the area; the
    caller clears the node's ``cell``/``x``/``y`` to match. A placement in
    ``new_scope`` itself is left alone, so re-assigning an area to the scope it
    already sits on is a no-op.

    Returns ``"assigned"``, ``"removed"`` or ``"unchanged"``.
    """
    area_id = str(area_id)
    new_scope = str(new_scope) if new_scope else None
    previous_scope = str(previous_scope) if previous_scope else None
    if new_scope and new_scope not in manifest:
        raise ValueError(f"no such scope {new_scope!r}")

    if new_scope == previous_scope:
        return "unchanged"

    if new_scope:
        ids = manifest[new_scope].setdefault("area_ids", [])
        if area_id not in ids:
            ids.append(area_id)
    if previous_scope and previous_scope in manifest:
        record = manifest[previous_scope]
        ids = record.get("area_ids")
        if isinstance(ids, list) and area_id in ids:
            ids.remove(area_id)
        # The cell it was parked on lived in the scope it just left. Leaving the
        # reservation behind would have that grid hold a cell for an area that is
        # no longer its member (and could block generate from ever using it).
        world_grid.unplace_area(manifest, previous_scope, area_id)
        if not record.get("area_placements"):
            record.pop("area_placements", None)

    return "assigned" if new_scope else "removed"


def _area_name_to_id(graph) -> Dict[str, str]:
    return {node.name: node_id for node_id, node in graph.nodes.items()
            if getattr(node, "type", "") == "area"}


def _items_in_area(graph, area_id: str) -> List[str]:
    out = []
    for edge in graph.get_edges_for_target(area_id):
        if edge.type in SPATIAL_TYPES and graph.get_node(edge.source):
            out.append(edge.source)
    return out


def spatial_item_nodes(graph, container_id) -> List:
    """Item *nodes* a container holds by any spatial relation (task-551).

    The one definition of "what can be reached in here", so the background
    simulation and a route handler asking the same question get the same answer.
    It used to be spelled out twice — as a class attribute in
    `background_simulation.REACHABLE_RELATIONS` and as `_SPATIAL_TYPES` in
    `routes/population_ops.py` — and the tiers drifting apart on it is how
    `engine/relief.py` ended up unable to tell whether a fixture was in reach.
    """
    out = []
    if graph is None or not container_id:
        return out
    for edge in graph.get_edges_for_target(container_id):
        if edge.type not in SPATIAL_TYPES:
            continue
        node = graph.get_node(edge.source)
        if node is not None and getattr(node, "type", None) == "item":
            out.append(node)
    return out


def characters_in_areas(graph, players, area_ids: Iterable[str]) -> int:
    area_ids = set(area_ids)
    name_to_id = _area_name_to_id(graph)
    count = 0
    for player in (players or {}).values():
        if name_to_id.get(getattr(player, "current_area", None)) in area_ids:
            count += 1
    return count


def item_count_in_areas(graph, area_ids: Iterable[str]) -> int:
    return sum(len(_items_in_area(graph, aid)) for aid in set(area_ids))


def _endpoint(props, id_key: str, name_key: str, name_to_id: Dict[str, str]) -> str:
    raw = props.get(id_key) or props.get(name_key)
    return name_to_id.get(raw, raw)


def way_endpoints(node, name_to_id: Dict[str, str]):
    """Resolve a way node's two area endpoints to ids.

    Prefers the id fields a generator writes (task-496), falling back to the
    display-name fields hand-authored ways store; either is resolved
    display-name → id, so both compare correctly.
    """
    props = getattr(node, "properties", {}) or {}
    return (_endpoint(props, "area_from_id", "area_from", name_to_id),
            _endpoint(props, "area_to_id", "area_to", name_to_id))


def boundary_ways(graph, area_ids: Iterable[str]) -> List[dict]:
    """Ways with one endpoint inside the scope and one outside."""
    area_ids = set(area_ids)
    name_to_id = _area_name_to_id(graph)

    out = []
    for node_id, node in graph.nodes.items():
        if getattr(node, "type", "") != "way":
            continue
        a, b = way_endpoints(node, name_to_id)
        inside = {x for x in (a, b) if x in area_ids}
        if len(inside) != 1:
            continue
        outside = b if a in inside else a
        out.append({"id": node_id, "name": node.name,
                    "inside": next(iter(inside)), "outside": outside})
    out.sort(key=lambda w: w["id"])
    return out


def area_summary(graph, players, area_id: str) -> dict:
    node = graph.get_node(area_id)
    if node is None:
        return {"id": area_id, "name": area_id, "tags": [],
                "character_count": 0, "item_count": 0}
    return {
        "id": area_id,
        "name": node.name,
        "tags": list(node.properties.get("tags") or []),
        "character_count": characters_in_areas(graph, players, [area_id]),
        "item_count": item_count_in_areas(graph, [area_id]),
    }


def scope_summary(manifest: Dict[str, dict], graph, players, scope_id: str) -> dict:
    rec = manifest.get(scope_id, {"id": scope_id, "name": scope_id,
                                  "kind": DEFAULT_KIND, "state": "unmade"})
    areas = area_ids_in_scope(manifest, graph, scope_id)
    chars = characters_in_areas(graph, players, areas)
    return {
        "id": rec["id"],
        "name": rec["name"],
        "kind": rec["kind"],
        "state": rec["state"],
        "parent_id": rec["parent_id"],
        "area_count": len(areas),
        "character_count": chars,
        "item_count": item_count_in_areas(graph, areas),
        "has_character": chars > 0,
        "children": direct_child_ids(manifest, scope_id),
        # task-523: the graph map layout adds this (cell units) to the scope's
        # painted coords, so a zone dragged on the canvas stays put across loads.
        "map_offset": world_grid.map_offset(rec),
    }


def project(manifest: Dict[str, dict], graph, players, scope_id: str,
            depth: int = 1, include_items: bool = False) -> dict:
    """Scoped projection.

    - A scope with children returns child cards (no unrelated nodes).
    - A leaf scope returns its area summaries and boundary ways, plus the
      contained item/way nodes only when explicitly requested.
    - ``scope_id == "root"`` (or empty/unknown) lists top-level scopes.
    """
    if scope_id in (None, "", "root") or scope_id not in manifest:
        return {"scope": None,
                "children": [scope_summary(manifest, graph, players, sid)
                             for sid in root_scope_ids(manifest)]}

    summary = scope_summary(manifest, graph, players, scope_id)
    child_ids = direct_child_ids(manifest, scope_id)
    if child_ids and depth >= 1:
        return {"scope": summary,
                "children": [scope_summary(manifest, graph, players, c)
                             for c in child_ids]}

    area_ids = sorted(area_ids_in_scope(manifest, graph, scope_id))
    result = {
        "scope": summary,
        "children": [],
        "areas": [area_summary(graph, players, aid) for aid in area_ids],
        "ways": boundary_ways(graph, area_ids),
    }
    if include_items:
        nodes = {}
        edges = []
        for aid in area_ids:
            node = graph.get_node(aid)
            if node:
                nodes[aid] = node.to_dict()
            for item_id in _items_in_area(graph, aid):
                inode = graph.get_node(item_id)
                if inode:
                    nodes[item_id] = inode.to_dict()
                    edges.append({"source": item_id, "target": aid,
                                  "type": "in", "properties": {}})
        result["nodes"] = nodes
        result["edges"] = edges
    return result


def flat_scopes(manifest: Dict[str, dict], graph, players) -> List[dict]:
    """Depth-first scope summaries with a ``depth`` field, for a scope picker.

    Cycle-safe: a scope is emitted at most once, so a malformed manifest whose
    parent links loop cannot hang the picker.
    """
    out: List[dict] = []
    seen: set = set()

    def walk(scope_id: str, depth: int):
        if scope_id in seen or scope_id not in manifest:
            return
        seen.add(scope_id)
        out.append({**scope_summary(manifest, graph, players, scope_id),
                    "depth": depth})
        for child in direct_child_ids(manifest, scope_id):
            walk(child, depth + 1)

    for root_id in root_scope_ids(manifest):
        walk(root_id, 0)
    return out


def rename_scope(manifest: Dict[str, dict], scope_id: str, name: str) -> dict:
    """Set a scope's **display name**. Ids are never renamed (task-439/495).

    Raises ``ValueError`` for an unknown scope or a blank name.
    """
    record = manifest.get(scope_id)
    if record is None:
        raise ValueError(f"scope {scope_id!r} not found")
    clean = str(name or "").strip()
    if not clean:
        raise ValueError("name must not be empty")
    record["name"] = clean
    return record


def delete_scope(manifest: Dict[str, dict], graph, scope_id: str,
                 cascade: bool = False) -> dict:
    """Remove a scope — and with ``cascade`` its descendants — from the world.

    - Refuses when the scope still has children unless ``cascade`` is set.
    - Unplaces it from every parent (``placements`` + ``children`` lists).
    - Deletes its **generated** graph nodes (provenance
      ``properties.generated.scope_id``): areas, ways, gateways and the items
      that generation placed. Hand-authored nodes are left alone rather than
      guessed at — except hand-*placed* areas (task-528), whose reserved cell
      lived in the record being deleted: they keep the area and lose the cell.
    - Returns ``{scope_ids, unplaced_from, deleted_nodes, released_areas}``.
    """
    if scope_id not in manifest:
        raise ValueError(f"scope {scope_id!r} not found")
    children = direct_child_ids(manifest, scope_id)
    if children and not cascade:
        raise ValueError(
            f"scope {scope_id!r} still has child scope(s): "
            f"{', '.join(children)}; delete them first or pass cascade=True")

    doomed = [scope_id]
    if cascade:
        seen = {scope_id}
        stack = list(children)
        while stack:
            child = stack.pop()
            if child in seen or child not in manifest:
                continue
            seen.add(child)
            doomed.append(child)
            stack.extend(direct_child_ids(manifest, child))
    doomed_set = set(doomed)

    unplaced_from: List[str] = []
    for other_id, record in manifest.items():
        if other_id in doomed_set:
            continue
        removed = False
        placements = record.get("placements")
        if isinstance(placements, dict):
            for dead in doomed_set:
                if placements.pop(dead, None) is not None:
                    removed = True
        kids = record.get("children")
        if isinstance(kids, list):
            kept = [c for c in kids if c not in doomed_set]
            removed = removed or len(kept) != len(kids)
            record["children"] = kept
        if removed:
            unplaced_from.append(other_id)

    deleted = 0
    unplaced_areas: List[str] = []
    for node_id, node in list(graph.nodes.items()):
        props = getattr(node, "properties", {}) or {}
        generated = props.get("generated") or {}
        if generated.get("scope_id") in doomed_set:
            graph.remove_node(node_id)
            deleted += 1
            continue
        # A hand-placed area (task-528) survives its scope, but the cell it was
        # parked on lived in that scope's record — which is about to disappear.
        # Leaving `cell` behind would make the whole graph think it has a
        # painted grid (layout-engine's has_painted_grid) on the strength of a
        # cell nothing reserves any more, and a later scope with the same id
        # could generate a second area on it. So release the cell, keep the area.
        if props.get("cell") and props.get("world_scope_id") in doomed_set:
            released = {k: v for k, v in props.items() if k not in ("cell", "x", "y")}
            node.properties = released
            unplaced_areas.append(node_id)

    for dead in doomed:
        manifest.pop(dead, None)
    return {"scope_ids": doomed, "unplaced_from": unplaced_from,
            "deleted_nodes": deleted, "released_areas": unplaced_areas}


def promote_to_scope(manifest: Dict[str, dict], graph, *, scope_id: str,
                      name: str, area_ids: List[str],
                      parent_id: Optional[str] = None,
                      cell: Optional[Tuple[int, int]] = None,
                      entry_area_id: Optional[str] = None,
                      mode: str = "interior",
                      enter: Optional[str] = None,
                      leave: Optional[str] = None,
                      ) -> dict:
    """Make a selection of existing areas into a new child scope (task-535).

    The deferred half of task-528. Task-528 parks an area you already wrote onto a
    cell; this takes a *selection* and makes a scope out of it, so a hand-authored
    interior becomes a level of the world without being redrawn: the areas move
    with their names, their items and their ways, and one gateway is minted from
    the parent's painted cell into the selection's entry area.

    Returns ``{scope_id, name, area_ids, entry_area_id, parent_id, cell, way_id,
    released_from}``, where ``released_from`` maps each promoted area to the scope
    it came out of.

    Four decisions are made here, and they are the reason this is a helper and not
    a route:

    - **Validate before mutating.** Every refusal below happens before the
      manifest, the nodes or the placement are touched, so a rejected promotion
      leaves the world exactly as it was — a half-created scope whose areas have
      already moved is worse than no promotion at all.
    - **The scope is ``baked``.** It is authored, not compiled: these areas came
      from paint or from the author's hand, and the compiler's own rule is to
      refuse a baked materialized scope. So the record carries no grid, and
      Generate on it says so rather than quietly replacing a hand-drawn interior
      with regions.
    - **The gateway is hand-authored and carries no ``generated`` block.**
      ``world_compile._gateway`` stamps ``generated.scope_id`` with the *parent*,
      which would make Ungenerate on the parent delete a gateway the author made
      by promoting something — the exact "it deleted my work" that task-528's
      boundary ways exist to prevent. The parent is left knowing only *where* the
      child is (``placements``); the way belongs to nobody's recipe.
    - **The entry is a choice, not a fallback.** ``entry_area_id`` when the author
      names one, else the first selected area **by id** — deterministic, and not
      "the top-left-most" as the compiler picks, because a promoted selection has
      no painted anchor to be top-left-most of.

    Raises ``ValueError`` for an empty selection, a duplicate scope id, an unknown
    parent, a selected id that is not an area, an entry outside the selection, or
    a cell that is not a painted place on the parent's grid.
    """
    scope_id = str(scope_id or "").strip()
    name = str(name or "").strip()
    if not scope_id:
        raise ValueError("scope_id is required")
    if not name:
        raise ValueError("name is required")
    if scope_id in manifest:
        raise ValueError(f"scope {scope_id!r} already exists")

    wanted: List[str] = []
    for raw in (area_ids or []):
        area_id = str(raw or "").strip()
        if not area_id or area_id in wanted:
            continue
        node = graph.get_node(area_id)
        if node is None or getattr(node, "type", "") != "area":
            raise ValueError(f"{area_id!r} is not an area in this world")
        wanted.append(area_id)
    if not wanted:
        raise ValueError("select at least one area to promote")

    entry = str(entry_area_id or "").strip() or sorted(wanted)[0]
    if entry not in wanted:
        raise ValueError(f"entry area {entry!r} is not in the selection")

    gateway_place = None
    if parent_id is not None:
        parent_id = str(parent_id)
        if parent_id not in manifest:
            raise ValueError(f"no such parent scope {parent_id!r}")
        if world_grid.cell_of(manifest[parent_id], scope_id):
            raise ValueError(f"{scope_id!r} is already placed on this map")
        # The gateway is minted from a *painted* place, and a hand-placed area
        # holding the cell is refused for the same reason a compiled one is: that
        # cell is deleted from the parent's compile set, so a gateway there would
        # be skipped in silence.
        if cell is not None:
            x, y = int(cell[0]), int(cell[1])
            gateway_place = _gateway_place(manifest, graph, parent_id, x, y)
            if gateway_place is None:
                raise ValueError(
                    f"cell ({x},{y}) is not a painted place in {parent_id!r}; "
                    f"a gateway opens from a place, not from a wall")

    # ── from here on the world changes ──
    record = {
        "id": scope_id,
        "name": name,
        "parent_id": parent_id,
        "mode": str(mode or "interior"),
        # Authored, not compiled — see the docstring.
        "paint_policy": "baked",
        "state": "materialized",
        "area_ids": list(wanted),
        "entry_area_id": entry,
        "entry_area_name": str(getattr(graph.get_node(entry), "name", entry)),
    }
    manifest[scope_id] = record
    if parent_id is not None:
        children = manifest[parent_id].setdefault("children", [])
        if scope_id not in children:
            children.append(scope_id)

    # Membership moves at both ends: the node's ``world_scope_id`` is the source of
    # truth and the manifest's list is the denormalized mirror, so both have to go
    # or a moved area keeps appearing in the old scope's count and canvas. Moving
    # out of the parent also releases the parent's cell reservation for it, which is
    # what frees the cell the gateway opens from.
    released_from: Dict[str, str] = {}
    for area_id in wanted:
        node = graph.get_node(area_id)
        props = getattr(node, "properties", None)
        old = str((props or {}).get("world_scope_id") or "")
        if old and old in manifest and old != scope_id:
            released_from[area_id] = old
        assign_area_membership(manifest, area_id, scope_id, old or None)
        if isinstance(props, dict):
            props["world_scope_id"] = scope_id
            # The painted cell belonged to the scope that owned the area; inside
            # the new scope the position is hand-authored canvas space, so the
            # painted marker goes — otherwise the layout engine would read engine
            # units as canvas pixels and place the area somewhere else entirely.
            props.pop("cell", None)

    way_id = ""
    if gateway_place is not None and cell is not None:
        place_area_id, place_name = gateway_place
        way_id = f"way_gateway_{parent_id}_{scope_id}"
        inward = str(enter or f"enter {name.lower()}")
        outward = str(leave or "leave")
        graph.nodes[way_id] = Node(
            id=way_id, type="way", name=f"{place_name} - {name}",
            properties={
                "area_from": place_name,
                "area_to": record["entry_area_name"],
                "area_from_id": place_area_id,
                "area_to_id": entry,
                "direction": inward,
                "return_direction": outward,
                "current_state": "open",
                "see_through": False,
                "pass_message": f"You {inward}.",
                "world_scope_id": parent_id,
                "child_scope_id": scope_id,
                "entry_phrase": inward,
                "entry_target": record["entry_area_name"],
                "aliases": ["in", "out"],
                # The author's own way, on purpose: **no** `generated` block. See
                # the docstring — a parent-stamped one would die with the parent's
                # next Ungenerate.
                "authored": True,
            })
        for source, target, direction in (
                (place_area_id, way_id, inward),
                (way_id, entry, inward),
                (entry, way_id, outward),
                (way_id, place_area_id, outward)):
            graph.add_edge(Edge(source=source, target=target, type=EDGE_CONNECTION,
                                properties={"direction": direction}))
        world_grid.place(manifest, parent_id, scope_id, int(cell[0]), int(cell[1]),
                         on_overlap="gateway")
        manifest[parent_id]["placements"][scope_id].update(
            {"area_id": place_area_id, "area_name": place_name})

    return {"scope_id": scope_id, "name": name, "area_ids": list(wanted),
            "entry_area_id": entry, "parent_id": parent_id,
            "cell": [int(cell[0]), int(cell[1])] if cell else None,
            "way_id": way_id, "released_from": released_from}


def _gateway_place(manifest: Dict[str, dict], graph, parent_id: str, x: int, y: int
                   ) -> Optional[Tuple[str, str]]:
    """The place a gateway out of ``parent_id`` opens from a cell, as ``(id, name)``.

    A hand-placed area on the cell wins (task-528, and the normal case for a
    promoted entrance — the thing being promoted is usually parked beside the road
    first), else the compiled region anchored there. ``None`` when the cell holds
    nothing a way can start from, which the caller turns into a refusal.
    """
    for area_id in (world_grid.area_placement_at(manifest[parent_id], x, y) or "",):
        if not area_id:
            break
        node = graph.get_node(area_id)
        if node is not None:
            return area_id, str(getattr(node, "name", area_id))
        return None
    compiled = f"area_{parent_id}_{x}_{y}"
    node = graph.get_node(compiled)
    if node is None:
        return None
    return compiled, str(getattr(node, "name", compiled))


def ungenerate_scope(manifest: Dict[str, dict], graph, scope_id: str) -> dict:
    """Delete a scope's generated nodes but keep the scope and its painted grid.

    The inverse of ``⚙ Generate``: every node whose provenance
    (``properties.generated.scope_id``) is this scope is removed — areas, ways,
    gateways and generated items — plus any gateway a *parent* emitted that opens
    into this scope (``properties.child_scope_id``). The scope record itself
    survives with its paint, reference, map offset and placements; only
    ``state``/``area_ids``/entry and the compiled ``placements`` area links are
    reset, so a later Generate starts from a clean slate. Returns
    ``{scope_id, deleted_nodes, kept_ways}``.

    **A baked scope cannot be ungenerated** (task-535). A scope promoted from a
    selection of the author's own areas is ``paint_policy: "baked"``: nothing in it
    was compiled, so there is nothing to undo, and a "delete everything this scope
    generated" that emptied it would take a hand-drawn interior with it. So the
    refusal is explicit rather than a no-op — Generate is the button that would
    have something to do, and it says why it will not.

    **A hand-authored way into this scope is kept**, and reported in
    ``kept_ways``. A *compiled* gateway dies with the scope it points at, because
    the scope is being emptied; an author's own does not, because Ungenerate is an
    undo of a Generate and the author never ran one. It is reported rather than
    silently left pointing at nothing.
    """
    if scope_id not in manifest:
        raise ValueError(f"scope {scope_id!r} not found")
    record = manifest[scope_id]
    if str(record.get("paint_policy") or "") == "baked":
        raise ValueError(
            f"scope {scope_id!r} is authored, not generated — there is nothing to "
            f"ungenerate. Delete the scope if you mean to throw it away.")

    deleted = 0
    kept_ways: List[str] = []
    for node_id, node in list(graph.nodes.items()):
        props = getattr(node, "properties", {}) or {}
        generated = props.get("generated") or {}
        into_scope = (getattr(node, "type", None) == "way"
                      and str(props.get("child_scope_id") or "") == scope_id)
        if not into_scope:
            if generated.get("scope_id") == scope_id:
                graph.remove_node(node_id)
                deleted += 1
            continue
        # A parent's *compiled* gateway into this scope dies with it, even though
        # its provenance names the parent.
        if generated:
            graph.remove_node(node_id)
            deleted += 1
        else:
            kept_ways.append(node_id)

    # Compiled placement links point at areas that no longer exist; drop them so
    # a regenerate re-links rather than following a dangling id.
    prefix = f"area_{scope_id}_"
    for other in manifest.values():
        for pos in (other.get("placements") or {}).values():
            if isinstance(pos, dict) and str(pos.get("area_id") or "").startswith(prefix):
                pos.pop("area_id", None)
                pos.pop("area_name", None)

    record["state"] = "unmade"
    record["area_ids"] = []
    record.pop("entry_area_id", None)
    record.pop("entry_area_name", None)
    return {"scope_id": scope_id, "deleted_nodes": deleted, "kept_ways": kept_ways}


def project_subgraph(manifest: Dict[str, dict], graph, players, scope_id: str,
                     include_items: bool = True, descendants: bool = False) -> dict:
    """A vis-loadable subgraph for one scope (task-397 step 3).

    Returns ``{nodes, edges}`` in the same shapes as ``WorldGraph.to_dict`` —
    ``nodes`` keyed by id, ``edges`` a list — so the graph view can load a
    scope's slice instead of the whole world. That is what keeps a densely
    painted WorldPainter world from freezing the canvas: the browser never
    receives nodes outside the requested scope (task-400).

    **Level-scoped by default.** Only the scope's *own* areas are included, so
    selecting a parent shows its own level — a placed child zone is one feature
    cell (carrying ``child_scope_id``), not its whole interior. Pass
    ``descendants=True`` for the recursive subtree (what "Whole world" uses).

    Membership:

    - every ``area`` whose ``world_scope_id`` is this scope (or, when
      ``descendants``, elsewhere in its subtree);
    - a ``way`` whose **both** endpoints are included;
    - a ``character``/``player`` standing in an included area;
    - an ``item`` attached to an included area, when ``include_items`` is true.

    Only edges with both endpoints included are emitted, so no edge ever
    dangles to a node the browser never received.
    """
    if descendants:
        area_ids = area_ids_in_scope(manifest, graph, scope_id)
    else:
        area_ids = own_area_ids(graph, scope_id)
    name_to_id = _area_name_to_id(graph)
    included: set = set()
    nodes: Dict[str, dict] = {}

    def add(node):
        if node is None or node.id in included:
            return
        included.add(node.id)
        nodes[node.id] = node.to_dict()

    for node in graph.nodes.values():
        if getattr(node, "type", "") == "area" and node.id in area_ids:
            add(node)

    for node in graph.nodes.values():
        if getattr(node, "type", "") != "way":
            continue
        a, b = way_endpoints(node, name_to_id)
        if a in area_ids and b in area_ids:
            add(node)

    for node in graph.nodes.values():
        ntype = getattr(node, "type", "")
        if ntype in ("character", "player") or (include_items and ntype == "item"):
            for edge in graph.get_edges_for_source(node.id):
                if getattr(edge, "type", "") in SPATIAL_TYPES and edge.target in area_ids:
                    add(node)
                    break

    edges = [e.to_dict() for e in graph.edges
             if e.source in included and e.target in included]
    return {"nodes": nodes, "edges": edges}
