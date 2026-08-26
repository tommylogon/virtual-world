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
    handle_apply_turn_decay,
    handle_clear_turn_events,
)

logger = logging.getLogger(__name__)


def register_action_routes(app):
    @app.route('/api/state', methods=['GET'])
    def get_state():
        return handle_get_state(app)

    @app.route('/api/autocomplete', methods=['POST'])
    def autocomplete():
        return handle_autocomplete(app)

    @app.route('/api/action', methods=['POST'])
    def take_action():
        return handle_take_action(app)

    @app.route('/api/emote', methods=['POST'])
    def process_emote_endpoint():
        return handle_process_emote(app)

    @app.route('/api/turn/apply', methods=['POST'])
    def apply_turn_decay():
        return handle_apply_turn_decay(app)

    @app.route('/api/turn/clear', methods=['POST'])
    def clear_turn_events():
        return handle_clear_turn_events(app)
