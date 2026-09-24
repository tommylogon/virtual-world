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
    """GET /api/world/scopes — top-level scope cards.

    ``?flat=1`` returns every scope depth-first with a ``depth`` field, which is
    what the graph view's scope picker needs (task-397 step 4).
    """
    manifest, graph, players = _parts(app)
    if str(request.args.get("flat", "")).lower() in ("1", "true", "yes"):
        return jsonify({"scopes": world_scopes.flat_scopes(manifest, graph, players)})
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


def handle_scope_subgraph(app, scope_id):
    """GET /api/world/scopes/<scope_id>/subgraph?include_items= — vis subgraph.

    The graph view loads this instead of the whole-world ``/api/graph/*`` when a
    scope is selected, so a huge painted world never ships every node to the
    browser (task-397 step 3 / task-400). Shape matches ``WorldGraph.to_dict``,
    plus the scope summary for the breadcrumb.
    """
    manifest, graph, players = _parts(app)
    if scope_id not in manifest:
        return jsonify({"error": f"Scope '{scope_id}' not found"}), 404
    include_items = str(request.args.get("include_items", "1")).lower() not in (
        "0", "false", "no")
    sub = world_scopes.project_subgraph(manifest, graph, players, scope_id,
                                        include_items=include_items)
    return jsonify({"scope": world_scopes.scope_summary(manifest, graph, players,
                                                        scope_id),
                    **sub})


def handle_scope_observe(app, scope_id):
    """POST /api/world/scopes/<scope_id>/observe — activation boundary (task-399).

    Opening a scope requests that its background residents become attended. The
    transition is *queued*, not applied inline: the turn loop flushes the batch
    at one tick boundary, so activate/offload stays atomic.
    """
    from engine import promotion

    manifest, _graph, _players = _parts(app)
    if scope_id not in manifest:
        return jsonify({"error": f"Scope '{scope_id}' not found"}), 404
    queued = promotion.activate_scope(app.world, scope_id)
    return jsonify({
        "scope_id": scope_id,
        "queued": sorted(queued),
        "pending": sorted(promotion.pending(app.world)),
    })
