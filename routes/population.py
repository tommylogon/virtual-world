"""Route registration for tag-chain area population (task-9).

Thin registrar only — the handlers live in ``routes/population_ops.py``.
"""

from .population_ops import handle_populate_area


def register_population_routes(app):
    @app.route('/api/populate/area/<area_id>', methods=['POST'])
    def populate_area(area_id):
        return handle_populate_area(app, area_id)
