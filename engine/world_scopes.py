"""World scope manifest and scoped projections (task-397).

A *scope* is a durable grouping/load boundary over the existing flat
area/way/item graph. Leaf areas stay normal ``area`` nodes; scopes never add
fake area nodes for buildings/floors/continents.

The manifest is a plain dict ``{scope_id: record}`` persisted on the world as
``world_scopes``. Everything here is pure over (manifest, graph, players) so it
is easily testable and safe for route handlers to call.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from engine import world_grid

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


def _area_name_to_id(graph) -> Dict[str, str]:
    return {node.name: node_id for node_id, node in graph.nodes.items()
            if getattr(node, "type", "") == "area"}


def _items_in_area(graph, area_id: str) -> List[str]:
    out = []
    for edge in graph.get_edges_for_target(area_id):
        if edge.type in SPATIAL_TYPES and graph.get_node(edge.source):
            out.append(edge.source)
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
      guessed at.
    - Returns ``{scope_ids, unplaced_from, deleted_nodes}``.
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
    for node_id, node in list(graph.nodes.items()):
        generated = (getattr(node, "properties", {}) or {}).get("generated") or {}
        if generated.get("scope_id") in doomed_set:
            graph.remove_node(node_id)
            deleted += 1

    for dead in doomed:
        manifest.pop(dead, None)
    return {"scope_ids": doomed, "unplaced_from": unplaced_from,
            "deleted_nodes": deleted}


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
