import logging
from flask import Flask, request, jsonify
from .player_ops import (
    handle_get_players,
    handle_get_emotions,
    handle_spike_emotion,
    handle_map_player_emotions,
    handle_get_relationship_profiles,
    handle_learn_names,
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
    handle_get_character_record,
    handle_set_character_record,
    handle_clear_character_record,
    handle_character_affect,
    handle_get_vital,
    handle_update_vital,
    handle_get_player_map,
    handle_mark_visited,
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

    @app.route('/api/players/<name>/emotions/map', methods=['POST'])
    def api_map_emotion(name):
        return handle_map_player_emotions(app, name)

    @app.route('/api/players/<name>/relationships/profiles', methods=['GET'])
    def api_relationship_profiles(name):
        return handle_get_relationship_profiles(app, name)

    @app.route('/api/players/<name>/names', methods=['POST'])
    def api_learn_names(name):
        return handle_learn_names(app, name)

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

    @app.route('/api/players/<name>/record', methods=['GET'])
    def api_get_character_record(name):
        return handle_get_character_record(app, name)

    @app.route('/api/players/<name>/record', methods=['PUT'])
    def api_set_character_record(name):
        return handle_set_character_record(app, name)

    @app.route('/api/players/<name>/record', methods=['DELETE'])
    def api_clear_character_record(name):
        return handle_clear_character_record(app, name)

    @app.route('/api/players/<name>/affect', methods=['GET', 'POST'])
    def api_character_affect(name):
        return handle_character_affect(app, name)

    @app.route('/api/players/<name>/vitals/<vital_name>', methods=['GET'])
    def api_get_vital(name, vital_name):
        return handle_get_vital(app, name, vital_name)

    @app.route('/api/players/<name>/vitals/<vital_name>', methods=['PATCH'])
    def api_update_vital(name, vital_name):
        return handle_update_vital(app, name, vital_name)

    @app.route('/api/players/<name>/map', methods=['GET'])
    def api_get_player_map(name):
        """task-677: the cells this character has been in, with what they last
        observed there. Separate from /api/state on purpose — that payload is
        ~2.48 MB polled every 1.5 s and must not grow a map payload."""
        return handle_get_player_map(app, name)

    @app.route('/api/players/<name>/map/visited', methods=['POST'])
    def api_mark_visited(name):
        """task-677: seed the map with places a character has been, by writing
        the same observation row an arrival writes."""
        return handle_mark_visited(app, name)

    @app.route('/api/abilities/curve', methods=['GET'])
    def api_ability_curve():
        """task-606: the scale-correct ability curve, so an author picking a size
        can read what that size expects instead of guessing."""
        from engine.abilities import describe_curve, stats_for_size
        from engine.size import SIZE_TIERS
        return jsonify({
            "curve": describe_curve(),
            "tiers": list(SIZE_TIERS),
            "abilities": ["STR", "DEX", "CON", "INT", "WIS", "CHA"],
            "defaults": {tier: stats_for_size(tier) for tier in SIZE_TIERS},
        })
