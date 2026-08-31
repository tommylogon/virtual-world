import logging
from flask import Flask, request, jsonify
from logger import setup_logger
from embeddings import embed as _embed_text
from engine.equipment import EquipmentSystem

logger = logging.getLogger(__name__)


def register_settings_routes(app):
    """Register settings, debug, pathfinding, embeddings, and narration-mode API routes."""

    @app.route('/api/settings/ghost_mode', methods=['GET'])
    def get_ghost_mode():
        """Get the current ghost mode setting."""
        try:
            mode = getattr(app.world, 'ghost_mode', False)
            return jsonify({"ghost_mode": mode})
        except Exception as e:
            return jsonify({"ghost_mode": False, "error": str(e)})

    @app.route('/api/settings/ghost_mode', methods=['POST'])
    def set_ghost_mode():
        """Set ghost mode on or off."""
        data = request.get_json()
        enabled = data.get('ghost_mode', False)
        if not isinstance(enabled, bool):
            return jsonify({"error": "ghost_mode must be a boolean"}), 400
        app.world.ghost_mode = enabled
        logger.info(f"Ghost mode set to: {enabled}")
        if enabled:
            app.world.add_log_entry("[System] Ghost mode activated — the dead may walk.")
        else:
            app.world.add_log_entry("[System] Ghost mode deactivated.")
        return jsonify({"status": "success", "ghost_mode": enabled})

    @app.route('/api/debug/save_log', methods=['POST'])
    def save_debug_log():
        """Save a run log file for debugging. Returns the filename."""
        try:
            data = request.get_json() or {}
            filename = data.get('filename')
            log_file = app.world.save_run_log(filename)
            return jsonify({"status": "success", "filename": log_file})
        except Exception as e:
            logger.exception("Error saving run log")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/debug/state', methods=['GET'])
    def dump_debug_state():
        """Return a compact debug dump of the world state."""
        w = app.world
        dump = {
            "ghost_mode": w.ghost_mode,
            "active_player": w.active_player,
            "turn": w.turn_number,
            "ticks": w.time_ticks,
            "time": w.get_current_time(),
            "players": {pname: {"area": p.current_area, "state": p.state, "HP": p.vitals.get("HP")} for pname, p in w.players.items()},
            "log_count": len(w.game_log),
            "area_count": len(w.areas),
            "dead_players": w.get_all_dead_players(),
            "alive_players": w.get_all_alive_players()
        }
        return jsonify(dump)

    @app.route('/api/path', methods=['POST'])
    def api_get_path():
        """Find the first direction to move from one area to another."""
        data = request.get_json()
        from_area = data.get('from')
        to_area = data.get('to')
        if not from_area or not to_area:
            return jsonify({"error": "Missing 'from' or 'to'"}), 400
        direction = app.world.get_path_to(from_area, to_area)
        return jsonify({"direction": direction})

    @app.route('/api/settings/time_per_tick', methods=['GET'])
    def get_time_per_tick():
        try:
            minutes = getattr(app.world, 'time_per_tick_minutes', 5)
            return jsonify({"time_per_tick_minutes": minutes})
        except Exception as e:
            return jsonify({"time_per_tick_minutes": 5, "error": str(e)})

    @app.route('/api/settings/time_per_tick', methods=['POST'])
    def set_time_per_tick():
        data = request.get_json()
        minutes = data.get('time_per_tick_minutes', 5)
        try:
            minutes = float(minutes)
            if minutes <= 0:
                return jsonify({"error": "Time per tick must be positive"}), 400
            app.world.time_per_tick_minutes = minutes
            logger.info(f"Time per tick set to: {minutes} minutes")
            return jsonify({"status": "success", "time_per_tick_minutes": minutes})
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid number"}), 400

    @app.route('/api/settings/clock_start', methods=['GET'])
    def get_clock_start():
        try:
            return jsonify({
                "clock_start_hour": getattr(app.world, 'clock_start_hour', 8),
                "clock_start_minute": getattr(app.world, 'clock_start_minute', 0),
            })
        except Exception as e:
            return jsonify({"clock_start_hour": 8, "clock_start_minute": 0, "error": str(e)})

    @app.route('/api/settings/clock_start', methods=['POST'])
    def set_clock_start():
        data = request.get_json()
        try:
            hour = int(data.get('clock_start_hour', 8))
            minute = int(data.get('clock_start_minute', 0))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return jsonify({"error": "Clock start must be a valid HH:MM"}), 400
            app.world.clock_start_hour = hour
            app.world.clock_start_minute = minute
            logger.info(f"Clock start set to: {hour}:{minute:02d}")
            return jsonify({
                "status": "success",
                "clock_start_hour": hour,
                "clock_start_minute": minute,
            })
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid number"}), 400

    @app.route('/api/settings/forecast', methods=['GET'])
    def get_forecast():
        """task-227: current forecast schedule + active override + moon."""
        try:
            world = app.world
            return jsonify({
                "forecast_schedule": dict(getattr(world, 'forecast_schedule', {}) or {}),
                "forecast_override": dict(getattr(world, 'forecast_override', {}) or {})
                    if getattr(world, 'forecast_override', None) else None,
                "moon_phase": world.current_moon_phase(),
                "game_day": int(world.game_day),
                "game_month": int(world.game_month),
                "game_year": int(world.game_year),
                "time": world.get_current_time(),
            })
        except Exception as e:
            logger.exception("Error in /api/settings/forecast")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/settings/forecast', methods=['POST'])
    def set_forecast():
        """task-227: replace the whole forecast schedule."""
        try:
            data = request.get_json()
            if not isinstance(data.get('schedule'), dict):
                return jsonify({"error": "Expected {'schedule': {...}}"}), 400
            schedule = data['schedule']
            # Reset the cached schedule object + transition state.
            app.world.forecast_schedule = {
                "mode": schedule.get("mode", "authored"),
                "seed": schedule.get("seed"),
                "granularity": schedule.get("granularity", "hourly"),
                "current_state": schedule.get("current_state", "clear"),
                "transition_interval": int(schedule.get("transition_interval", 1) or 1),
                "transition_table": schedule.get("transition_table") or {},
                "entries": schedule.get("entries") or [],
            }
            app.world._forecast_sched_obj = None
            app.world._forecast_last_entry_key = None
            app.world._forecast_last_minute = None
            from routes.saveload import _push_undo_snapshot
            _push_undo_snapshot(app, label="forecast schedule update")
            return jsonify({"status": "success"})
        except Exception as e:
            logger.exception("Error in POST /api/settings/forecast")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/settings/forecast-override', methods=['POST'])
    def set_forecast_override():
        """task-234: GM/trigger forecast override (weather/wind/etc + duration)."""
        try:
            data = request.get_json() or {}
            prev = dict(getattr(app.world, 'forecast_override', {}) or {})
            if data.get("clear_all"):
                app.world.forecast_override = None
            else:
                app.world.set_forecast_override(data)
            from routes.saveload import _push_undo_snapshot
            _push_undo_snapshot(app, label="forecast override")
            app.world._forecast_tick()
            return jsonify({
                "status": "success",
                "forecast_override": dict(getattr(app.world, 'forecast_override', {}) or {})
                    if getattr(app.world, 'forecast_override', None) else None,
            })
        except Exception as e:
            logger.exception("Error in POST /api/settings/forecast-override")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/settings/date', methods=['POST'])
    def set_date():
        """task-228: set game calendar date (day, month, year — each optional)."""
        try:
            data = request.get_json() or {}
            app.world.set_game_date(
                day=data.get('day'), month=data.get('month'), year=data.get('year'))
            return jsonify({
                "status": "success",
                "game_day": int(app.world.game_day),
                "game_month": int(app.world.game_month),
                "game_year": int(app.world.game_year),
            })
        except Exception as e:
            logger.exception("Error in POST /api/settings/date")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/settings/narration', methods=['GET'])
    def get_narration_mode():
        """Get the current narration mode."""
        try:
            mode = getattr(app.world, 'narration_mode', 'none')
            return jsonify({"mode": mode})
        except Exception as e:
            return jsonify({"mode": "none", "error": str(e)})

    @app.route('/api/settings/auto_generate_descriptions', methods=['GET'])
    def get_auto_generate_descriptions():
        """Get whether equipment descriptions auto-generate on equip/unequip."""
        try:
            enabled = getattr(app.world, 'auto_generate_descriptions', True)
            return jsonify({"auto_generate_descriptions": enabled})
        except Exception as e:
            return jsonify({"auto_generate_descriptions": True, "error": str(e)})

    @app.route('/api/settings/auto_generate_descriptions', methods=['POST'])
    def set_auto_generate_descriptions():
        """Toggle auto-generation of equipment descriptions on equip/unequip."""
        data = request.get_json()
        enabled = data.get('auto_generate_descriptions', True)
        if not isinstance(enabled, bool):
            return jsonify({"error": "auto_generate_descriptions must be a boolean"}), 400
        app.world.auto_generate_descriptions = enabled
        logger.info(f"Auto-generate descriptions set to: {enabled}")
        return jsonify({"status": "success", "auto_generate_descriptions": enabled})

    @app.route('/api/settings/narration', methods=['POST'])
    def set_narration_mode():
        """Set the narration mode: 'none', 'player', or 'ai'."""
        data = request.get_json()
        mode = data.get('mode', 'none')
        if mode not in ('none', 'player', 'ai'):
            return jsonify({"error": f"Invalid narration mode: {mode}. Must be 'none', 'player', or 'ai'"}), 400
        app.world.narration_mode = mode
        logger.info(f"Narration mode set to: {mode}")
        return jsonify({"status": "success", "mode": mode})

    @app.route('/api/settings/engine_config', methods=['GET'])
    def get_engine_config():
        """Return the live engine tuning values + schema metadata for the UI."""
        from engine.runtime_config import config as engine_config, SCHEMA, _SECTION_DESCRIPTIONS
        return jsonify({
            "values": engine_config.values,
            "schema": SCHEMA,
            "sections": _SECTION_DESCRIPTIONS,
        })

    @app.route('/api/settings/engine_config', methods=['POST'])
    def set_engine_config():
        """Merge posted values into engine_config.json and persist."""
        from engine.runtime_config import config as engine_config
        data = request.get_json() or {}
        values = data.get("values") or {}
        if not isinstance(values, dict):
            return jsonify({"error": "'values' must be an object"}), 400
        try:
            merged = engine_config.save(values)
            logger.info("Engine config updated: %s", list(values.keys()))
            return jsonify({"status": "success", "values": merged})
        except Exception as e:
            logger.exception("Failed to update engine config")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/settings/engine_config/reset', methods=['POST'])
    def reset_engine_config():
        """Restore all engine tunables to built-in defaults."""
        from engine.runtime_config import config as engine_config
        try:
            merged = engine_config.reset()
            return jsonify({"status": "success", "values": merged})
        except Exception as e:
            logger.exception("Failed to reset engine config")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/settings/equip_slots', methods=['GET'])
    def get_equip_slots():
        """Get equipment slot configuration (max_depth per slot)."""
        try:
            return jsonify({"equip_slots": EquipmentSystem.EQUIP_SLOTS})
        except Exception as e:
            return jsonify({"equip_slots": {}, "error": str(e)})

    @app.route('/api/embeddings', methods=['POST'])
    def api_embeddings():
        """Generate embeddings for text using local sentence-transformers model."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body"}), 400
        text = data.get("text", "")
        texts = data.get("texts", None)
        if texts is not None:
            if not isinstance(texts, list):
                return jsonify({"error": "texts must be a list"}), 400
            result = []
            for t in texts:
                try:
                    result.append(_embed_text(t))
                except Exception as e:
                    result.append(None)
            return jsonify({"embeddings": result})
        if not text:
            return jsonify({"error": "No 'text' or 'texts' field"}), 400
        try:
            emb = _embed_text(text)
            return jsonify({"embedding": emb})
        except Exception as e:
            logger.exception("Embedding failed")
            return jsonify({"error": str(e)}), 500
