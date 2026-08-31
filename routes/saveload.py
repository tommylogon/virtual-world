import os
import re
import json
import time
import logging
from flask import Flask, request, jsonify
from virtual_world_engine import VirtualWorld
from logger import setup_logger
from player import Player
from graph import Node, Edge
from .helpers import _save_game, SAVES_DIR

logger = logging.getLogger(__name__)

_MAX_UNDO_DEPTH = 10


def _snapshot(world):
    """Capture a serializable snapshot of the world for undo/redo."""
    return (world.to_dict(), getattr(world, '_scenario_source', None))


def _push_undo_snapshot(app, label="world edit"):
    """Save the current world state onto the undo stack and clear redo."""
    state, source = _snapshot(app.world)
    app._undo_stack.append((state, source, label or "world edit"))
    if len(app._undo_stack) > _MAX_UNDO_DEPTH:
        app._undo_stack.pop(0)
    app._redo_stack.clear()


def _unpack_stack_entry(entry):
    """(state, source, label) triples, backward-compatible with old pairs."""
    if len(entry) == 3:
        return entry[0], entry[1], entry[2]
    return entry[0], entry[1], "world edit"


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


def _safe_save_path(saves_dir, filename):
    """Resolve a save path inside saves_dir, rejecting traversal tricks."""
    if not filename or not isinstance(filename, str):
        return None
    base = os.path.basename(filename.replace('\\', '/'))
    if base in ('', '.', '..') or base != filename:
        return None
    if not base.endswith('.json'):
        return None
    return os.path.join(saves_dir, base)


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
            _push_undo_snapshot(app, label=f"load{' savegame' if '_save_metadata' in data else ' scenario'} <{data.get('_scenario_name') or data.get('name') or 'unnamed'}>")
            app.world.load_from_dict(data)
            # Save game loads (have _save_metadata) clear the scenario source
            if "_save_metadata" in data:
                app.world._scenario_source = None
            elif data.get('persist'):
                # GUI scenario loads opt IN with persist:true — write the source
                # file to scenarios/ so Save Scenario works. Ephemeral loads
                # (tests, MCP import, "New Scenario") never write to disk.
                scenario_name = data.get('_scenario_name') or data.get('name', 'unnamed')
                scenarios_dir = os.path.join(app.config['DATA_DIR'], 'scenarios')
                os.makedirs(scenarios_dir, exist_ok=True)
                scenario_path = os.path.join(scenarios_dir, f"{scenario_name}.json")
                # task-222: persisted worlds are graph-only — drop the redundant
                # per-room exits copies on the way to disk.
                app.world.serializer.strip_redundant_exits(data)
                with open(scenario_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                app.world._scenario_source = scenario_path
                app.world._scenario_name = scenario_name
                app.world._commit_seq = getattr(app.world, '_edit_seq', 0)
                logger.info(f"Saved loaded scenario to {scenario_path}")
            else:
                # Ephemeral load (no persist flag): the world is replaced in
                # memory but nothing is written to scenarios/. Reset falls back
                # to the boot template.
                app.world._scenario_source = None
                app.world._scenario_name = data.get('_scenario_name') or data.get('name') or ''
                app.world._commit_seq = getattr(app.world, '_edit_seq', 0)
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
            _push_undo_snapshot(app, label="reset")
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

            # Clear any game_log/time state inherited from the template so only
            # fresh init messages remain. load_from_dict writes to legacy_compat
            # (which _serialize_world reads from for the frontend), while
            # VirtualWorld.add_log_entry writes to game_logger — so set BOTH.
            new_world.legacy_compat.game_log = []
            new_world.legacy_compat.turn_events = []
            new_world.legacy_compat.log_revision = 0
            new_world.legacy_compat.time_ticks = 0
            new_world.legacy_compat.clock_start_hour = 8
            new_world.legacy_compat.clock_start_minute = 0
            new_world.legacy_compat.turn_number = 0
            # Also set on VirtualWorld attrs since get_current_time() reads them directly
            new_world.time_ticks = 0
            new_world.clock_start_hour = 8
            new_world.clock_start_minute = 0
            new_world.turn_number = 0
            # Re-add fresh init messages (also goes to game_logger for engine use)
            new_world.add_log_entry("[System] Welcome to VirtualWorld. Available Actions:")
            new_world.add_log_entry(" - Movement: go [exit] (e.g., 'go doorway', 'go grand_stairs', 'go trapdoor')")
            new_world.add_log_entry(" - Interaction: open/close [door], use [item] (on [target])")
            new_world.add_log_entry(" - Items: take [item], drop [item], examine [item], inventory")
            new_world.add_log_entry(" - Vitals: rest [minutes], eat/drink (use item), stats")
            new_world.add_log_entry(" - CRITICAL: Keep Energy above 25% to survive and enable HP regeneration! Hunger and Thirst RISE over time — eat and drink before they max out!")
            new_world.add_log_entry(" - WARNING: Environmental conditions affect your needs. Pay attention to temperature, air, noise, and smell!")
            # Mirror fresh log into legacy_compat so frontend sees it via to_dict()
            new_world.legacy_compat.game_log = list(new_world.game_logger.game_log)

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
        """Restore the world to its state before the last snapshot (e.g. reset).

        Optional ``steps`` (default 1) pops several snapshots at once so the
        history dropdown can restore to a specific labeled point.
        """
        try:
            body = request.get_json(force=True, silent=True) or {}
            steps = max(1, min(int(body.get('steps', 1) or 1), len(app._undo_stack)))
            applied = 0
            for _ in range(steps):
                if not app._undo_stack:
                    break
                entry = app._undo_stack.pop()
                state, source, label = _unpack_stack_entry(entry)
                # Push current state onto the redo stack
                app._redo_stack.append(_snapshot(app.world) + (label,))
                if len(app._redo_stack) > _MAX_UNDO_DEPTH:
                    app._redo_stack.pop(0)
                _restore_snapshot(app, state, source)
                applied += 1
            logger.info(f"Undo: restored previous world state ({applied} step(s))")
            if not applied:
                return jsonify({"error": "Nothing to undo"}), 400
            return jsonify({"status": "success", "steps": applied})
        except Exception as e:
            logger.exception("Error in /api/undo")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/undo/list', methods=['GET'])
    def undo_list():
        """Labels for every undo snapshot, newest first (index 0 = next undo)."""
        try:
            entries = []
            for entry in reversed(app._undo_stack):
                _s, _src, label = _unpack_stack_entry(entry)
                entries.append({"label": label})
            return jsonify({"entries": entries})
        except Exception as e:
            logger.exception("Error in /api/undo/list")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/redo', methods=['POST'])
    def redo_action():
        """Re-apply a state that was undone."""
        try:
            if not app._redo_stack:
                return jsonify({"error": "Nothing to redo"}), 400
            entry = app._redo_stack.pop()
            state, source, label = _unpack_stack_entry(entry)
            app._undo_stack.append(_snapshot(app.world) + (label,))
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
        saves_dir = SAVES_DIR
        try:
            if not os.path.exists(saves_dir):
                return jsonify([])
            files = []
            for fname in sorted(os.listdir(saves_dir), reverse=True):
                if fname.endswith('.json'):
                    path = os.path.join(saves_dir, fname)
                    try:
                        with open(path, 'r', encoding='utf-8-sig') as f:
                            data = json.load(f)
                        meta = data.get('_save_metadata', {})
                        files.append({
                            'filename': fname,
                            'name': meta.get('name', fname),
                            'scenario': meta.get('scenario', ''),
                            'timestamp': meta.get('timestamp', ''),
                            'tick': meta.get('tick', 0),
                            'turn': meta.get('turn', 0),
                            'player': meta.get('player', ''),
                            'version': meta.get('version', ''),
                            'autosave': bool(meta.get('autosave', False)),
                            'players': len(data.get('players', {}) or {}),
                            'areas': len(data.get('areas', {}) or {}),
                            'size': os.path.getsize(path),
                        })
                    except Exception:
                        files.append({'filename': fname, 'name': fname})
            # Newest first, then a stable pass pins the autosave slot on top.
            files.sort(key=lambda s: s.get('timestamp', ''), reverse=True)
            files.sort(key=lambda s: 0 if s.get('autosave') else 1)
            return jsonify(files)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/save-game', methods=['POST'])
    def save_game():
        data = request.get_json(force=True) or {}
        name = data.get('name')
        slot = data.get('slot')
        filename = _save_game(app.world, name, slot=slot)
        if filename:
            return jsonify({"status": "success", "filename": filename}), 201
        return jsonify({"error": "Could not save game"}), 500

    @app.route('/api/save-game/<filename>/rename', methods=['POST'])
    def rename_save_game(filename):
        """Rename a save's display name (and its file, keeping the extension)."""
        saves_dir = SAVES_DIR
        path = _safe_save_path(saves_dir, filename)
        if not path or not os.path.exists(path):
            return jsonify({"error": "Save file not found"}), 404
        body = request.get_json(force=True, silent=True) or {}
        new_name = str(body.get('name', '')).strip()
        if not new_name:
            return jsonify({"error": "Name required"}), 400
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            meta = data.get('_save_metadata', {})
            meta['name'] = new_name
            data['_save_metadata'] = meta
            safe_new = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in new_name)
            old_base = os.path.basename(path)[:-5]
            # Timestamped saves end in the convention name_YYYYMMDD_HHMMSS.
            m = re.match(r'^(.*)_(\d{8}_\d{6})$', old_base)
            if meta.get('autosave') or not m:
                # Slot saves keep their identity — only the label changes.
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                new_filename = os.path.basename(path)
            else:
                new_filename = f"{safe_new}_{m.group(2)}.json"
                new_path = os.path.join(saves_dir, new_filename)
                with open(new_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.remove(path)
            return jsonify({"status": "success", "filename": new_filename})
        except Exception as e:
            return jsonify({"error": f"Could not rename save: {e}"}), 500

    @app.route('/api/load-game/<filename>', methods=['POST'])
    def load_game(filename):
        saves_dir = SAVES_DIR
        path = _safe_save_path(saves_dir, filename)
        if not path or not os.path.exists(path):
            return jsonify({"error": "Save file not found"}), 404
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            _push_undo_snapshot(app, label=f"load savegame <{filename}>")
            app.world.load_from_dict(data)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": f"Could not load save: {e}"}), 500

    @app.route('/api/save-game/<filename>', methods=['DELETE'])
    def delete_save_game(filename):
        saves_dir = SAVES_DIR
        path = _safe_save_path(saves_dir, filename)
        if not path or not os.path.exists(path):
            return jsonify({"error": "Save file not found"}), 404
        try:
            os.remove(path)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/scenario/diff', methods=['GET'])
    def scenario_diff():
        """Structural diff between the live world and its scenario source.

        Groups: added_areas / removed_areas / changed_areas (description,
        environment, exits) / added_players / removed_players /
        added_items / removed_items / changed_items / added_ways /
        removed_ways / changed_ways. Rides on a canonical fingerprint —
        no storage format changes.
        """
        world = app.world
        source = getattr(world, '_scenario_source', None)
        if not source or not os.path.exists(source):
            return jsonify({"source": None, "groups": {}})
        try:
            with open(source, 'r', encoding='utf-8-sig') as f:
                src = json.load(f)
        except Exception:
            return jsonify({"source": source, "groups": {}, "warning": "source unreadable"})
        cur = world.to_scenario_dict()

        def fingerprint(d, name):
            a = (d.get('areas') or {}).get(name) or {}
            env = a.get('environment') or {}
            return json.dumps({
                "description": a.get("description", ""),
                "environment": {k: env.get(k) for k in ("light", "temperature", "air", "smell", "noise")},
                "exits": a.get("exits") or {},
            }, sort_keys=True, default=str)

        src_areas = set(str(k) for k in (src.get('areas') or {}))
        cur_areas = set(str(k) for k in (cur.get('areas') or {}))
        added = sorted(cur_areas - src_areas)
        removed = sorted(src_areas - cur_areas)
        common = src_areas & cur_areas
        changed = sorted(n for n in common if fingerprint(src, n) != fingerprint(cur, n))

        def player_names(d):
            if "players" in d:
                return set(str(k) for k in (d.get('players') or {}))
            names = set()
            p = d.get('player') or {}
            if p.get('name'):
                names.add(str(p['name']))
            for c in (d.get('characters') or []):
                if isinstance(c, dict) and c.get('name'):
                    names.add(str(c['name']))
            return names

        src_players = player_names(src)
        cur_players = player_names(cur)

        # Item/way drift via the graph node set (types item/way), keyed by node id
        # so renames don't show as remove+add. Fingerprint = name + state +
        # description so a pure position change (same node) stays out.
        def graph_nodes(d):
            nodes = {}
            g = d.get('graph') or {}
            for nid, nd in (g.get('nodes') or {}).items():
                if not isinstance(nd, dict) or nd.get('type') not in ('item', 'way'):
                    continue
                props = nd.get('properties')
                if not isinstance(props, dict):
                    props = {}
                nodes[nid] = (nd.get('name') or nid,
                              str(props.get('current_state', '')),
                              str(props.get('description', '')))
            return nodes

        src_nodes = graph_nodes(src)
        cur_nodes = graph_nodes(cur)
        src_item_ids = set()
        src_way_ids = set()
        cur_item_ids = set()
        cur_way_ids = set()
        for nid, nd in (src.get('graph') or {}).get('nodes', {}).items():
            if not isinstance(nd, dict):
                continue
            if nd.get('type') == 'item':
                src_item_ids.add(nid)
            elif nd.get('type') == 'way':
                src_way_ids.add(nid)
        for nid, nd in (cur.get('graph') or {}).get('nodes', {}).items():
            if not isinstance(nd, dict):
                continue
            if nd.get('type') == 'item':
                cur_item_ids.add(nid)
            elif nd.get('type') == 'way':
                cur_way_ids.add(nid)

        added_items = sorted(cur_item_ids - src_item_ids)
        added_ways = sorted(cur_way_ids - src_way_ids)
        removed_items = sorted(src_item_ids - cur_item_ids)
        removed_ways = sorted(src_way_ids - cur_way_ids)
        common_items = cur_item_ids & src_item_ids
        common_ways = cur_way_ids & src_way_ids
        changed_items = sorted(i for i in common_items
                               if src_nodes.get(i) != cur_nodes.get(i))
        changed_ways = sorted(i for i in common_ways
                              if src_nodes.get(i) != cur_nodes.get(i))

        return jsonify({
            "source": source,
            "groups": {
                "added_areas": added,
                "removed_areas": removed,
                "changed_areas": changed,
                "added_players": sorted(cur_players - src_players),
                "removed_players": sorted(src_players - cur_players),
                "added_items": added_items,
                "removed_items": removed_items,
                "changed_items": changed_items,
                "added_ways": added_ways,
                "removed_ways": removed_ways,
                "changed_ways": changed_ways,
            },
        })

    @app.route('/api/save-scenario', methods=['POST'])
    def save_scenario():
        data = request.get_json() or {}
        name = data.get('name', '').strip() or None
        scenario_data = app.world.to_scenario_dict()
        return jsonify({"status": "success", "name": name or 'unnamed', "data": scenario_data})

    # ───────────────────────── Changes panel (task-373) ─────────────────────────

    def _merge_area_into_source(src, cur, area_name):
        src_areas = src.setdefault('areas', {})
        if area_name in cur.get('areas', {}):
            src_areas[area_name] = cur['areas'][area_name]

    def _merge_node_into_source(src, cur, node_id, node_type):
        g_src = src.setdefault('graph', {})
        g_cur = cur.get('graph') or {}
        nodes_src = g_src.setdefault('nodes', {})
        nodes_cur = g_cur.get('nodes') or {}
        if node_id in nodes_cur:
            nodes_src[node_id] = nodes_cur[node_id]

    @app.route('/api/scenario/diff/apply', methods=['POST'])
    def scenario_diff_apply():
        """Per-group Commit (merge live → source) and Discard (restore).

        Body: {"commit": [group, ...], "discard": [group, ...]} where a group
        is one of: areas, items, ways, players. Commit copies the live values
        of that group's drift into the source file; Discard restores that
        group FROM the source INTO the live world (undo snapshot first).
        """
        world = app.world
        body = request.get_json(force=True, silent=True) or {}
        commit_groups = set(body.get('commit') or [])
        discard_groups = set(body.get('discard') or [])
        if not commit_groups and not discard_groups:
            return jsonify({"error": "Nothing to apply — pass commit/discard groups."}), 400

        source = getattr(world, '_scenario_source', None)
        if not source or not os.path.exists(source):
            return jsonify({"error": "No scenario source to apply against."}), 400

        # snapshot Live world first (discard mutates the world — undoable)
        if discard_groups:
            _push_undo_snapshot(app, label="scenario discard (restore from source)")

        with open(source, 'r', encoding='utf-8-sig') as f:
            src = json.load(f)

        # ── COMMIT: live → source ──
        if commit_groups:
            cur = world.to_scenario_dict()
            if 'areas' in commit_groups:
                # re-diff to know which areas drifted (commit all of them)
                for name in set((src.get('areas') or {})) | set((cur.get('areas') or {})):
                    _merge_area_into_source(src, cur, name)
            if 'items' in commit_groups or 'ways' in commit_groups:
                g_cur = cur.get('graph') or {}
                for nid, nd in (g_cur.get('nodes') or {}).items():
                    if nd.get('type') == 'item' and 'items' in commit_groups:
                        _merge_node_into_source(src, cur, nid, 'item')
                    elif nd.get('type') == 'way' and 'ways' in commit_groups:
                        _merge_node_into_source(src, cur, nid, 'way')
            if 'players' in commit_groups:
                src['players'] = cur.get('players') or {}
                src['active_player'] = cur.get('active_player')
            # also carry the graph edges when any node group is committed
            if 'items' in commit_groups or 'ways' in commit_groups:
                src.setdefault('graph', {}).setdefault('nodes', {})
                src['graph']['edges'] = (cur.get('graph') or {}).get('edges') or []

        # ── DISCARD: source → live ──
        if discard_groups:
            cur = world.to_scenario_dict()
            src_graph = src.get('graph') or {}
            src_nodes = src_graph.get('nodes') or {}
            if 'items' in discard_groups or 'ways' in discard_groups:
                # Remove live nodes of that type, then re-add from source.
                live_nodes = world.graph.nodes
                for nid, nd in list(live_nodes.items()):
                    if 'items' in discard_groups and nd.type == 'item':
                        world.graph.remove_node(nid)
                    elif 'ways' in discard_groups and nd.type == 'way':
                        world.graph.remove_node(nid)
                for nid, nd in src_nodes.items():
                    if 'items' in discard_groups and nd.get('type') == 'item':
                        world.graph.add_node(Node(id=nid, type='item', name=nd.get('name', nid),
                                                  properties=dict(nd.get('properties') or {})))
                    elif 'ways' in discard_groups and nd.get('type') == 'way':
                        world.graph.add_node(Node(id=nid, type='way', name=nd.get('name', nid),
                                                  properties=dict(nd.get('properties') or {})))
            if 'areas' in discard_groups:
                # Restore description/environment/tags from source onto the
                # LIVE area nodes (keep the nodes — no remove/add churn, so
                # placement edges and current runtime state survive).
                src_areas = src.get('areas') or {}
                for nid, node in list(world.graph.nodes.items()):
                    if node.type != 'area':
                        continue
                    name_key = node.name
                    a = src_areas.get(name_key) or next(
                        (v for k, v in src_areas.items()
                         if str(k).lower() == str(name_key).lower()), None)
                    if not a:
                        continue
                    node.properties['description'] = a.get('description', node.properties.get('description', ''))
                    node.properties['environment'] = dict(a.get('environment') or {})
                    if a.get('tags'):
                        node.properties['tags'] = list(a['tags'])
            if 'players' in discard_groups:
                # players are live state; restoring from source would delete
                # runtime memories — only re-add names that source has.
                for pname in (src.get('players') or {}):
                    if pname not in world.player_manager.players:
                        world.player_manager.add_player(Player(pname))

        # commit file write (atomic)
        tmp_path = source + '.tmp'
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(src, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, source)
        except Exception as e:
            logger.exception("Scenario diff apply failed")
            return jsonify({"error": str(e)}), 500
        world._commit_seq = getattr(world, '_edit_seq', 0)
        return jsonify({"status": "success", "committed": sorted(commit_groups),
                        "discarded": sorted(discard_groups)})

    # ───────────────────────── Scenario manager (task-374) ─────────────────────────

    def _scenarios_dir():
        return os.path.join(app.config['DATA_DIR'], 'scenarios')

    def _safe_scenario_name(name):
        """Resolve a scenario name to a path inside the scenarios dir."""
        from urllib.parse import unquote
        name = unquote(str(name or ''))
        if not name or not isinstance(name, str):
            return None
        base = name.replace('\\', '/').split('/')[-1]
        if base in ('', '.', '..'):
            return None
        safe = ''.join(c if c.isalnum() or c in ' _-.()' else '_' for c in base)
        if not safe.lower().endswith('.json'):
            safe += '.json'
        return os.path.join(_scenarios_dir(), safe)

    @app.route('/api/scenarios', methods=['GET'])
    def list_scenarios():
        """Every scenario file with lightweight stats (for the manager modal)."""
        sdir = _scenarios_dir()
        if not os.path.isdir(sdir):
            return jsonify([])
        out = []
        for fname in sorted(os.listdir(sdir), reverse=True):
            if not fname.lower().endswith('.json'):
                continue
            path = os.path.join(sdir, fname)
            entry = {"name": os.path.splitext(fname)[0], "filename": fname,
                     "size": os.path.getsize(path), "modified": os.path.getmtime(path),
                     "areas": 0, "players": 0,
                     # task-385 health: file-parseable, structural issue counts
                     "health": {"ok": False, "parse_error": None,
                                "issues": 0, "trigger_edges": 0,
                                "dangling_trigger_targets": 0,
                                "ways_missing_description": 0,
                                "areas_missing_description": 0}}
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                entry["areas"] = len(data.get('areas') or {})
                entry["players"] = len(data.get('players') or {}) or (1 if (data.get('player') or {}).get('name') else 0)
                # health scan (cheap, no world load)
                h = entry["health"]
                h["ok"] = True
                graph_edges = (data.get('graph') or {}).get('edges') or []
                graph_nodes = (data.get('graph') or {}).get('nodes') or {}
                h["trigger_edges"] = sum(1 for e in graph_edges if e.get('type') == 'triggers')
                for e in graph_edges:
                    if e.get('type') == 'triggers' and e.get('target') not in graph_nodes:
                        h["dangling_trigger_targets"] += 1
                for n in graph_nodes.values():
                    if not isinstance(n, dict):
                        continue
                    props = n.get('properties') or {}
                    if n.get('type') == 'way' and not props.get('description'):
                        h["ways_missing_description"] += 1
                    elif n.get('type') == 'area' and not props.get('description'):
                        h["areas_missing_description"] += 1
                h["issues"] = (h["dangling_trigger_targets"] + h["ways_missing_description"]
                               + h["areas_missing_description"])
            except Exception as e:
                entry["health"]["parse_error"] = str(e)
            out.append(entry)
        return jsonify(out)

    @app.route('/api/scenarios/<path:name>/duplicate', methods=['POST'])
    def duplicate_scenario(name):
        src = _safe_scenario_name(name)
        if not src or not os.path.exists(src):
            return jsonify({"error": "Scenario not found"}), 404
        base = os.path.splitext(os.path.basename(src))[0]
        import re as _re
        m = _re.match(r'^(.*) \(copy(?: \d+)?\)$', base)
        stem = m.group(1) if m else base
        candidate = f"{stem} (copy).json"
        n = 2
        while os.path.exists(os.path.join(_scenarios_dir(), candidate)):
            candidate = f"{stem} (copy {n}).json"
            n += 1
        dst = os.path.join(_scenarios_dir(), candidate)
        import shutil
        shutil.copyfile(src, dst)
        return jsonify({"status": "success", "name": os.path.splitext(candidate)[0]})

    @app.route('/api/scenarios/<path:name>/rename', methods=['POST'])
    def rename_scenario(name):
        src = _safe_scenario_name(name)
        if not src or not os.path.exists(src):
            return jsonify({"error": "Scenario not found"}), 404
        body = request.get_json(force=True, silent=True) or {}
        new_name = str(body.get('name', '')).strip()
        if not new_name:
            return jsonify({"error": "Name required"}), 400
        dst = _safe_scenario_name(new_name)
        if not dst or dst == src or os.path.exists(dst):
            return jsonify({"error": "Target name exists or invalid"}), 400
        os.rename(src, dst)
        return jsonify({"status": "success", "name": os.path.splitext(os.path.basename(dst))[0]})

    @app.route('/api/scenarios/<path:name>', methods=['GET'])
    def get_scenario(name):
        src = _safe_scenario_name(name)
        if not src or not os.path.exists(src):
            return jsonify({"error": "Scenario not found"}), 404
        try:
            with open(src, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
        except Exception as e:
            return jsonify({"error": f"Could not read scenario: {e}"}), 400
        data['_scenario_name'] = os.path.splitext(os.path.basename(src))[0]
        return jsonify(data)

    @app.route('/api/scenarios/<path:name>', methods=['DELETE'])
    def delete_scenario(name):
        src = _safe_scenario_name(name)
        if not src or not os.path.exists(src):
            return jsonify({"error": "Scenario not found"}), 404
        os.remove(src)
        return jsonify({"status": "success"})

    @app.route('/api/scenario/status', methods=['GET'])
    def scenario_status():
        """Scenario source status for the top-bar chip.

        ``dirty`` = the live world was mutated since the source was last loaded
        or committed (edit_seq vs commit_seq, bumped in the after_request
        autosave hook). Cheap and exact — no serialization on every poll.
        """
        world = app.world
        source = getattr(world, '_scenario_source', None)
        name = (getattr(world, '_scenario_name', None)
                or (os.path.splitext(os.path.basename(source))[0] if source else None)
                or 'unnamed')
        edit_seq = getattr(world, '_edit_seq', 0)
        commit_seq = getattr(world, '_commit_seq', 0)
        committed_at = None
        if source and os.path.exists(source):
            try:
                committed_at = os.path.getmtime(source)
            except Exception:
                committed_at = None
        return jsonify({
            "name": name,
            "source": source or "",
            "dirty": edit_seq != commit_seq,
            "committed_at": committed_at,
        })

    @app.route('/api/scenario/commit', methods=['POST'])
    def scenario_commit():
        """Write the live world into the scenario source (undo not needed —
        the world itself is unchanged; only the source file is refreshed)."""
        world = app.world
        body = request.get_json(force=True, silent=True) or {}
        name = str(body.get('name') or getattr(world, '_scenario_name', None) or '').strip()
        source = getattr(world, '_scenario_source', None)
        if not name:
            name = os.path.splitext(os.path.basename(source))[0] if source else 'unnamed'
        if not source or not os.path.exists(source):
            scenarios_dir = os.path.join(app.config['DATA_DIR'], 'scenarios')
            os.makedirs(scenarios_dir, exist_ok=True)
            safe = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in name) or 'unnamed'
            source = os.path.join(scenarios_dir, f"{safe}.json")
        scenario_data = world.to_scenario_dict()
        tmp_path = source + '.tmp'
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(scenario_data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, source)
        except Exception as e:
            logger.exception("Scenario commit failed")
            return jsonify({"error": str(e)}), 500
        world._scenario_source = source
        world._scenario_name = name
        world._commit_seq = getattr(world, '_edit_seq', 0)
        logger.info(f"Committed live world to scenario {source}")
        return jsonify({"status": "success", "name": name, "path": source})
