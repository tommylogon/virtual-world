import logging
from flask import Flask, request, jsonify
from .player_ops import (
    handle_get_players,
    handle_get_emotions,
    handle_spike_emotion,
    handle_get_conditions,
    handle_create_player,
    handle_set_active_player,
    handle_delete_player,
    handle_kill_player,
    handle_move_player,
    handle_player_speak,
    handle_update_player,
    handle_import_player,
    handle_generate_character_description,
    handle_get_vital,
    handle_update_vital,
)

logger = logging.getLogger(__name__)


def register_players_routes(app):
    @app.route('/api/players', methods=['GET'])
    def api_get_players():
        return handle_get_players(app)

    @app.route('/api/players/<name>/emotions', methods=['GET'])
    def api_get_emotions(name):
        return handle_get_emotions(app, name)

    @app.route('/api/players/<name>/emotions', methods=['POST'])
    def api_spike_emotion(name):
        return handle_spike_emotion(app, name)

    @app.route('/api/conditions', methods=['GET'])
    def api_get_conditions():
        return handle_get_conditions(app)

    @app.route('/api/players', methods=['POST'])
    def api_create_player():
        return handle_create_player(app)

    @app.route('/api/players/active', methods=['POST'])
    def api_set_active_player():
        return handle_set_active_player(app)

    @app.route('/api/players/<name>', methods=['DELETE'])
    def api_delete_player(name):
        return handle_delete_player(app, name)

    @app.route('/api/players/<name>/kill', methods=['POST'])
    def api_kill_player(name):
        return handle_kill_player(app, name)

    @app.route('/api/players/<name>/move', methods=['POST'])
    def api_move_player(name):
        return handle_move_player(app, name)

    @app.route('/api/players/<name>/speak', methods=['POST'])
    def api_player_speak(name):
        return handle_player_speak(app, name)

    @app.route('/api/players/<name>', methods=['POST'])
    def api_update_player(name):
        return handle_update_player(app, name)

    @app.route('/api/players/import', methods=['POST'])
    def import_player():
        return handle_import_player(app)

    @app.route('/api/players/<name>/generate-description', methods=['POST'])
    def api_generate_character_description(name):
        return handle_generate_character_description(app, name)

    @app.route('/api/players/<name>/vitals/<vital_name>', methods=['GET'])
    def api_get_vital(name, vital_name):
        return handle_get_vital(app, name, vital_name)

    @app.route('/api/players/<name>/vitals/<vital_name>', methods=['PATCH'])
    def api_update_vital(name, vital_name):
        return handle_update_vital(app, name, vital_name)
