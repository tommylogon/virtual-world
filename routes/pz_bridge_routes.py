"""PZ Bridge proxy routes — expose the in-game PZBridge mod REST API.

Lives under /api/pz/ so the Flask UI / agents can drive Project Zomboid
NPCs through the viwo backend without talking to the bridge directly.
"""
import logging
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)


def get_adapter(app):
    return getattr(app, 'pz_adapter', None)


def register_pz_bridge_routes(app):
    bp = Blueprint('pz_bridge', __name__)

    @bp.route('/api/pz/status', methods=['GET'])
    def pz_status():
        ad = get_adapter(app)
        if ad is None:
            return jsonify({"status": "offline", "error": "PZ adapter not configured"})
        return jsonify(ad.snapshot())

    @bp.route('/api/pz/snapshot', methods=['GET'])
    def pz_snapshot():
        ad = get_adapter(app)
        if ad is None:
            return jsonify({"status": "offline", "error": "PZ adapter not configured"})
        return jsonify(ad.snapshot())

    @bp.route('/api/pz/npc', methods=['GET', 'POST'])
    def pz_npc():
        ad = get_adapter(app)
        if ad is None:
            return jsonify({"status": "offline", "error": "PZ adapter not configured"})
        if request.method == 'GET':
            return jsonify(ad._request("npc"))
        payload = request.get_json(silent=True) or {}
        return jsonify(ad._request("npc", payload))

    @bp.route('/api/pz/npc/<name>', methods=['GET'])
    def pz_npc_sheet(name):
        ad = get_adapter(app)
        if ad is None:
            return jsonify({"status": "offline", "error": "PZ adapter not configured"})
        resp = ad._request("npc/" + name)
        return jsonify(resp)

    @bp.route('/api/pz/act', methods=['POST'])
    def pz_act():
        ad = get_adapter(app)
        if ad is None:
            return jsonify({"status": "offline", "error": "PZ adapter not configured"})
        payload = request.get_json(silent=True) or {}
        name = payload.get('npc') or payload.get('name')
        action = payload.get('action')
        if not name or not action:
            return jsonify({"status": "error", "message": "npc and action required"}), 400
        return jsonify(ad.act(name, action, payload.get('params') or {}))

    @bp.route('/api/pz/zone', methods=['GET'])
    def pz_zone():
        ad = get_adapter(app)
        if ad is None:
            return jsonify({"status": "offline", "error": "PZ adapter not configured"})
        resp = ad._request("zone")
        return jsonify(resp)

    bp.before_app_request(_decorate)
    app.register_blueprint(bp)


def _decorate():
    """No-op hook kept for symmetry with the route module pattern."""
    pass