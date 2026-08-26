import logging
from flask import Flask, request, jsonify
from logger import setup_logger

logger = logging.getLogger(__name__)


def register_narration_routes(app):
    """Register narration-related API routes (area context, action context, description, inject)."""

    @app.route('/api/area/description', methods=['GET'])
    def get_area_description_api():
        """Return the full rich area description (same as `look` command)."""
        try:
            desc = app.world.get_area_description()
            return jsonify({"description": desc})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/narration/context/area', methods=['GET'])
    def get_narration_area_context():
        """Get structured context for narrating the current area."""
        try:
            area_name = request.args.get('area')
            context = app.world.get_narration_context_for_area(area_name)
            if not context:
                return jsonify({"error": "Could not get area context"}), 400
            return jsonify(context)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/narration/context/action', methods=['POST'])
    def get_narration_action_context():
        """Get structured context for narrating an action."""
        try:
            data = request.get_json()
            actor = data.get('actor', app.world.active_player)
            action_type = data.get('action_type', 'action')
            description = data.get('description', '')
            area_name = data.get('area')
            context = app.world.get_narration_context_for_action(actor, action_type, description, area_name)
            if not context:
                return jsonify({"error": "Could not get action context"}), 400
            return jsonify(context)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/narration/inject', methods=['POST'])
    def inject_narration():
        """Inject narration text into the event log and turn events."""
        try:
            data = request.get_json()
            text = data.get('text', '')
            source = data.get('source', 'player')
            area_name = data.get('area')
            actor_name = data.get('actor')
            if not text.strip():
                return jsonify({"error": "Empty narration text"}), 400
            app.world.inject_narration(text, source=source, area_name=area_name, actor_name=actor_name)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
