"""Structure templates: capture a connected area group (with population) and
materialize it into another world.

See ``docs/virtualWorld/dev_tasks/todo/library/task-357-structure-save-load-connected-areas.md``.

A *structure* is a portable, internally-wired subgraph — areas + ways + items +
resident characters (as full ``Player`` payloads) — plus boundary stubs for exits
that leave the captured group. Capture is a raw graph subset so materialization
is a straight replay with deterministic id remapping.

Design rules (task-357, settled 2026-09-22):

- Template semantics are the core; a pinned-identity pack is a special case.
- Node collisions remap **ids only** — a node's display name is never changed.
  Residents are the exception: the engine keys people by name, so a duplicate
  resident **mints a unique instance name** (``zombie`` → ``zombie 2``) rather
  than being dropped. True duplicate display names need the id-keyed identity
  refactor.
- Characters are ``Player`` payloads (state lives in ``player_manager.players``),
  not bare graph anchors.
- Boundary exits are near-side-only way stubs; never an edge to a missing node.
  Grafting a stub onto the host world is manual **by design**; all wiring
  *inside* the captured group is replayed automatically.
- Materialization is add-only and deterministic for a given ``(template, seed)``.
"""

from __future__ import annotations

import copy
import hashlib
import re
from typing import Any, Dict, List, Optional, Set

from graph import (
    Edge,
    Node,
    EDGE_AT,
    EDGE_BEHIND,
    EDGE_BESIDE,
    EDGE_CARRYING,
    EDGE_CONNECTION,
    EDGE_EQUIPPED,
    EDGE_IN,
    EDGE_ON,
    EDGE_UNDER,
)

# Items physically present in a captured area (directly or on a surface/container).
_ITEM_PLACEMENT_EDGE_TYPES = (
    EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT,
)
# Items held by a captured resident.
_ITEM_HOLD_EDGE_TYPES = (EDGE_CARRYING, EDGE_EQUIPPED)
# Obsolete since triggers superseded them (corrections.md graph.unlock_edges_obsolete).
_OBSOLETE_EDGE_TYPES = ("unlocks", "requires")
# Node properties that are runtime artifacts, not authored content.
_RUNTIME_PROP_KEYS = ("last_relation",)

STRUCTURE_SCHEMA_VERSION = 1


# ───────────────────────────── helpers ─────────────────────────────


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").lower()).strip("_") or "structure"


def _same_id(a: Any, b: Any) -> bool:
    return str(a or "").lower() == str(b or "").lower()


def _remap_refs(value: Any, id_map: Dict[str, str]) -> Any:
    """Recursively rewrite any string equal to a remapped node id.

    Handles edge endpoints, id-bearing properties (``area_from``/``area_to``,
    ``node_id``, trigger ``target``), ``equipped`` stacks and memory
    ``entity_ids`` uniformly, so a remap can never leave a dangling reference.
    """
    if isinstance(value, str):
        return id_map.get(value, value)
    if isinstance(value, list):
        return [_remap_refs(v, id_map) for v in value]
    if isinstance(value, dict):
        return {k: _remap_refs(v, id_map) for k, v in value.items()}
    return value


def _deterministic_suffix(template_id: str, seed: Any, old_id: str) -> str:
    raw = f"{template_id}:{seed}:{old_id}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:6]


def _unique_id(graph, old_id: str, template_id: str, seed: Any, used: Set[str]) -> str:
    """Return ``old_id`` when free, else a deterministic suffixed variant.

    Display names are untouched; only the id changes (task-357).
    """
    if graph.get_node(old_id) is None and old_id not in used:
        return old_id
    suffix = _deterministic_suffix(template_id, seed, old_id)
    candidate = f"{old_id}__{suffix}"
    n = 2
    while graph.get_node(candidate) is not None or candidate in used:
        candidate = f"{old_id}__{suffix}_{n}"
        n += 1
    return candidate


def _find_area_node_by_name(graph, name: str):
    if not name:
        return None
    wanted = str(name).lower()
    # Prefer the derived id, then any area node with a matching name.
    derived = f"area_{str(name).lower()}".replace(" ", "_")
    node = graph.get_node(derived)
    if node and node.type == "area":
        return node
    for node in graph.nodes.values():
        if node.type == "area" and str(node.name).lower() == wanted:
            return node
    return None


def _instance_name(pm, base: str) -> str:
    """Mint a unique instance name for a materialized resident.

    Duplicates resolve by identity, not by refusing the copy: base ``zombie``
    stamped three times gives ``zombie``, ``zombie 2``, ``zombie 3`` (node ids
    ``player_zombie``, ``player_zombie_2``, ...). Display names stay readable and
    unique, which the current name-keyed engine requires. Deterministic for
    identical host worlds; true duplicate *display* names (500 literal "Jon"s)
    need the id-keyed identity refactor and are out of scope here.
    """
    if base not in pm.players:
        return base
    n = 2
    while f"{base} {n}" in pm.players:
        n += 1
    return f"{base} {n}"


