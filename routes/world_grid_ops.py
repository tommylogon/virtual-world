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
from typing import Dict, List, Optional

from flask import jsonify, request

from engine import biomes as biomes_mod
from engine import generation, world_compile, world_grid, world_scopes


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


def _grid_payload(manifest: Dict[str, dict], scope_id: str) -> dict:
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
        },
        "grid": ({"w": w, "h": h, "cell_scale": (rec.get("grid") or {}).get("cell_scale", 1.0)}
                 if world_grid.has_grid(rec) else None),
        "mode": rec.get("mode"),
        "reference": world_grid.reference(rec),
        "layers": dict(rec.get("layers") or {}),
        "map_offset": world_grid.map_offset(rec),
        "placements": placements,
        "feature": world_grid.feature_layer(rec),
        "children": children,
        "parent": parent,
        "breadcrumb": _breadcrumb(manifest, scope_id),
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
    return jsonify(_grid_payload(manifest, scope_id))


def handle_painter_vocabulary(app):
    """GET /api/world/painter/vocabulary — the values a cell may be painted with.

    The editor needs the real ids, not free text: a biome id painted wrong does
    not error, it silently compiles a barren area (no tags → nothing forages or
    spawns there). Served from the taxonomy (``data/worldpainter/biomes.json``).
    """
    return jsonify({
        "biomes": [{"id": key, "name": (rec or {}).get("name", key)}
                   for key, rec in sorted(biomes_mod.biomes().items())],
        "features": [{"id": key, "name": (rec or {}).get("name", key)}
                     for key, rec in sorted(biomes_mod.features().items())],
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
    return jsonify({"status": "created", **_grid_payload(manifest, scope_id)})


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
    return jsonify({"status": "saved", **_grid_payload(manifest, scope_id)})


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
                    **_grid_payload(manifest, scope_id)})


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
    return jsonify({"status": outcome, **_grid_payload(manifest, scope_id)})


#: Image types the reference picker may offer (mirrors the background uploader).
_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"}


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
    return jsonify({"status": "saved", **_grid_payload(manifest, scope_id)})


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
                    **_grid_payload(manifest, scope_id)})


def handle_generate_scope(app, scope_id):
    """POST /api/world/scopes/<scope_id>/grid/generate — compile grid → nodes.

    The bridge from authoring to engine data (task-496 → task-398): compile the
    painted grid into a ``GenerationPatch`` and apply it once. Generated ``area``
    and ``way`` nodes load through the ordinary area/way conventions, so no
    engine change is needed — a painted world becomes a walkable one.

    Body: ``{region_merge?, seed?, allow_regenerate?, tick?}``. A second apply is
    rejected (409) unless ``allow_regenerate`` — the once-only guard that stops a
    re-run from duplicating nodes or clobbering a later hand edit.
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
    try:
        patch = world_compile.compile_grid(
            manifest, scope_id,
            region_merge=bool(data.get("region_merge")),
            link_islands=bool(data.get("link_islands", True)),
            seed=data.get("seed"),
            tick=int(tick))
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
    payload = _grid_payload(manifest, scope_id)
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
    payload = _grid_payload(manifest, scope_id)
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
    return jsonify({"status": "removed", **_grid_payload(manifest, scope_id)})


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
