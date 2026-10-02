"""WorldPainter grid authoring API (task-495).

Read + write endpoints for a scope's authoring grid: select a scope, set or
resize its grid, paint a cell, and place/move/remove feature (child-scope)
placements. All mutation goes through the pure helpers in
``engine/world_grid.py`` so the editor, the compiler (task-496), and the tests
agree on one shape.

This is the *authoring substrate*, not engine behaviour: nothing here changes
area/way nodes. The grid→graph compiler (task-496) consumes the same data via
task-398's generation contract.

Undo/autosave: these POSTs are covered by ``app.py``'s after-mutation hook, but
each mutating handler pushes its own **pre-state** snapshot (the hook is told to
skip these paths) so the first Undo actually reverts the edit.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from flask import jsonify, request

from engine import biomes as biomes_mod
from engine import (generation, generation_recipes, interior_gen, world_compile,
                    world_grid, world_scopes)
from engine.population import LibraryIndex


# ─────────────────────────────── helpers ──────────────────────────────────


def _load(app) -> Dict[str, dict]:
    """The live manifest, normalised. Callers mutate and hand to :func:`_commit`."""
    return world_scopes.normalise_manifest(
        getattr(app.world, "world_scopes", {}) or {})


def _commit(app, manifest: Dict[str, dict]) -> None:
    """Write a mutated manifest back onto the world."""
    app.world.world_scopes = manifest


def _snapshot(app, label: str) -> None:
    """Push a pre-state undo snapshot (mirrors ``graph_ops.handle_delete_node``)."""
    from routes.saveload import _push_undo_snapshot
    _push_undo_snapshot(app, label=label)


def _recipe_entry_area(manifest: Dict[str, dict], record: Dict[str, dict]) -> Optional[str]:
    """The area a recipe's front door opens off.

    The recipe stays a pure function and takes this as an argument, so the *author*
    decides what "the hall" is. Explicit ``entry_area_id`` on the scope wins;
    otherwise the first area of the parent scope, which is the hallway a child
    apartment opens off in every floor in the data.
    """
    explicit = record.get("entry_area_id")
    if explicit:
        return explicit
    parent = manifest.get(record.get("parent_id")) or {}
    areas = parent.get("area_ids") or []
    return areas[0] if areas else None


def _breadcrumb(manifest: Dict[str, dict], scope_id: str) -> List[dict]:
    """``[{id, name}, ...]`` from the root down to *scope_id* (cycle-safe)."""
    trail: List[dict] = []
    seen = set()
    current: Optional[str] = scope_id
    while current and current in manifest and current not in seen:
        seen.add(current)
        rec = manifest[current]
        trail.append({"id": rec["id"], "name": rec["name"]})
        current = rec.get("parent_id")
    trail.reverse()
    return trail


def _unplaced_areas(graph, manifest: Dict[str, dict]) -> List[dict]:
    """Hand-authored areas not parked on any grid — the place tool's candidates.

    An area qualifies when it is an ``area`` node, carries no ``generated``
    provenance, and has no cell anywhere. Generated areas are excluded on purpose:
    they already own a cell, and re-pointing one would fight the scope that
    generated it (see the task-528 refusal in :func:`handle_place_area`).

    Every candidate carries its **owning scope** (``scope_id``/``scope_name``), not
    just that it has none: the picker groups by scope (task-541), so an area of a
    child scope is never listed as if it belonged to the map being painted. An
    area with no scope at all is genuinely free-floating and is grouped with the
    scope being edited.
    """
    if graph is None:
        return []
    placed: set = set()
    for record in (manifest or {}).values():
        placed.update(world_grid.area_placements(record))
    out: List[dict] = []
    for node_id, node in getattr(graph, "nodes", {}).items():
        if getattr(node, "type", "") != "area":
            continue
        props = getattr(node, "properties", {}) or {}
        if props.get("generated") or props.get("cell") or node_id in placed:
            continue
        owner = props.get("world_scope_id")
        out.append({"id": node_id, "name": getattr(node, "name", node_id),
                    "scope_id": owner,
                    "scope_name": (manifest.get(owner) or {}).get("name") if owner else None})
    out.sort(key=lambda area: str(area["name"]).lower())
    return out


def _boundary_ways(graph, rec: Dict[str, dict], scope_id: str) -> List[dict]:
    """The boundary ways this scope minted around its hand-placed areas (task-528).

    A boundary way is recognised by its **endpoints** rather than by its id: one
    of them is an area the author parked on this grid. That is the same test
    :func:`handle_boundary_override` uses, kept in one place so the painter can
    never offer to remove a way the route would then refuse.

    Only this scope's own generated ways, and only ones that still stand: a seam
    the author removed is in ``boundary_overrides`` instead, so the list is "what
    Generate put here", with ``overridden`` marking the ones already handed back.
    """
    placed_ids = set(world_grid.area_placements(rec))
    if graph is None or not placed_ids:
        return []
    overrides = world_grid.boundary_overrides(rec)
    out: List[dict] = []
    for node_id, node in getattr(graph, "nodes", {}).items():
        if getattr(node, "type", "") != "way":
            continue
        props = getattr(node, "properties", {}) or {}
        if str((props.get("generated") or {}).get("scope_id") or "") != str(scope_id):
            continue
        ends = [str(props.get("area_from_id") or ""), str(props.get("area_to_id") or "")]
        froms = [(a, b) for a, b in zip(ends, ends[::-1]) if a in placed_ids]
        if not froms:
            continue
        placed_id, other_id = froms[0]
        other = graph.get_node(other_id) if other_id else None
        out.append({
            "way_id": node_id,
            "name": getattr(node, "name", node_id),
            "area_id": placed_id,
            "area_name": getattr(graph.get_node(placed_id), "name", placed_id),
            "to_id": other_id,
            "to_name": getattr(other, "name", other_id) if other is not None else other_id,
            "direction": props.get("direction"),
            "kind": props.get("kind"),
            "cell": props.get("cell"),
            "overridden": node_id in overrides,
        })
    out.sort(key=lambda row: (str(row["area_name"]).lower(), str(row["to_name"]).lower()))
    return out


def _grid_payload(manifest: Dict[str, dict], scope_id: str, graph=None) -> dict:
    """Everything the editor needs to render one scope's grid."""
    rec = manifest[scope_id]
    w, h = world_grid.grid_size(rec)
    placements = []
    for child_id, pos in world_grid.placements(rec).items():
        child = manifest.get(child_id, {})
        placements.append({
            "id": child_id,
            "name": child.get("name", child_id),
            "kind": child.get("kind", "scope"),
            "mode": child.get("mode"),
            "x": pos["x"],
            "y": pos["y"],
        })
    area_placements = []
    for area_id, pos in world_grid.area_placements(rec).items():
        node = graph.get_node(area_id) if graph is not None else None
        area_placements.append({
            "id": area_id,
            "name": getattr(node, "name", area_id) if node is not None else area_id,
            "x": pos["x"],
            "y": pos["y"],
        })
    area_placements.sort(key=lambda area: str(area["name"]).lower())
    # The author's decisions about the boundary ways the compiler minted for
    # those placements (task-528), so the painter can mark a seam as theirs
    # instead of leaving the author to remember which ones they touched.
    boundary_overrides = []
    for way_id, decision in world_grid.boundary_overrides(rec).items():
        node = graph.get_node(way_id) if graph is not None else None
        boundary_overrides.append({
            "way_id": way_id,
            "action": decision.get("action"),
            "hand_way_id": decision.get("way_id"),
            "name": getattr(node, "name", way_id) if node is not None else way_id,
        })
    boundary_overrides.sort(key=lambda row: str(row["name"]).lower())
    # …and the seams themselves, so the painter can offer each one back or take it
    # away without the author having to find the way in the graph first (task-528).
    boundary_ways = _boundary_ways(graph, rec, scope_id)
    children = []
    for child_id in world_scopes.direct_child_ids(manifest, scope_id):
        child = manifest[child_id]
        child_w, child_h = world_grid.grid_size(child)
        children.append({
            "id": child["id"],
            "name": child["name"],
            "kind": child["kind"],
            "state": child["state"],
            "mode": child.get("mode"),
            "has_grid": world_grid.has_grid(child),
            "w": child_w,
            "h": child_h,
            "placed": child_id in world_grid.placements(rec),
        })
    parent = None
    if rec.get("parent_id") and rec["parent_id"] in manifest:
        parent = {"id": rec["parent_id"], "name": manifest[rec["parent_id"]]["name"]}
    return {
        "scope": {
            "id": rec["id"],
            "name": rec["name"],
            "kind": rec["kind"],
            "state": rec["state"],
            "mode": rec.get("mode"),
            "has_grid": world_grid.has_grid(rec),
            # The editor cannot see this anywhere else, and it is the difference
            # between "Generate failed" and an explanation. `baked` is the reason
            # a scope promoted from existing areas can never be compiled, and it
            # used to be readable only in the save file.
            "paint_policy": rec.get("paint_policy") or world_compile.PAINT_POLICY_CANONICAL,
        },
        "grid": ({"w": w, "h": h, "cell_scale": (rec.get("grid") or {}).get("cell_scale", 1.0)}
                 if world_grid.has_grid(rec) else None),
        "mode": rec.get("mode"),
        "reference": world_grid.reference(rec),
        # Every paint layer is present, even when nothing is painted on it
        # (task-651). The records are normalized to omit empty layers, so a
        # scope with only biome/road used to arrive with those two keys and no
        # floor/climate at all — indistinguishable from "this layer does not
        # exist" to anything reading the payload. The editor offers four layers,
        # so the payload answers with four, each possibly {}.
        "layers": {layer: dict((rec.get("layers") or {}).get(layer) or {})
                   for layer in world_grid.PAINT_LAYERS},
        "names": dict(rec.get("names") or {}),
        "map_offset": world_grid.map_offset(rec),
        "placements": placements,
        "feature": world_grid.feature_layer(rec),
        "area_placements": area_placements,
        "boundary_overrides": boundary_overrides,
        "boundary_ways": boundary_ways,
        "unplaced_areas": _unplaced_areas(graph, manifest),
        "children": children,
        "parent": parent,
        "breadcrumb": _breadcrumb(manifest, scope_id),
        # Why this scope cannot be compiled yet, and what to do about it. The
        # compiler's own refusals, as advice, so a scope explains itself before
        # the author presses Generate rather than after.
        "blockers": world_compile.preflight(manifest, scope_id),
    }


