import logging
from flask import Flask, request, jsonify
from .action_handlers import (
    _ACTIVITY_ALLOWED,
    _ACTION_BLOCK_ALLOWED,
    _ACTIVITY_NON_INTERRUPTING,
    _activity_cmd_allowed,
    _activity_gate,
    _action_block_gate,
    _parse_activity_args,
    _build_narration_context_for_current_area,
    handle_get_state,
    handle_autocomplete,
    handle_take_action,
    handle_process_emote,
    handle_llm_respond_post,
    handle_apply_turn_decay,
    handle_clear_turn_events,
)
from .timeskip_ops import handle_timeskip, handle_soak_declare, handle_soak_cancel

logger = logging.getLogger(__name__)


def _timeskip_busy():
    """A running skip owns the clock; other mutating calls must not interleave."""
    from engine import timeskip
    return timeskip.is_running()


def register_action_routes(app):
    @app.route('/api/state', methods=['GET'])
    def get_state():
        return handle_get_state(app)

    @app.route('/api/autocomplete', methods=['POST'])
    def autocomplete():
        return handle_autocomplete(app)

    @app.route('/api/action', methods=['POST'])
    def take_action():
        if _timeskip_busy():
            return jsonify({"error": "A timeskip is running."}), 409
        return handle_take_action(app)

    @app.route('/api/emote', methods=['POST'])
    def process_emote_endpoint():
        return handle_process_emote(app)

    @app.route('/api/llm_respond', methods=['POST'])
    def llm_respond_post():
        if _timeskip_busy():
            return jsonify({"error": "A timeskip is running."}), 409
        return handle_llm_respond_post(app)

    @app.route('/api/auto_dress', methods=['POST'])
    def auto_dress():
        from flask import request, jsonify
        data = request.get_json() or {}
        name = data.get('character') or data.get('char')
        if not name:
            return jsonify({"error": "Missing 'character'"}), 400
        try:
            output = app.world.auto_dress_character(name)
            return jsonify({"output": output})
        except Exception as e:
            return jsonify({"output": str(e), "success": False}), 400

    @app.route('/api/turn/apply', methods=['POST'])
    def apply_turn_decay():
        if _timeskip_busy():
            return jsonify({"error": "A timeskip is running."}), 409
        return handle_apply_turn_decay(app)

    @app.route('/api/turn/clear', methods=['POST'])
    def clear_turn_events():
        return handle_clear_turn_events(app)

    @app.route('/api/world/timeskip', methods=['POST'])
    def world_timeskip():
        return handle_timeskip(app)

    @app.route('/api/world/soak', methods=['POST'])
    def world_soak():
        return handle_soak_declare(app)

    @app.route('/api/world/soak', methods=['DELETE'])
    def world_soak_cancel():
        return handle_soak_cancel(app)
