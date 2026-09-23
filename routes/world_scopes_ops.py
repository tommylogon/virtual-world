"""Handlers for world-scope projections (task-397).

Read-only. Thin registrar lives in ``routes/world_scopes.py``.
"""

from flask import jsonify, request

from engine import world_scopes


def _parts(app):
    manifest = world_scopes.normalise_manifest(
        getattr(app.world, "world_scopes", {}) or {})
    players = getattr(getattr(app.world, "player_manager", None), "players", {}) or {}
    return manifest, app.world.graph, players


def handle_scopes_root(app):
    """GET /api/world/scopes — top-level scope cards."""
    manifest, graph, players = _parts(app)
    return jsonify(world_scopes.project(manifest, graph, players, "root"))


def handle_scope_detail(app, scope_id):
    """GET /api/world/scopes/<scope_id> — child cards, or leaf areas + boundary ways."""
    manifest, graph, players = _parts(app)
    if scope_id not in manifest:
        return jsonify({"error": f"Scope '{scope_id}' not found"}), 404
    return jsonify(world_scopes.project(manifest, graph, players, scope_id))


def handle_scope_graph(app, scope_id):
    """GET /api/world/scopes/<scope_id>/graph?depth=&include_items= — projection."""
    manifest, graph, players = _parts(app)
    if scope_id not in manifest:
        return jsonify({"error": f"Scope '{scope_id}' not found"}), 404
    try:
        depth = int(request.args.get("depth", 1))
    except (TypeError, ValueError):
        depth = 1
    include_items = str(request.args.get("include_items", "")).lower() in ("1", "true", "yes")
    return jsonify(world_scopes.project(manifest, graph, players, scope_id,
                                        depth=max(0, depth), include_items=include_items))