def _unique_scope_id(manifest: Dict[str, dict], base: str) -> str:
    """A scope id that is free, disambiguating by id only (display name kept)."""
    base = base or "scope"
    candidate, n = base, 2
    while candidate in manifest:
        candidate = f"{base}_{n}"
        n += 1
    return candidate


def _slug(name: str) -> str:
    out = "".join(c if (c.isalnum() or c in "_-") else "_" for c in str(name or "").strip().lower())
    return out.strip("_") or "scope"


def _error(message: str, status: int = 400):
    return jsonify({"error": message}), status


# ─────────────────────────────── reads ────────────────────────────────────


def handle_scope_grid(app, scope_id):
    """GET /api/world/scopes/<scope_id>/grid — the scope's authoring grid."""
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    return jsonify(_grid_payload(manifest, scope_id, app.world.graph))


def handle_painter_vocabulary(app):
    """GET /api/world/painter/vocabulary — the values a cell may be painted with.

    The editor needs the real ids, not free text: a biome id painted wrong does
    not error, it silently compiles a barren area (no tags → nothing forages or
    spawns there). Served from the taxonomy (``data/worldpainter/biomes.json``).
    """
    return jsonify({
        # `tags` ride along because the editor groups the palette by them: a town
        # author picks a *building* from 30-odd types, which is only usable if the
        # list is grouped by category instead of being one flat 47-entry column
        # (task-561). It is also what makes the types self-describing to anything
        # else that reads the vocabulary.
        "biomes": [{"id": key, "name": (rec or {}).get("name", key),
                    "tags": list((rec or {}).get("tags") or []),
                    # A tile has to be pickable without a lookup (task-596): the
                    # palette shows what the entry *is* (its ground material and
                    # its prose) next to what it does. The same record the
                    # compiler reads, so the preview cannot drift from the world.
                    "surface": (rec or {}).get("surface", ""),
                    "descriptions": list((rec or {}).get("descriptions") or []),
                    # What this building's door says when it has no interior to go
                    # into (task-563). Sent from the same function the compiler
                    # uses, so the line the painter reads in the cell inspector is
                    # the line the world gives — one implementation, not two.
                    "refusal": (world_compile.building_refusal(key)
                                if biomes_mod.is_building(key) else "")}
                   for key, rec in sorted(biomes_mod.biomes().items())],
        # Features carry what makes a bridge a bridge and a ford a ford (task-596
        # asks the palette to answer that without opening another panel): the
        # prose, the terrain it may cross, and the verb its doorway uses.
        "features": [{"id": key, "name": (rec or {}).get("name", key),
                      "tags": list((rec or {}).get("tags") or []),
                      "biomes": list((rec or {}).get("biomes") or []),
                      "entry_phrase": (rec or {}).get("entry_phrase", ""),
                      "exit_phrase": (rec or {}).get("exit_phrase", ""),
                      "descriptions": list((rec or {}).get("descriptions") or [])}
                     for key, rec in sorted(biomes_mod.features().items())],
        # The coarse climates, from the same table the compiler aggregates against
        # (task-557). Sent rather than duplicated in the editor, because a palette
        # showing one base °C while the compiler writes another is the kind of
        # disagreement nobody notices until a painted mountain is the wrong
        # temperature. The editor adds only the *colour*, which is a display
        # decision the backend has no opinion about.
        "climates": [{"id": key, "base": base}
                     for key, base in sorted(world_grid.CLIMATE_BASE_C.items())],
        "default_climate": world_grid.DEFAULT_CLIMATE,
        "layers": list(world_grid.PAINT_LAYERS),
        "modes": list(world_grid.MODES),
    })


