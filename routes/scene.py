"""Scene snapshot route for the human turn panel (task-333 Phase 1)."""

import logging

from flask import jsonify, request

from engine.scene_snapshot import build_scene

logger = logging.getLogger(__name__)


def register_scene_routes(app):
    """Register /api/scene/<player> — the panel's one-call scene payload."""

    @app.route('/api/scene/<player_name>', methods=['GET'])
    def get_scene(player_name):
        """Everything the human turn panel's scene view renders, in one call."""
        try:
            return jsonify(build_scene(app.world, player_name))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            logger.exception("Error building scene for %s", player_name)
            return jsonify({"error": str(exc)}), 500
