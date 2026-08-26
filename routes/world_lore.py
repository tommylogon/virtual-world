import logging
import time
import random
from flask import Flask, request, jsonify
from logger import setup_logger
from .helpers import _save_scenario

logger = logging.getLogger(__name__)


def register_world_lore_routes(app):
    """Register world-lore API routes (CRUD for lore entries)."""

    @app.route('/api/world/lore', methods=['GET'])
    def get_world_lore():
        return jsonify({"lore": getattr(app.world, 'world_lore', [])})

    @app.route('/api/world/lore', methods=['POST'])
    def set_world_lore():
        data = request.get_json(force=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Expected JSON object"}), 400
        lore = data.get("lore", [])
        if not isinstance(lore, list):
            return jsonify({"error": "lore must be a list"}), 400
        app.world.world_lore = lore
        _save_scenario(app.world)
        return jsonify({"status": "success", "count": len(lore)})

    @app.route('/api/world/lore/entry', methods=['POST'])
    def add_world_lore_entry():
        data = request.get_json(force=True)
        lore = getattr(app.world, 'world_lore', [])
        entry = {
            "id": data.get("id", f"lore_{int(time.time()*1000)}_{random.randint(0,999)}"),
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "category": data.get("category", "general"),
            "tick_created": app.world.time_ticks,
            "importance": data.get("importance", 3),
            "tags": data.get("tags", []),
            "source": data.get("source", "manual")
        }
        lore.append(entry)
        app.world.world_lore = lore
        _save_scenario(app.world)
        return jsonify({"status": "success", "entry": entry}), 201

    @app.route('/api/world/lore/entry/<entry_id>', methods=['POST'])
    def update_world_lore_entry(entry_id):
        data = request.get_json(force=True)
        lore = getattr(app.world, 'world_lore', [])
        for entry in lore:
            if entry.get("id") == entry_id:
                for key in ["title", "content", "category", "importance", "tags"]:
                    if key in data:
                        entry[key] = data[key]
                app.world.world_lore = lore
                _save_scenario(app.world)
                return jsonify({"status": "success", "entry": entry})
        return jsonify({"error": "Entry not found"}), 404

    @app.route('/api/world/lore/entry/<entry_id>', methods=['DELETE'])
    def delete_world_lore_entry(entry_id):
        lore = getattr(app.world, 'world_lore', [])
        new_lore = [e for e in lore if e.get("id") != entry_id]
        if len(new_lore) == len(lore):
            return jsonify({"error": "Entry not found"}), 404
        app.world.world_lore = new_lore
        _save_scenario(app.world)
        return jsonify({"status": "success"})