# ─────────────────────────────── writes ───────────────────────────────────


def handle_create_scope(app):
    """POST /api/world/scopes — create an (optionally gridded) scope.

    Used by the editor's "add feature" affordance: a feature is a child scope
    placed at a cell. Creating the record does not fabricate any area/way node;
    task-398/496 generate those. The id is disambiguated on collision; the
    display name is never renamed.

    Hierarchy is "root then zone": a record with no ``parent_id`` is a root
    (there is no stored root record — the literal id ``"root"`` is only a
    projection alias), and a zone passes ``parent_id`` naming an **existing**
    scope; an unknown parent is rejected here. Creating a child never compiles
    the parent's or the child's grid — generation is per scope (see
    ``handle_generate_scope``), so a placed feature's own grid is generated
    separately.
    """
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    if not name:
        return _error("name is required")

    manifest = _load(app)
    scope_id = _unique_scope_id(manifest, str(data.get("id") or _slug(name)).strip())
    parent_id = data.get("parent_id") or None
    if parent_id is not None and parent_id not in manifest:
        return _error(f"Parent scope '{parent_id}' not found")

    mode = data.get("mode")
    if mode is not None and mode not in world_grid.MODES:
        return _error(f"unknown mode {mode!r}; expected one of {world_grid.MODES}")

    record: Dict = {
        "id": scope_id,
        "name": name,
        "kind": str(data.get("kind") or "scope"),
        "parent_id": parent_id,
        "children": [],
        "area_ids": [],
        "state": str(data.get("state") or "unmade"),
    }
    try:
        w, h = data.get("w"), data.get("h")
        if w and h:
            world_grid.ensure_grid(record, int(w), int(h),
                                   float(data.get("cell_scale") or 1.0), mode=mode)
        elif mode:
            record["mode"] = mode
    except (TypeError, ValueError) as exc:
        return _error(str(exc))

    _snapshot(app, label=f"create scope {name}")
    manifest[scope_id] = record
    if parent_id is not None:
        siblings = manifest[parent_id].setdefault("children", [])
        if scope_id not in siblings:
            siblings.append(scope_id)
    _commit(app, manifest)
    return jsonify({"status": "created", **_grid_payload(manifest, scope_id, app.world.graph)})


def handle_set_scope_grid(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid — create/resize the grid.

    Body: ``{w, h, cell_scale?, mode?}``. A shrink prunes out-of-bounds paint and
    placements (``engine/world_grid.ensure_grid``) rather than dangling them.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    record = manifest[scope_id]
    try:
        w = int(data.get("w"))
        h = int(data.get("h"))
    except (TypeError, ValueError):
        return _error("w and h are required integers")
    mode = data.get("mode", record.get("mode"))
    if mode is not None and mode not in world_grid.MODES:
        return _error(f"unknown mode {mode!r}; expected one of {world_grid.MODES}")

    try:
        _snapshot(app, label=f"set grid {record.get('name', scope_id)}")
        world_grid.ensure_grid(record, w, h, float(data.get("cell_scale") or 1.0), mode=mode)
    except (TypeError, ValueError) as exc:
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": "saved", **_grid_payload(manifest, scope_id, app.world.graph)})


def handle_paint_cell(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/paint — set one cell on a layer.

    Body: ``{layer, x, y, value}``. ``value`` of ``null``/``""`` erases the cell.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    record = manifest[scope_id]
    layer = data.get("layer")
    try:
        x, y = int(data.get("x")), int(data.get("y"))
    except (TypeError, ValueError):
        return _error("x and y are required integers")

    try:
        _snapshot(app, label=f"paint {layer} on {record.get('name', scope_id)}")
        world_grid.paint(record, layer, x, y, data.get("value"))
    except ValueError as exc:
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": "painted", "layer": layer, "x": x, "y": y,
                    "value": data.get("value"),
                    **_grid_payload(manifest, scope_id, app.world.graph)})