def _place_anchor(graph, anchor_id: str, area_node: Node) -> None:
    """Point a character anchor's EDGE_IN at the (possibly non-derived) area id."""
    for edge in list(graph.get_edges_for_source(anchor_id, EDGE_IN)):
        graph.remove_edge(edge.source, edge.target, edge.type)
    graph.add_edge(Edge(source=anchor_id, target=area_node.id, type=EDGE_IN))


# ───────────────────────────── capture ─────────────────────────────


def collect_structure(
    world,
    root_area_id: str,
    include_items: bool = True,
    include_characters: bool = False,
    template_id: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Walk outward from ``root_area_id`` and return a structure template.

    Traversal follows ``EDGE_CONNECTION`` area→way→area with a visited set, so
    cycles terminate. Boundary ways (no far-side area node, or far side outside
    the captured group) keep only their near-side edges and are recorded in
    ``boundary_exits`` as graft points.

    Returns ``{schema_version, template_id, name, root_area, nodes, edges,
    residents, boundary_exits, captured}``.
    """
    graph = world.graph
    pm = world.player_manager

    root = graph.get_node(root_area_id)
    if not root or root.type != "area":
        raise ValueError(f"Not an area: {root_area_id!r}")
    root_id = root.id

    area_ids: List[str] = []
    area_seen: Set[str] = set()
    way_ids: Set[str] = set()
    boundary_exits: List[Dict[str, str]] = []

    queue = [root_id]
    area_seen.add(root_id)
    while queue:
        area_id = queue.pop(0)
        area_ids.append(area_id)
        for edge in graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            way = graph.get_node(edge.target)
            if not way or way.type != "way":
                continue
            way_ids.add(way.id)
            far_area = None
            for conn in graph.get_edges_for_source(way.id, EDGE_CONNECTION):
                if _same_id(conn.target, area_id):
                    continue
                cand = graph.get_node(conn.target)
                if cand and cand.type == "area":
                    far_area = cand
                    break
            if far_area is None:
                boundary_exits.append({
                    "way": way.id,
                    "area": area_id,
                    "direction": edge.properties.get("direction", ""),
                    "name": way.name,
                })
            elif far_area.id not in area_seen:
                area_seen.add(far_area.id)
                queue.append(far_area.id)

    collected: Set[str] = set(area_ids) | way_ids
    item_ids: Set[str] = set()

    if include_items:
        # Fixpoint: pull in items reachable through area/surface/container
        # placement edges, in any order, without depending on edge order.
        changed = True
        while changed:
            changed = False
            for edge in graph.edges:
                if edge.type not in _ITEM_PLACEMENT_EDGE_TYPES:
                    continue
                if edge.target in collected and edge.source not in collected:
                    src = graph.get_node(edge.source)
                    if src and src.type == "item":
                        collected.add(src.id)
                        item_ids.add(src.id)
                        changed = True

    resident_entries: List[Dict[str, Any]] = []
    if include_characters:
        for area_id in area_ids:
            area_node = graph.get_node(area_id)
            area_name = area_node.name if area_node else ""
            for pname, player_obj in list(pm.players.items()):
                if getattr(player_obj, "current_area", None) != area_name:
                    continue
                anchor_id = pm.get_player_node_id(pname)
                payload = world.serializer._serialize_player(pname, player_obj)
                resident_entries.append({"name": pname, "anchor_id": anchor_id, "player": payload})
                collected.add(anchor_id)
                for hold_type in _ITEM_HOLD_EDGE_TYPES:
                    for hold_edge in graph.get_edges_for_target(anchor_id, hold_type):
                        held = graph.get_node(hold_edge.source)
                        if held and held.type == "item":
                            collected.add(held.id)
                            item_ids.add(held.id)

    nodes: Dict[str, Any] = {}
    for nid in collected:
        if any(res["anchor_id"] == nid for res in resident_entries):
            continue  # anchors travel as residents, not as raw nodes
        node = graph.get_node(nid)
        if not node:
            continue
        node_dict = node.to_dict()
        props = node_dict.get("properties")
        if isinstance(props, dict):
            for key in _RUNTIME_PROP_KEYS:
                props.pop(key, None)
        nodes[nid] = node_dict

    edges: List[Any] = []
    for edge in graph.edges:
        if edge.type in _OBSOLETE_EDGE_TYPES:
            continue
        if edge.source in collected and edge.target in collected:
            edges.append(edge.to_dict())

    return {
        "schema_version": STRUCTURE_SCHEMA_VERSION,
        "template_id": template_id or _slug(root.name),
        "name": name or root.name,
        "root_area": root_id,
        "nodes": nodes,
        "edges": edges,
        "residents": resident_entries,
        "boundary_exits": boundary_exits,
        "captured": {
            "areas": len(area_ids),
            "ways": len(way_ids),
            "items": len(item_ids),
            "residents": len(resident_entries),
            "boundary_exits": len(boundary_exits),
        },
    }


def summarize_structure(template: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight listing entry for a stored template."""
    captured = template.get("captured") or {}
    return {
        "id": template.get("template_id", ""),
        "name": template.get("name", template.get("template_id", "")),
        "root_area": template.get("root_area", ""),
        "areas": captured.get("areas", len(template.get("nodes") or {})),
        "ways": captured.get("ways", 0),
        "items": captured.get("items", 0),
        "residents": captured.get("residents", len(template.get("residents") or [])),
        "boundary_exits": captured.get("boundary_exits", len(template.get("boundary_exits") or [])),
    }


# ──────────────────────────── materialize ────────────────────────────


def materialize_structure(
    world,
    template: Dict[str, Any],
    seed: Any = None,
    include_items: bool = True,
    include_characters: bool = True,
) -> Dict[str, Any]:
    """Replay a structure template into the live world. Add-only.

    Node ids are remapped deterministically for collisions; node display names
    are kept. Residents are deserialized as full ``Player`` objects and default
    to ``simulation_mode == "background"``; a duplicate resident name mints a
    unique instance (``zombie`` → ``zombie 2``). All edges inside the captured
    group are replayed automatically, so the imported zone is fully wired;
    boundary stubs are dead exits the author grafts manually (by design).
    """
    graph = world.graph
    pm = world.player_manager
    template_id = template.get("template_id") or template.get("name") or "structure"
    seed = 0 if seed is None else seed

    template_nodes = template.get("nodes") or {}
    template_edges = template.get("edges") or []
    residents = template.get("residents") or []

    id_map: Dict[str, str] = {}
    used: Set[str] = set()
    for old_id in template_nodes:
        if not include_items and (template_nodes[old_id].get("type") == "item"):
            continue
        new_id = _unique_id(graph, old_id, template_id, seed, used)
        id_map[old_id] = new_id
        used.add(new_id)

    # Resident anchors never collide by name (collisions are skipped below), so
    # their id is the canonical convention; map the old anchor id to it.
    for res in residents:
        if res.get("anchor_id"):
            id_map[res["anchor_id"]] = pm.get_player_node_id(res["name"])

    materialized = {"areas": 0, "ways": 0, "items": 0, "residents": 0, "edges": 0}
    renamed: List[Dict[str, str]] = []

    for old_id, node_dict in template_nodes.items():
        new_id = id_map.get(old_id)
        if new_id is None:
            continue
        node_type = node_dict.get("type", "")
        props = _remap_refs(copy.deepcopy(node_dict.get("properties") or {}), id_map)
        graph.add_node(Node(
            id=new_id,
            type=node_type,
            name=node_dict.get("name", new_id),
            properties=props,
        ))
        if new_id != old_id:
            renamed.append({"old_id": old_id, "new_id": new_id})
        if node_type == "area":
            materialized["areas"] += 1
        elif node_type == "way":
            materialized["ways"] += 1
        elif node_type == "item":
            materialized["items"] += 1

    for edge_dict in template_edges:
        src = id_map.get(edge_dict.get("source"))
        tgt = id_map.get(edge_dict.get("target"))
        if src is None or tgt is None:
            continue  # boundary far side / excluded type
        props = _remap_refs(copy.deepcopy(edge_dict.get("properties") or {}), id_map)
        graph.add_edge(Edge(source=src, target=tgt, type=edge_dict.get("type", ""), properties=props))
        materialized["edges"] += 1

    imported_residents: List[str] = []
    minted_residents: List[Dict[str, str]] = []
    if include_characters:
        for res in residents:
            base_name = res.get("name")
            if not base_name:
                continue
            # Never drop a resident for a name clash: mint a unique instance
            # identity (zombie → zombie 2) so a stamp always delivers its
            # population. See _instance_name for the id-vs-name caveat.
            instance_name = _instance_name(pm, base_name)
            payload = _remap_refs(copy.deepcopy(res.get("player") or {}), id_map)
            payload["name"] = instance_name
            player_obj = world.serializer._deserialize_player(instance_name, payload)
            # Residents default to the background tier. Use the promotion seam
            # (task-399) so the demotion boundary tick is stamped — a later
            # activation can then summarize exactly the background span.
            mode = payload.get("simulation_mode") or "background"
            if mode == "background":
                from engine import promotion
                promotion.offload(world, player_obj, reason="materialize")
            else:
                player_obj.simulation_mode = mode
            pm.players[instance_name] = player_obj
            anchor_id = pm.get_player_node_id(instance_name)
            if graph.get_node(anchor_id) is None:
                graph.add_node(Node(id=anchor_id, type="character", name=instance_name))
            area_node = _find_area_node_by_name(graph, player_obj.current_area)
            if area_node is not None:
                _place_anchor(graph, anchor_id, area_node)
            imported_residents.append(instance_name)
            if instance_name != base_name:
                minted_residents.append({"from": base_name, "to": instance_name})
            materialized["residents"] += 1

    issues: List[Any] = []
    try:
        issues = world.validate_triggers() if hasattr(world, "validate_triggers") else []
    except Exception:
        issues = []

    return {
        "status": "materialized",
        "template_id": template_id,
        "materialized": materialized,
        "renamed": renamed,
        "residents": imported_residents,
        "minted_residents": minted_residents,
        "boundary_exits": template.get("boundary_exits") or [],
        "validator_issues": issues,
    }
