import os
import json
import time
import logging
from flask import Flask, request, jsonify
from virtual_world_engine import VirtualWorld
from logger import setup_logger
from .helpers import _save_game

logger = logging.getLogger(__name__)

_MAX_UNDO_DEPTH = 10


def _snapshot(world):
    """Capture a serializable snapshot of the world for undo/redo."""
    return (world.to_dict(), getattr(world, '_scenario_source', None))


def _push_undo_snapshot(app):
    """Save the current world state onto the undo stack and clear redo."""
    app._undo_stack.append(_snapshot(app.world))
    if len(app._undo_stack) > _MAX_UNDO_DEPTH:
        app._undo_stack.pop(0)
    app._redo_stack.clear()


def _restore_snapshot(app, state, source):
    """Replace app.world with a fresh instance loaded from a snapshot."""
    new_world = VirtualWorld()
    new_world.load_from_dict(state)
    new_world._scenario_source = source
    new_world.time_per_tick_minutes = getattr(app.world, 'time_per_tick_minutes', 5)
    app.world = new_world
    # Persist the restored state so a restart doesn't lose it (skip in tests)
    if not app.config.get('TESTING'):
        from .helpers import save_autosave
        save_autosave(app.world)


def register_saveload_routes(app):
    """Register save/load/reset API routes including save-game CRUD and scenario saving."""

    @app.route('/api/save', methods=['GET'])
    def save_world():
        try:
            return jsonify(app.world.to_dict())
        except Exception as e:
            logger.exception("Error in /api/save")
            return jsonify({"error": "Internal server error"}), 500

    @app.route('/api/load', methods=['POST'])
    def load_world():
        logger.info("POST /api/load called")
        try:
            data = request.get_json()
            if not data:
                logger.warning("No JSON data received")
                return jsonify({"error": "No data provided"}), 400

            # Log some stats about the incoming data
            num_areas = len(data.get('areas', {}))
            num_players = len(data.get('players', {}))
            logger.info(f"Loading world with {num_areas} areas, {num_players} players")

            start = time.time()
            _push_undo_snapshot(app)
            app.world.load_from_dict(data)
            # Save game loads (have _save_metadata) clear the scenario source
            if "_save_metadata" in data:
                app.world._scenario_source = None
            else:
                # Template/scenario load — save to scenarios dir so Save Scenario works
                scenario_name = data.get('_scenario_name') or data.get('name', 'unnamed')
                scenarios_dir = os.path.join(app.config['DATA_DIR'], 'scenarios')
                os.makedirs(scenarios_dir, exist_ok=True)
                scenario_path = os.path.join(scenarios_dir, f"{scenario_name}.json")
                with open(scenario_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                app.world._scenario_source = scenario_path
                logger.info(f"Saved loaded scenario to {scenario_path}")
            elapsed = (time.time() - start) * 1000
            logger.info(f"World loaded in {elapsed:.0f} ms")
            return jsonify({"status": "success"})
        except Exception as e:
            logger.exception("Error in /api/load")
            return jsonify({"error": str(e)}), 400

    @app.route('/api/reset', methods=['POST'])
    def reset_world():
        """Reload the world from the original scenario source, clearing all state."""
        try:
            # Snapshot current state onto the undo stack so undo can restore
            # any areas/connections that existed before the reset.
            _push_undo_snapshot(app)
            new_world = VirtualWorld()
            source = getattr(app.world, '_scenario_source', None)
            if source and os.path.exists(source):
                template_path = source
            else:
                template_path = os.path.join(app.root_path, 'world_template.json')
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8-sig') as f:
                    template_data = json.load(f)
                new_world.load_from_dict(template_data)
                new_world._scenario_source = template_path
                logger.info(f"Reset world from {template_path}")
            else:
                logger.warning("No scenario file found, using blank world")
            new_world.time_per_tick_minutes = getattr(app.world, 'time_per_tick_minutes', 5)
            app.world = new_world
            # Delete autosave so restart is truly clean and next server start doesn't load stale state
            from .helpers import AUTOSAVE_PATH
            if os.path.exists(AUTOSAVE_PATH):
                os.remove(AUTOSAVE_PATH)
                logger.info("Deleted autosave after reset")
            return jsonify({"status": "success"})
        except Exception as e:
            logger.exception("Error in /api/reset")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/undo', methods=['POST'])
    def undo_action():
        """Restore the world to its state before the last snapshot (e.g. reset)."""
        try:
            if not app._undo_stack:
                return jsonify({"error": "Nothing to undo"}), 400
            state, source = app._undo_stack.pop()
            # Push current state onto the redo stack
            app._redo_stack.append(_snapshot(app.world))
            if len(app._redo_stack) > _MAX_UNDO_DEPTH:
                app._redo_stack.pop(0)
            _restore_snapshot(app, state, source)
            logger.info("Undo: restored previous world state")
            return jsonify({"status": "success"})
        except Exception as e:
            logger.exception("Error in /api/undo")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/redo', methods=['POST'])
    def redo_action():
        """Re-apply a state that was undone."""
        try:
            if not app._redo_stack:
                return jsonify({"error": "Nothing to redo"}), 400
            state, source = app._redo_stack.pop()
            app._undo_stack.append(_snapshot(app.world))
            if len(app._undo_stack) > _MAX_UNDO_DEPTH:
                app._undo_stack.pop(0)
            _restore_snapshot(app, state, source)
            logger.info("Redo: restored next world state")
            return jsonify({"status": "success"})
        except Exception as e:
            logger.exception("Error in /api/redo")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/save-games', methods=['GET'])
    def list_save_games():
        saves_dir = os.path.join(app.root_path, 'saves')
        try:
            if not os.path.exists(saves_dir):
                return jsonify([])
            files = []
            for fname in sorted(os.listdir(saves_dir), reverse=True):
                if fname.endswith('.json'):
                    path = os.path.join(saves_dir, fname)
                    try:
                        with open(path, 'r', encoding='utf-8-sig') as f:
                            meta = json.load(f).get('_save_metadata', {})
                        files.append({
                            'filename': fname,
                            'name': meta.get('name', fname),
                            'scenario': meta.get('scenario', ''),
                            'timestamp': meta.get('timestamp', ''),
                            'tick': meta.get('tick', 0),
                            'turn': meta.get('turn', 0),
                            'player': meta.get('player', ''),
                            'size': os.path.getsize(path)
                        })
                    except Exception:
                        files.append({'filename': fname, 'name': fname})
            return jsonify(files)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/save-game', methods=['POST'])
    def save_game():
        data = request.get_json(force=True) or {}
        name = data.get('name')
        filename = _save_game(app.world, name)
        if filename:
            return jsonify({"status": "success", "filename": filename}), 201
        return jsonify({"error": "Could not save game"}), 500

    @app.route('/api/load-game/<filename>', methods=['POST'])
    def load_game(filename):
        saves_dir = os.path.join(app.root_path, 'saves')
        path = os.path.join(saves_dir, filename)
        if not os.path.exists(path):
            return jsonify({"error": "Save file not found"}), 404
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            _push_undo_snapshot(app)
            app.world.load_from_dict(data)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": f"Could not load save: {e}"}), 500

    @app.route('/api/save-game/<filename>', methods=['DELETE'])
    def delete_save_game(filename):
        saves_dir = os.path.join(app.root_path, 'saves')
        path = os.path.join(saves_dir, filename)
        if not os.path.exists(path):
            return jsonify({"error": "Save file not found"}), 404
        try:
            os.remove(path)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/save-scenario', methods=['POST'])
    def save_scenario():
        data = request.get_json() or {}
        name = data.get('name', '').strip() or None
        scenario_data = app.world.to_scenario_dict()
        return jsonify({"status": "success", "name": name or 'unnamed', "data": scenario_data})