def handle_set_cell_name(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/name — set one cell's name.

    Body: ``{x, y, name}``. An empty/whitespace ``name`` clears it.

    A name is *metadata about* a cell, not paint on it, so it is a map beside the
    layers rather than a fourth layer: there is no name vocabulary, and a name is
    not something you paint over or erase with the eraser. The compiler uses it for
    the place's **display name** (task-560) and nothing else — ids stay the
    authoritative key.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    record = manifest[scope_id]
    try:
        x, y = int(data.get("x")), int(data.get("y"))
    except (TypeError, ValueError):
        return _error("x and y are required integers")
    name = data.get("name")
    if name is not None and not isinstance(name, str):
        return _error("name must be a string")

    try:
        _snapshot(app, label=f"name cell {x},{y} on {record.get('name', scope_id)}")
        now = world_grid.set_name(record, x, y, name)
    except ValueError as exc:
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": "named", "x": x, "y": y, "name": now,
                    **_grid_payload(manifest, scope_id, app.world.graph)})


def handle_place_feature(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/place — place/move a child scope.

    Body: ``{child_id, x, y, on_overlap?}``. Overlap is forbidden by default;
    ``on_overlap="displace"`` replaces the occupant (the placement rule in
    ``engine/world_grid.py``). Ids/references are preserved — a move only changes
    the cell.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    child_id = str(data.get("child_id") or "").strip()
    if not child_id:
        return _error("child_id is required")
    try:
        x, y = int(data.get("x")), int(data.get("y"))
    except (TypeError, ValueError):
        return _error("x and y are required integers")

    parent = manifest[scope_id]
    try:
        label = ("move" if child_id in world_grid.placements(parent) else "place")
        _snapshot(app, label=f"{label} {child_id} in {parent.get('name', scope_id)}")
        outcome = world_grid.place(manifest, scope_id, child_id, x, y,
                                   on_overlap=str(data.get("on_overlap") or "forbid"))
    except ValueError as exc:
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": outcome, **_grid_payload(manifest, scope_id, app.world.graph)})


# ─────────────────────── placing existing areas (task-528) ────────────────


def _set_area_membership(manifest: Dict[str, dict], area_id: str,
                         new_scope: str, previous_scope: Optional[str]) -> None:
    """Mirror a scope move in the manifest's denormalized ``area_ids`` lists.

    Thin wrapper over :func:`world_scopes.assign_area_membership`, which owns the
    rules (and the cell release on leaving a scope).
    """
    world_scopes.assign_area_membership(manifest, area_id, new_scope, previous_scope)


def _movable_area(graph, area_id: str):
    """The area node behind *area_id*, or ``(None, reason)`` saying why not.

    A generated area cannot be reassigned: it already owns a cell on the grid of
    the scope that generated it, and moving it would fight that scope. The
    refusal text matches :func:`handle_place_area` so both routes explain
    themselves the same way.
    """
    node = graph.get_node(area_id)
    if node is None:
        return None, f"No area '{area_id}' in the world"
    if getattr(node, "type", "") != "area":
        return None, f"'{area_id}' is a {getattr(node, 'type', '?')}, not an area"
    props = getattr(node, "properties", {}) or {}
    generated = props.get("generated")
    if generated:
        return None, (
            f"'{getattr(node, 'name', area_id)}' was generated by "
            f"'{generated.get('scope_id')}' and already owns its cell — "
            f"regenerating that scope would put it back. Paint or generate the "
            f"grid instead of moving a generated area.")
    return node, ""


def handle_scope_areas(app, scope_id):
    """POST /api/world/scopes/<scope_id>/areas — reassign areas to this scope.

    Body: ``{add: [area_id, ...], remove: [area_id, ...]}``. **Membership only**
    (task-539): this moves ``world_scope_id`` and the manifest's ``area_ids``
    mirror, and nothing else. A child scope's interior areas belong to that
    scope, but they do not each need a painted cell on the parent's grid — that
    is the distinction :func:`handle_place_area` cannot express, because placing
    an area also parks it on a cell.

    One request is **one undo step**, and ``add``/``remove`` are lists so a
    multi-selection of nodes moves at once. Leaving a scope releases any cell the
    area was parked on there; a cell it holds in *this* scope is untouched, so
    "make it a member of the scope it already sits on" is a no-op.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)

    def _ids(key):
        raw = data.get(key) or []
        if isinstance(raw, str):
            raw = [raw]
        return [str(a).strip() for a in raw if str(a).strip()]

    add = _ids("add")
    remove = _ids("remove")
    if not add and not remove:
        return _error("add and/or remove must list at least one area id")
    overlap = sorted(set(add) & set(remove))
    if overlap:
        return _error(f"{', '.join(overlap)} is both added and removed")

    graph = app.world.graph
    # Validate everything before the snapshot, so a refusal leaves no junk undo
    # entry and no half-applied move.
    plan = []
    for area_id in add:
        node, reason = _movable_area(graph, area_id)
        if node is None:
            return _error(reason)
        plan.append((area_id, (node.properties or {}).get("world_scope_id"), scope_id))
    for area_id in remove:
        node, reason = _movable_area(graph, area_id)
        if node is None:
            return _error(reason)
        plan.append((area_id, (node.properties or {}).get("world_scope_id"), None))

    _snapshot(app, label=(f"move {len(add)} area(s) to {manifest[scope_id].get('name', scope_id)}"
                          if add else f"remove {len(remove)} area(s) from "
                                      f"{manifest[scope_id].get('name', scope_id)}"))
    outcomes = {}
    for area_id, previous, target in plan:
        try:
            _set_area_membership(manifest, area_id, target, previous)
        except ValueError as exc:
            return _error(str(exc))
        node = graph.get_node(area_id)
        props = dict(getattr(node, "properties", {}) or {})
        released = False
        if target:
            props["world_scope_id"] = target
            if previous and previous != target:
                # The cell it was parked on belonged to the scope it just left.
                released = bool(props.pop("cell", None))
                props.pop("x", None)
                props.pop("y", None)
        else:
            props.pop("world_scope_id", None)
            released = bool(props.pop("cell", None))
            props.pop("x", None)
            props.pop("y", None)
        node.properties = props
        outcomes[area_id] = "assigned" if target else "removed"
        if released:
            outcomes[f"{area_id}:cell"] = "released"
    _commit(app, manifest)
    return jsonify({"status": "ok", "scope_id": scope_id, "areas": outcomes,
                    **_grid_payload(manifest, scope_id, graph)})


def handle_place_area(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/place_area — park an area on a cell.

    Body: ``{area_id, x, y, on_overlap?}``. The counterpart of
    ``/grid/generate``: generate makes areas *from* cells, this puts an area the
    author already wrote *onto* one (task-528).

    One request, one undo step, because the node side and the manifest side are
    useless apart: ``properties.cell``/``x``/``y`` place the area on the map,
    ``world_scope_id`` makes it a member of the scope, and ``area_placements`` is
    the record that stops generate from compiling a second area on that cell.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    record = manifest[scope_id]
    area_id = str(data.get("area_id") or "").strip()
    if not area_id:
        return _error("area_id is required")
    try:
        x, y = int(data.get("x")), int(data.get("y"))
    except (TypeError, ValueError):
        return _error("x and y are required integers")
    on_overlap = str(data.get("on_overlap") or "forbid")

    graph = app.world.graph
    node = graph.get_node(area_id)
    if node is None:
        return _error(f"No area '{area_id}' in the world")
    if getattr(node, "type", "") != "area":
        return _error(f"'{area_id}' is a {getattr(node, 'type', '?')}, not an area")
    props = getattr(node, "properties", {}) or {}
    if props.get("generated"):
        return _error(
            f"'{getattr(node, 'name', area_id)}' was generated by "
            f"'{props['generated'].get('scope_id')}' and already owns its cell — "
            f"regenerating that scope would put it back. Paint or generate the grid "
            f"instead of moving a generated area.")

    # Validate before the snapshot so a refusal does not leave a junk undo entry.
    if not world_grid.has_grid(record):
        return _error(f"Scope '{scope_id}' has no grid to place on")
    if not world_grid.in_bounds(record, x, y):
        return _error(f"cell ({x},{y}) is outside the grid")
    occupant = world_grid.area_placement_at(record, x, y)
    if occupant and occupant != area_id and on_overlap != "displace":
        other = graph.get_node(occupant)
        return _error(
            f"cell ({x},{y}) already holds "
            f"'{getattr(other, 'name', occupant) if other else occupant}'; "
            f"unplace it first or displace it")

    try:
        _snapshot(app, label=f"place {getattr(node, 'name', area_id)} on {record.get('name', scope_id)}")
        outcome = world_grid.place_area(manifest, scope_id, area_id, x, y,
                                        on_overlap=on_overlap)
    except ValueError as exc:
        return _error(str(exc))

    # `cell` is what flips the map into painted-grid mode; `x`/`y` are the canvas
    # coordinates the layout reads (cell * 40, the compiler's own unit pair).
    previous_scope = props.get("world_scope_id")
    new_props = dict(props)
    new_props["world_scope_id"] = scope_id
    new_props["cell"] = {"x": x, "y": y}
    new_props["x"] = x * world_compile.CELL_CANVAS_UNITS
    new_props["y"] = y * world_compile.CELL_CANVAS_UNITS
    node.properties = new_props
    if occupant and occupant != area_id and on_overlap == "displace":
        displaced = graph.get_node(occupant)
        if displaced is not None:
            dprops = dict(getattr(displaced, "properties", {}) or {})
            dprops.pop("cell", None)
            displaced.properties = dprops
    _set_area_membership(manifest, area_id, scope_id, previous_scope)
    _commit(app, manifest)
    return jsonify({"status": outcome, "area_id": area_id, "cell": {"x": x, "y": y},
                    **_grid_payload(manifest, scope_id, graph)})


def handle_unplace_area(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/unplace_area — free an area's cell.

    Body: ``{area_id}``. The area itself survives, and so does its scope
    membership; only the position goes, so the graph places it by physics again
    and the cell is free for a biome to be painted on it.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    area_id = str(data.get("area_id") or "").strip()
    if not area_id:
        return _error("area_id is required")
    if area_id not in world_grid.area_placements(manifest[scope_id]):
        return _error(f"'{area_id}' is not placed on this grid")
    graph = app.world.graph
    node = graph.get_node(area_id)

    _snapshot(app, label=f"unplace {getattr(node, 'name', area_id)}")
    world_grid.unplace_area(manifest, scope_id, area_id)
    if node is not None:
        new_props = dict(getattr(node, "properties", {}) or {})
        for key in ("cell", "x", "y"):
            new_props.pop(key, None)
        node.properties = new_props
    _commit(app, manifest)
    return jsonify({"status": "unplaced", "area_id": area_id,
                    **_grid_payload(manifest, scope_id, graph)})


#: Image types the reference picker may offer (mirrors the background uploader).
_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"}


def handle_promote_scope(app):
    """POST /api/world/promote — make a selection of areas a child scope (task-535).

    Body: ``{scope_id, name, area_ids, parent_id?, cell?: {x, y}, entry_area_id?,
    mode?, enter?, leave?}``.

    One undoable step for the whole thing, because it *is* one thing: the areas
    change scope, the scope record appears, the placement is written and the
    gateway is minted. Split across two requests the world would pass through a
    state where the areas belong to a scope that does not exist yet.

    ``cell`` is the parent's painted cell the gateway opens from, and it has to be
    a place — the refusal says so rather than minting a way from a wall. Without
    ``parent_id`` the selection still becomes a scope, just an unplaced one: the
    author may be grouping before deciding where it lives.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    area_ids = data.get("area_ids")
    if isinstance(area_ids, str):
        area_ids = [area_ids]
    if not area_ids:
        return _error("area_ids is required — select the areas to promote")
    cell = data.get("cell")
    where = None
    if isinstance(cell, dict):
        try:
            where = (int(cell.get("x")), int(cell.get("y")))
        except (TypeError, ValueError):
            return _error("cell must be {'x': int, 'y': int}")
    elif cell is not None:
        return _error("cell must be {'x': int, 'y': int}")

    _snapshot(app, label="promote selection to a scope")
    try:
        result = world_scopes.promote_to_scope(
            manifest, app.world.graph,
            scope_id=str(data.get("scope_id") or ""),
            name=str(data.get("name") or ""),
            area_ids=area_ids,
            parent_id=data.get("parent_id"),
            cell=where,
            entry_area_id=data.get("entry_area_id"),
            mode=str(data.get("mode") or "interior"),
            enter=data.get("enter"),
            leave=data.get("leave"),
        )
    except ValueError as exc:
        # The snapshot was pushed before the call, so a refusal would leave an undo
        # step that does nothing. Better: nothing happened, and nothing to undo.
        app._undo_stack.pop()
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": "promoted", **result,
                    "scope": world_scopes.scope_summary(
                        manifest, app.world.graph,
                        app.world.player_manager.players, result["scope_id"])})


