"""Route registration for structure templates (task-357).

Thin registrar only — the handlers live in ``routes/structures_ops.py``.
"""

from .structures_ops import (
    handle_structures_delete,
    handle_structures_list,
    handle_structures_materialize,
    handle_structures_preview,
    handle_structures_save,
)


def register_structures_routes(app):
    @app.route('/api/structures', methods=['GET'])
    def structures_list():
        return handle_structures_list(app)

    @app.route('/api/structures/preview', methods=['POST'])
    def structures_preview():
        return handle_structures_preview(app)

    @app.route('/api/structures/save', methods=['POST'])
    def structures_save():
        return handle_structures_save(app)

    @app.route('/api/structures/<structure_id>/materialize', methods=['POST'])
    def structures_materialize(structure_id):
        return handle_structures_materialize(app, structure_id)

    @app.route('/api/structures/<structure_id>', methods=['DELETE'])
    def structures_delete(structure_id):
        return handle_structures_delete(app, structure_id)
