"""Route registration for in-app bug reports.

@module bug_reports
@contributes the POST /api/bugs/report route
@docs none — developer tooling; the contract is this module's own docstring

Thin registrar only — the handler lives in ``routes/bug_reports_ops.py``.
"""

from .bug_reports_ops import handle_bug_report


def register_bug_reports_routes(app):
    @app.route('/api/bugs/report', methods=['POST'])
    def bug_report():
        return handle_bug_report(app)