def handle_generate_interior(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/interior — paint a plan (task-567).

    Body: ``{building, storeys?}``.

    **Paints, does not generate areas.** The plan goes into the scope's grid as
    ordinary cells and the scope stays ``unmade``, so the author edits it in the
    painter and then runs ⚙ Generate like any other hand-drawn interior. That is
    deliberate: one code path turns paint into places (:mod:`engine.world_compile`),
    and a generated interior is not a second kind of thing.

    Author edits are protected and **detected, not locked** — the scope records
    what the generator wrote, and a cell whose value no longer matches is left
    alone. So a re-run after editing does half its work and says which half, and a
    cell the author never touched is brought back in line with the plan.

    One undoable step, like every other grid write.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    building = str(data.get("building") or "").strip()
    if not building:
        return _error("building is required — a building type, e.g. 'tavern'")
    if not biomes_mod.is_building(building):
        return _error(f"{building!r} is not a building type")
    storeys = data.get("storeys")
    try:
        storeys = int(storeys) if storeys is not None else None
    except (TypeError, ValueError):
        return _error("storeys must be a whole number")

    _snapshot(app, label=f"interior {building}")
    try:
        patch = interior_gen.generate_interior(
            manifest, scope_id, building, storeys=storeys)
    except ValueError as exc:
        app._undo_stack.pop()
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": "painted",
                    "building": building,
                    "scope_id": scope_id,
                    "report": patch.report.to_dict(),
                    **_grid_payload(manifest, scope_id, app.world.graph)})


