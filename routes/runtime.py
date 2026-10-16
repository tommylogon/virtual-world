"""Runtime snapshot route registration.

@module runtime_routes
@contributes GET /api/runtime/state for the character-focused runtime projection
"""

from .runtime_ops import handle_runtime_state


def register_runtime_routes(app):
    @app.route("/api/runtime/state", methods=["GET"])
    def runtime_state():
        with app._vw_write_lock:
            return handle_runtime_state(app)
