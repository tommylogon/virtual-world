"""Route registration for the doc resolver (task-578).

Thin registrar only — handlers live in ``routes/docs_ops.py``.

@module docs
@contributes the /api/docs/resolve and /api/docs/body URLs
@docs none — route registrar; handlers live in routes/docs_ops.py
"""

from .docs_ops import handle_docs_body, handle_docs_resolve


def register_docs_routes(app):
    @app.route('/api/docs/resolve', methods=['GET'])
    def docs_resolve():
        return handle_docs_resolve(app)

    @app.route('/api/docs/body', methods=['GET'])
    def docs_body():
        return handle_docs_body(app)