def handle_boundary_override(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/boundary_override — own a seam.

    The compiler mints a way from a hand-placed area to every painted cell
    touching it (task-528). That way is a *draft*: this route is how the author
    takes it over, in one undoable step, so the decision survives a later
    Generate instead of being overwritten by it.

    Body: ``{way_id, action, hand_way_id?}``.

    - ``action: "suppress"`` — the author deleted this way and does not want it
      back. The generated node is removed now, and the pair is never re-minted.
    - ``action: "hand"`` — the author wrote their own way for this seam and names
      it in ``hand_way_id``. The generated one is removed, so the seam is not
      walkable twice.
    - ``action: "auto"`` (or omitted) — hand the seam back: drop the record, and
      the next Generate mints it again. Not a third decision, just the absence of
      one.

    Refuses a way this scope did not generate, and a generated way that is not a
    boundary way (a road between two compiled areas is the compiler's to own
    regardless of what the author does to it here).
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    record = manifest[scope_id]
    way_id = str(data.get("way_id") or "").strip()
    if not way_id:
        return _error("way_id is required")
    action = str(data.get("action") or "auto").strip()
    hand_way_id = str(data.get("hand_way_id") or "").strip() or None

    graph = app.world.graph
    node = graph.get_node(way_id)
    if node is None and not world_grid.boundary_override(record, way_id):
        return _error(f"no way {way_id!r} to override; generate the scope first", 404)
    generated = (getattr(node, "properties", {}) or {}).get("generated") or {}
    props = getattr(node, "properties", {}) or {}
    # A boundary way is recognised by its **endpoints**: one of them is a
    # hand-placed area of this scope. Everything else the compiler mints is its
    # own to own — a road between two compiled areas is not something the author
    # overrides here, they edit it in the graph like any other generated node.
    placed_ids = set(world_grid.area_placements(record))
    endpoints = {str(props.get("area_from_id") or ""), str(props.get("area_to_id") or "")}
    if node is not None and not (endpoints & placed_ids):
        if not generated:
            return _error(
                f"'{getattr(node, 'name', way_id)}' is hand-authored; there is "
                f"nothing to override — edit or delete the way itself")
        return _error(
            f"'{getattr(node, 'name', way_id)}' does not touch a hand-placed "
            f"area of '{record.get('name', scope_id)}'; only the ways minted "
            f"around a placement can be overridden")
    if action == "auto":
        world_grid.set_boundary_override(record, way_id, None)
    else:
        try:
            world_grid.set_boundary_override(record, way_id, action,
                                             hand_way_id=hand_way_id)
        except ValueError as exc:
            return _error(str(exc))

    # Removing the node is part of the same operation, not a second one: leaving
    # it would mean a suppressed way still standing in the graph until the next
    # Generate, which is the exact "I deleted this and it came back" the record
    # exists to prevent. One snapshot, so one undo reverts both halves.
    deleted = False
    if node is not None and action in ("suppress", "hand"):
        _snapshot(app, label=f"override {getattr(node, 'name', way_id)}")
        graph.remove_node(way_id)
        deleted = True
    elif node is None:
        _snapshot(app, label=f"override {way_id}")
    _commit(app, manifest)
    return jsonify({"status": "cleared" if action == "auto" else action,
                    "way_id": way_id, "deleted_node": deleted,
                    **_grid_payload(manifest, scope_id, graph)})


def _background_urls(app):
    """Background images available to a reference overlay.

    The scenario's configured map layers first (the art you already see on the
    graph), then every file in the backgrounds folder — so you can reuse the
    existing picture instead of re-uploading it.
    """
    urls = []
    seen = set()

    def add(url):
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    bg = getattr(app.world, "graph_background", None) or {}
    for layer in (bg.get("layers") or []):
        if isinstance(layer, dict):
            add(layer.get("image") or layer.get("imagePath") or layer.get("imageSrc"))
    add(bg.get("image"))  # legacy single-image form

    folder = os.path.join(app.root_path, "static", "images", "backgrounds")
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext in _IMAGE_EXTS:
                add(f"/static/images/backgrounds/{name}")
    return urls


def handle_list_backgrounds(app):
    """GET /api/world/painter/backgrounds — images usable as a reference."""
    return jsonify({"images": _background_urls(app)})


def handle_set_reference(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/reference — reference image.

    Body: ``{image, opacity?, visible?, rect?, crop?, reset?}``. ``image`` of
    ``null`` clears it. ``rect`` (cell units) and ``crop`` (normalized source
    window) are the author's move/resize/crop of the picture; ``reset: true``
    drops them back to auto-fit. The image is a *reference* only and never
    compiles into areas/ways.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    record = manifest[scope_id]
    image = data.get("image")
    if image not in (None, "") and not str(image).startswith(("/static/", "http", "data:")):
        return _error("image must be a /static/ path, URL, or data URI")
    try:
        _snapshot(app, label=f"set reference on {record.get('name', scope_id)}")
        world_grid.set_reference(record, image,
                                 opacity=data.get("opacity"),
                                 visible=data.get("visible"),
                                 rect=data.get("rect"),
                                 crop=data.get("crop"),
                                 reset=bool(data.get("reset")))
    except ValueError as exc:
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": "saved", **_grid_payload(manifest, scope_id, app.world.graph)})


def handle_paint_batch(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/paint_batch — paint many cells.

    Body: ``{edits: [{layer, x, y, value}, ...]}``. A route/trail tool emits
    hundreds of edits; one request (and one undo snapshot) keeps a 240-cell
    road from being 240 round-trips.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    edits = data.get("edits")
    if not isinstance(edits, list) or not edits:
        return _error("edits must be a non-empty list")
    if len(edits) > 20000:
        return _error("too many edits in one request (max 20000)")
    record = manifest[scope_id]
    try:
        _snapshot(app, label=f"paint route on {record.get('name', scope_id)}")
        count = world_grid.paint_many(record, edits)
    except ValueError as exc:
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": "painted", "count": count,
                    **_grid_payload(manifest, scope_id, app.world.graph)})


def handle_generate_scope(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/generate — make this scope real.

    Two ways to make a scope, one verb:

    - a scope that carries a **recipe** is generated by that recipe
      (``_generate_from_recipe``) — a deterministic patch of areas, ways and
      placed items, which is how an unmade scope with no grid (Pines Apartment
      3B) becomes walkable;
    - a scope with a **painted grid** is compiled by the grid compiler, below.

    Body: ``{region_merge?, seed?, allow_regenerate?, tick?, entry_area_id?}``. A
    second apply is rejected (409) unless ``allow_regenerate`` — the once-only
    guard that stops a re-run from duplicating nodes or clobbering a later hand
    edit.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    record = manifest[scope_id]
    allow_regenerate = bool(data.get("allow_regenerate"))
    if record.get("state") == generation.MATERIALIZED and not allow_regenerate:
        return _error(
            f"Scope '{scope_id}' is already materialized; pass allow_regenerate "
            f"to re-run generation", 409)

    tick = data.get("tick")
    if tick is None:
        tick = int(getattr(app.world, "turn_number", 0) or 0)

    if record.get("recipe"):
        return _generate_from_recipe(app, manifest, record, scope_id, data,
                                     allow_regenerate=allow_regenerate, tick=tick)

    # task-569: the item library is what turns a biome's resource_distribution
    # tags into real items placed in the compiled areas.
    index = LibraryIndex.from_directory(
        Path(app.config["DATA_DIR"]) / "library" / "items")
    try:
        patch = world_compile.compile_grid(
            manifest, scope_id,
            region_merge=bool(data.get("region_merge")),
            link_islands=bool(data.get("link_islands", True)),
            seed=data.get("seed"),
            tick=int(tick),
            # Hand-placed areas are existing nodes, and their boundary ways have
            # to speak their names (task-528).
            graph=app.world.graph,
            spawn_index=index,
            resources_per_area=int(data.get("resources_per_area") or 1))
    except ValueError as exc:
        # Missing scope, no grid, no painted cells, or a baked zone.
        return _error(str(exc))

    # A painted region scales areas = cells; refuse a patch big enough to choke
    # the graph view rather than silently minting tens of thousands of nodes.
    max_nodes = int(data.get("max_nodes") or 20000)
    if len(patch.nodes) > max_nodes:
        return _error(
            f"that patch would create {len(patch.nodes)} nodes (limit {max_nodes}); "
            f"merge same-biome or generate a smaller scope", 400)

    # Compile is pure; only now is it safe to snapshot before touching the world.
    _snapshot(app, label=f"generate {record.get('name', scope_id)}")
    try:
        report = generation.apply_patch(app.world.graph, manifest, patch,
                                        allow_regenerate=allow_regenerate)
    except ValueError as exc:
        return _error(str(exc), 409)
    _commit(app, manifest)
    payload = _grid_payload(manifest, scope_id, app.world.graph)
    payload["status"] = "generated"
    payload["report"] = report.to_dict()
    return jsonify(payload)


def _generate_from_recipe(app, manifest: Dict[str, dict], record: Dict[str, dict],
                          scope_id: str, data: dict, *, allow_regenerate: bool,
                          tick: int):
    """POST .../grid/generate for a scope that carries a **recipe** (task-400).

    The recipe is a pure function of (scope id, seed, library, entry area), so
    this is a build of a patch and one ``apply_patch`` — the same contract the
    grid compiler uses, which is the point: an unmade scope is minted the same
    way whether it was painted or declared, and a second call is refused by
    ``apply_patch`` rather than duplicating the interior.

    This is the production caller ``generation_recipes`` was written for. Without
    it ``apartment.v1`` was reachable only from its own tests: the scope record
    declared a recipe that nothing ran, and this endpoint could only compile a
    painted grid, so an unmade scope *with* a recipe could not be generated at
    all.
    """
    recipe_id = record.get("recipe")
    recipe = generation_recipes.get_recipe(recipe_id)
    if recipe is None:
        return _error(
            f"scope {scope_id!r} asks for recipe {recipe_id!r}, which is not "
            f"registered (known: {', '.join(sorted(generation_recipes.RECIPES)) or 'none'})",
            400)

    seed = data.get("seed") or record.get("seed")
    if not seed:
        return _error(
            f"scope {scope_id!r} has no seed; pass one in the body or store it on "
            f"the scope — generation is only reproducible with a seed", 400)

    entry_area_id = data.get("entry_area_id") or _recipe_entry_area(manifest, record)
    index = LibraryIndex.from_directory(Path(app.config["DATA_DIR"]) / "library" / "items")
    patch = recipe(scope_id, seed=str(seed), index=index,
                   entry_area_id=entry_area_id, tick=int(tick))

    max_nodes = int(data.get("max_nodes") or 20000)
    if len(patch.nodes) > max_nodes:
        return _error(
            f"that patch would create {len(patch.nodes)} nodes (limit {max_nodes})",
            400)

    _snapshot(app, label=f"generate {record.get('name', scope_id)}")
    try:
        report = generation.apply_patch(app.world.graph, manifest, patch,
                                        allow_regenerate=allow_regenerate)
    except ValueError as exc:
        return _error(str(exc), 409)
    _commit(app, manifest)
    payload = _grid_payload(manifest, scope_id, app.world.graph)
    payload["status"] = "generated"
    payload["report"] = report.to_dict()
    return jsonify(payload)


def handle_ungenerate_scope(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/ungenerate — delete generated nodes.

    The inverse of Generate: removes the scope's generated areas/ways/gateways
    (and parent gateways into it) but keeps the scope record — its painted grid,
    reference, map offset and placements — and resets it to ``unmade``, so the
    author can regenerate a clean slate. Hand-authored nodes are never touched.
    """
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    _snapshot(app, label=f"ungenerate {manifest[scope_id].get('name', scope_id)}")
    try:
        result = world_scopes.ungenerate_scope(manifest, app.world.graph, scope_id)
    except ValueError as exc:
        return _error(str(exc))
    _commit(app, manifest)
    payload = _grid_payload(manifest, scope_id, app.world.graph)
    payload["status"] = "ungenerated"
    payload["deleted_nodes"] = result["deleted_nodes"]
    return jsonify(payload)


def handle_remove_feature(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/remove — remove a placement.

    Removes only the placement, never the child scope record: deleting a
    feature from a grid must not delete unrelated scopes it may parent.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    child_id = str(data.get("child_id") or "").strip()
    if not child_id:
        return _error("child_id is required")
    parent = manifest[scope_id]
    _snapshot(app, label=f"remove {child_id} from {parent.get('name', scope_id)}")
    removed = world_grid.remove(manifest, scope_id, child_id)
    if not removed:
        return _error(f"{child_id!r} is not placed in {scope_id!r}", 404)
    _commit(app, manifest)
    return jsonify({"status": "removed", **_grid_payload(manifest, scope_id, app.world.graph)})


def handle_rename_scope(app, scope_id):
    """POST /api/world/scopes/<scope_id>/rename — ``{name}``.

    Changes the **display name** only; the id (and every node reference) stays,
    so renaming never breaks areas, placements or the graph.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    _snapshot(app, label=f"rename {scope_id}")
    try:
        record = world_scopes.rename_scope(manifest, scope_id, data.get("name"))
    except ValueError as exc:
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": "renamed", "id": scope_id, "name": record["name"]})


def handle_delete_scope(app, scope_id):
    """POST /api/world/scopes/<scope_id>/delete — ``{cascade?}``.

    Removes the scope's record, unplaces it from parents, and deletes the nodes
    generation made for it. Refuses a scope that still has children unless
    ``cascade`` is set (see :func:`engine.world_scopes.delete_scope`).
    """
    data = request.get_json(silent=True) or {}
    cascade = str(data.get("cascade", "")).lower() in ("1", "true", "yes")
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    _snapshot(app, label=f"delete {scope_id}")
    try:
        result = world_scopes.delete_scope(manifest, app.world.graph, scope_id,
                                           cascade=cascade)
    except ValueError as exc:
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": "deleted", **result})


def handle_set_scope_offset(app, scope_id):
    """POST /api/world/scopes/<scope_id>/offset — ``{x, y}`` cells or ``{reset}``.

    Persists the map-canvas zone drag (task-523): the graph map layout adds this
    offset to the scope's painted coords, so a zone the author moves stays moved
    across reloads without editing the painter's cell coords. ``{reset: true}``
    returns the zone to its painted position.
    """
    data = request.get_json(silent=True) or {}
    manifest = _load(app)
    if scope_id not in manifest:
        return _error(f"Scope '{scope_id}' not found", 404)
    reset = str(data.get("reset", "")).lower() in ("1", "true", "yes")
    _snapshot(app, label=f"move zone {scope_id}")
    try:
        world_grid.set_map_offset(manifest[scope_id], x=data.get("x", 0.0),
                                  y=data.get("y", 0.0), reset=reset)
    except ValueError as exc:
        return _error(str(exc))
    _commit(app, manifest)
    return jsonify({"status": "offset", "id": scope_id,
                    "map_offset": world_grid.map_offset(manifest[scope_id])})
