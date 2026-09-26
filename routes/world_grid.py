"""Route registration for the WorldPainter grid API (task-495).

Thin registrar only — handlers live in ``routes/world_grid_ops.py``.
"""

from .world_grid_ops import (
    handle_create_scope,
    handle_delete_scope,
    handle_generate_scope,
    handle_list_backgrounds,
    handle_painter_vocabulary,
    handle_paint_batch,
    handle_paint_cell,
    handle_place_feature,
    handle_remove_feature,
    handle_rename_scope,
    handle_scope_grid,
    handle_set_reference,
    handle_set_scope_grid,
    handle_set_scope_offset,
    handle_ungenerate_scope,
)


def register_world_grid_routes(app):
    @app.route('/api/world/painter/vocabulary', methods=['GET'])
    def world_painter_vocabulary():
        return handle_painter_vocabulary(app)

    @app.route('/api/world/painter/backgrounds', methods=['GET'])
    def world_painter_backgrounds():
        return handle_list_backgrounds(app)

    @app.route('/api/world/scopes/<scope_id>/grid/reference', methods=['POST'])
    def world_scope_grid_reference(scope_id):
        return handle_set_reference(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/grid', methods=['GET'])
    def world_scope_grid(scope_id):
        return handle_scope_grid(app, scope_id)

    @app.route('/api/world/scopes', methods=['POST'])
    def world_scope_create():
        return handle_create_scope(app)

    @app.route('/api/world/scopes/<scope_id>/grid', methods=['POST'])
    def world_scope_grid_set(scope_id):
        return handle_set_scope_grid(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/grid/paint', methods=['POST'])
    def world_scope_grid_paint(scope_id):
        return handle_paint_cell(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/grid/paint_batch', methods=['POST'])
    def world_scope_grid_paint_batch(scope_id):
        return handle_paint_batch(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/grid/place', methods=['POST'])
    def world_scope_grid_place(scope_id):
        return handle_place_feature(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/grid/remove', methods=['POST'])
    def world_scope_grid_remove(scope_id):
        return handle_remove_feature(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/grid/generate', methods=['POST'])
    def world_scope_grid_generate(scope_id):
        return handle_generate_scope(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/grid/ungenerate', methods=['POST'])
    def world_scope_grid_ungenerate(scope_id):
        return handle_ungenerate_scope(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/rename', methods=['POST'])
    def world_scope_rename(scope_id):
        return handle_rename_scope(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/offset', methods=['POST'])
    def world_scope_offset(scope_id):
        return handle_set_scope_offset(app, scope_id)

    @app.route('/api/world/scopes/<scope_id>/delete', methods=['POST'])
    def world_scope_delete(scope_id):
        return handle_delete_scope(app, scope_id)
