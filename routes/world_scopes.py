"""Route registration for world-scope projections (task-397).

Thin registrar only — handlers live in ``routes/world_scopes_ops.py``.
"""

from .world_scopes_ops import (
    handle_scope_detail,
    handle_scope_graph,
    handle_scope_observe,
    handle_scopes_root,
)


def register_world_scopes_routes(app):
    @app.route('/api/world/scopes', methods=['GET'])
    def world_scopes_root():
        return handle_scopes_root(app)

    @app.route('/api/world/scopes/<scope_id>', methods=['GET'])
    def world_scope_detail(scope_id):
        return handle_scope_detail(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/graph', methods=['GET'])
    def world_scope_graph(scope_id):
        return handle_scope_graph(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/observe', methods=['POST'])
    def world_scope_observe(scope_id):
        return handle_scope_observe(app, scope_id)
