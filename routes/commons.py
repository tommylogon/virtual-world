"""HTTP endpoints for The Commons conversations.

@module commons_routes
@contributes conversation listing, membership, and authorized message endpoints
@powers The Commons communication
@relates engine/commons.py, routes/pages.py
@docs docs/virtualWorld/Gameplay/The Commons.md
"""
import os
import uuid
from flask import jsonify, request, send_file
from player import Player

from engine.commons import (
    COMMONS_THEMES,
    Commons,
    DEFAULT_COMMONS_THEME,
    ChatAuthorizationError,
    PUBLIC_CHANNEL_ID,
)


def register_commons_routes(app):
    def _theme(world):
        theme = getattr(world, "commons_theme", DEFAULT_COMMONS_THEME)
        return theme if isinstance(theme, str) and theme in COMMONS_THEMES else DEFAULT_COMMONS_THEME

    def _channel_allowed(theme, channel):
        return theme != "town_board" or channel.get("kind") != "group"

    def _unavailable_group():
        return jsonify({"error": "Group conversations are unavailable in town-board mode"}), 403

    def _is_standalone():
        return not bool(getattr(app, "_commons_use_viwo_state", True))

    def _ensure_standalone_chat(world):
        chat = getattr(app, "_commons_standalone_chat", None)
        if chat is None:
            chat = Commons()
            seed_iso = None
            if world is not None and getattr(world, "game_year", 1) > 1 and hasattr(world, "datetime_for_tick"):
                try:
                    seed_iso = world.datetime_for_tick(getattr(world, "time_ticks", 0))
                except Exception:
                    seed_iso = None
            chat.set_anchored_clock(seed_iso)
            app._commons_standalone_chat = chat
        return chat

    def _world_chat():
        world = getattr(app, "world", None)
        if _is_standalone():
            chat = _ensure_standalone_chat(world)
            for char_name in (getattr(world, "players", {}) or {}):
                chat.set_participant(char_name)
            return world, chat, None
        chat = getattr(world, "commons", None) if world else None
        if not world or chat is None:
            return None, None, (jsonify({"error": "The Commons is not initialized"}), 500)
        for char_name in (getattr(world, "players", {}) or {}):
            chat.set_participant(char_name)
        return world, chat, None

    def _known_member(world, name):
        return name == "User" or name in (getattr(world, "players", {}) or {})

    def _failure(error):
        if isinstance(error, ChatAuthorizationError):
            return jsonify({"error": str(error)}), 403
        if isinstance(error, KeyError):
            return jsonify({"error": str(error).strip("'")}), 404
        return jsonify({"error": str(error)}), 400

    @app.route('/api/commons/characters/<name>', methods=['GET'])
    def commons_character_context(name):
        world = getattr(app, 'world', None)
        player = getattr(world, 'players', {}).get(name) if world else None
        if not player:
            return jsonify({"error": "Player not found"}), 404
        # Read the existing Player identity; this is a projection, not a
        # chat-specific character/persona record.
        node_id = getattr(player, 'node_id', None) or Player.node_id_for(name)
        graph = getattr(world, 'graph', None)
        node = graph.get_node(node_id) if graph is not None and node_id else None
        properties = node.properties if node is not None else {}
        ticks = int(getattr(world, "time_ticks", 0) or 0)
        mpt = float(getattr(world, "time_per_tick_minutes", 5) or 5)
        start_h = int(getattr(world, "clock_start_hour", 8) or 8)
        start_m = int(getattr(world, "clock_start_minute", 0) or 0)
        standalone = _is_standalone()
        if standalone:
            chat = _ensure_standalone_chat(world)
            world_datetime = chat.current_anchored_iso()
            world_time = chat.format_iso_label(world_datetime)
            clock_mode = "standalone"
        else:
            clock_mode = "scenario"
            world_datetime = world.datetime_for_tick(ticks) if hasattr(world, "datetime_for_tick") else None
            if hasattr(world, "calendar_label_for_tick"):
                world_time = world.calendar_label_for_tick(ticks)
            else:
                start_min = start_h * 60 + start_m
                total_min = int(round(start_min + ticks * mpt))
                hh = (total_min % 1440) // 60
                mm = total_min % 60
                world_time = f"{hh:02d}:{mm:02d}"
        curr_area = getattr(player, "current_area", "") or ""
        people_here = [
            pname for pname, pother in (getattr(world, "players", {}) or {}).items()
            if pname != name and getattr(pother, "current_area", "") == curr_area and curr_area
        ]
        return jsonify({
            "name": name,
            "traits": getattr(player, "traits", {}) or {},
            "personality": properties.get("personality") or getattr(player, "personality", "") or "",
            "personality_dials": getattr(player, "personality_dials", {}) or {},
            "description": getattr(player, "description", "") or properties.get("description", "") or properties.get("base_description", "") or "",
            "tags": getattr(player, "tags", []) or [],
            "state": getattr(player, "state", "awake"),
            "emotion": getattr(player, "emotion", "neutral") or "neutral",
            "emotion_intensity": getattr(player, "emotion_intensity", 0) or 0,
            "conditions": getattr(player, "conditions", {}) or {},
            "relationships": getattr(player, "relationships", {}) or {},
            "current_area": curr_area,
            "people_here": people_here,
            "time_ticks": ticks,
            "time_per_tick_minutes": mpt,
            "clock_start_hour": start_h,
            "clock_start_minute": start_m,
            "game_day": int(getattr(world, "game_day", 1) or 1),
            "game_month": int(getattr(world, "game_month", 1) or 1),
            "game_year": int(getattr(world, "game_year", 1) or 1),
            "calendar_config": dict(getattr(world, "calendar_config", {}) or {}),
            "clock_mode": clock_mode,
            "world_datetime": world_datetime,
            "world_time": world_time,
        })

    @app.route('/api/commons/state', methods=['GET'])
    def commons_state():
        world, chat, error = _world_chat()
        if error:
            return error
        perspective = request.args.get("as", "User")
        if not _known_member(world, perspective):
            return jsonify({"error": "Character not found"}), 404
        player = (getattr(world, "players", {}) or {}).get(perspective)
        known_characters = [
            name for name, other in (getattr(world, "players", {}) or {}).items()
            if name != perspective and name != "User"
            and player is not None and hasattr(player, "knows_name")
            and player.knows_name(name)
        ]
        participant_data = {}
        for name, row in chat.participants.items():
            character = (getattr(world, "players", {}) or {}).get(name)
            if character is None:
                control_mode = "unavailable"
            elif getattr(character, "simple_npc", False):
                control_mode = "npc"
            elif not bool(getattr(character, "autonomy", True)):
                control_mode = "human"
            else:
                control_mode = "llm"
            participant_data[name] = {
                "active": bool(row.get("active", True)),
                "blocked": bool(row.get("blocked", False)),
                "control_mode": control_mode,
                "state": getattr(character, "state", "awake") if character is not None else "unavailable",
                "muted_channels": list(row.get("muted_channels") or []),
            }
        standalone = _is_standalone()
        cur_dt = (
            chat.current_anchored_iso()
            if standalone
            else (world.datetime_for_tick(getattr(world, "time_ticks", 0)) if world and hasattr(world, "datetime_for_tick") else None)
        )
        cur_label = (
            chat.format_iso_label(cur_dt)
            if cur_dt and hasattr(chat, "format_iso_label")
            else (world.calendar_label_for_tick() if world and hasattr(world, "calendar_label_for_tick") else None)
        )
        return jsonify({
            "perspective": perspective,
            "use_viwo_state": not standalone,
            "clock_mode": "standalone" if standalone else "scenario",
            "active_branch_id": getattr(chat, "active_branch_id", "main"),
            "branches": chat.list_branches() if hasattr(chat, "list_branches") else [],
            "anchored_clock": getattr(chat, "anchored_clock", None),
            "current_datetime": cur_dt,
            "current_time_label": cur_label,
            "channels": [
                channel for channel in chat.list_channels(perspective)
                if _channel_allowed(_theme(world), channel)
            ],
            "participants": participant_data,
            "known_characters": known_characters,
            "world_clock": {
                "time_ticks": int(getattr(world, "time_ticks", 0) or 0),
                "time_per_tick_minutes": float(getattr(world, "time_per_tick_minutes", 5) or 5),
                "clock_start_hour": int(getattr(world, "clock_start_hour", 8) or 8),
                "clock_start_minute": int(getattr(world, "clock_start_minute", 0) or 0),
                "game_day": int(getattr(world, "game_day", 1) or 1),
                "game_month": int(getattr(world, "game_month", 1) or 1),
                "game_year": int(getattr(world, "game_year", 1) or 1),
                "calendar_config": dict(getattr(world, "calendar_config", {}) or {}),
            },
            "theme": _theme(world),
        })

    @app.route('/api/commons/theme', methods=['POST'])
    def commons_set_theme():
        world = getattr(app, "world", None)
        if world is None:
            return jsonify({"error": "The Commons is not initialized"}), 500
        data = request.get_json() or {}
        theme = data.get("theme")
        if not isinstance(theme, str) or theme not in COMMONS_THEMES:
            return jsonify({
                "error": f"Invalid Commons theme: {theme}. Must be one of {sorted(COMMONS_THEMES)}"
            }), 400
        world.commons_theme = theme
        return jsonify({"theme": theme})

    @app.route('/api/commons/channels', methods=['POST'])
    def commons_create_channel():
        world, chat, error = _world_chat()
        if error:
            return error
        data = request.get_json() or {}
        creator = str(data.get("creator") or "").strip()
        if not _known_member(world, creator):
            return jsonify({"error": "Creator not found"}), 404
        kind = str(data.get("kind") or "").strip().lower()
        if kind == "group" and _theme(world) == "town_board":
            return _unavailable_group()
        try:
            if kind == "group":
                members = data.get("members") or []
                if not isinstance(members, list) or any(not _known_member(world, str(member)) for member in members):
                    return jsonify({"error": "Every group member must be User or an existing character"}), 400
                channel = chat.create_group(creator, data.get("name", ""), members)
            elif kind == "dm":
                other = str(data.get("other") or "").strip()
                if not _known_member(world, other):
                    return jsonify({"error": "Recipient not found"}), 404
                channel = chat.create_dm(creator, other)
            else:
                return jsonify({"error": "Channel kind must be group or dm"}), 400
        except (ValueError, KeyError, ChatAuthorizationError) as exc:
            return _failure(exc)
        return jsonify({"channel": channel}), 201

    @app.route('/api/commons/channels/<channel_id>/members', methods=['PATCH'])
    def commons_update_members(channel_id):
        world, chat, error = _world_chat()
        if error:
            return error
        data = request.get_json() or {}
        actor = str(data.get("actor") or "").strip()
        if not _known_member(world, actor):
            return jsonify({"error": "Actor not found"}), 404
        if _theme(world) == "town_board":
            channel = chat.channels.get(channel_id)
            if channel and not _channel_allowed(_theme(world), channel):
                return _unavailable_group()
        add, remove = data.get("add") or [], data.get("remove") or []
        if (not isinstance(add, list) or not isinstance(remove, list)
                or any(not _known_member(world, str(name)) for name in add + remove)):
            return jsonify({"error": "Every member must be User or an existing character"}), 400
        try:
            channel = chat.update_group_members(channel_id, actor, add, remove)
        except (ValueError, KeyError, ChatAuthorizationError) as exc:
            return _failure(exc)
        return jsonify({"channel": channel})

    @app.route('/api/commons/channels/<channel_id>/mute', methods=['POST'])
    def commons_mute_channel(channel_id):
        world, chat, error = _world_chat()
        if error:
            return error
        data = request.get_json() or {}
        actor = str(data.get("actor") or "").strip()
        if not _known_member(world, actor):
            return jsonify({"error": "Actor not found"}), 404
        if _theme(world) == "town_board":
            channel = chat.channels.get(channel_id)
            if channel and not _channel_allowed(_theme(world), channel):
                return _unavailable_group()
        muted = bool(data.get("muted", True))
        try:
            muted_state = chat.set_muted(actor, channel_id, muted)
        except (ValueError, KeyError, ChatAuthorizationError) as exc:
            return _failure(exc)
        return jsonify({"channel_id": channel_id, "muted": muted_state})

    @app.route('/api/commons/messages', methods=['GET', 'POST'])
    def commons_messages():
        world, chat, error = _world_chat()
        if error:
            return error
        if request.method == 'GET':
            channel_id = request.args.get("channel_id", PUBLIC_CHANNEL_ID)
            perspective = request.args.get("as", "User")
            if not _known_member(world, perspective):
                return jsonify({"error": "Character not found"}), 404
            try:
                channel = chat.channels.get(channel_id)
                if channel and not _channel_allowed(_theme(world), channel):
                    return _unavailable_group()
                chat.require_access(perspective, channel_id)
            except (KeyError, ChatAuthorizationError) as exc:
                return _failure(exc)
            since_id = request.args.get('since_id', type=int)
            msgs = [
                dict(message) for message in chat.messages
                if message.get("channel_id", PUBLIC_CHANNEL_ID) == channel_id
                and (since_id is None or message["id"] > since_id)
                and not message.get("deleted")
            ]
            return jsonify({"messages": msgs})

        data = request.get_json() or {}
        author = str(data.get("author", "User") or "User").strip()
        channel_id = str(data.get("channel_id") or PUBLIC_CHANNEL_ID)
        text = str(data.get("text") or "").strip()
        attachments = data.get("attachments") or []
        if not _known_member(world, author):
            return jsonify({"error": "Author not found"}), 404
        if not text and not attachments:
            return jsonify({"error": "Empty message text and no attachments"}), 400
        channel = chat.channels.get(channel_id)
        if channel and not _channel_allowed(_theme(world), channel):
            return _unavailable_group()
        clean_attachments = []
        for att in attachments:
            if isinstance(att, dict):
                clean_attachments.append({
                    "id": str(att.get("id") or uuid.uuid4().hex[:8]),
                    "url": str(att.get("url") or "").strip(),
                    "mime_type": str(att.get("mime_type") or "image/png").strip(),
                    "size": int(att.get("size") or 0),
                    "caption": str(att.get("caption") or "").strip(),
                })
        try:
            standalone = _is_standalone()
            if not standalone and bool(data.get("advance_tick")):
                world.time_ticks = int(getattr(world, "time_ticks", 0) or 0) + 1
            msg_dt = (
                chat.current_anchored_iso()
                if standalone
                else (world.datetime_for_tick(getattr(world, "time_ticks", 0)) if world and hasattr(world, "datetime_for_tick") else None)
            )
            message = chat.post_message(
                author=author,
                text=text,
                tick=getattr(world, 'time_ticks', 0),
                channel_id=channel_id,
                attachments=clean_attachments if clean_attachments else None,
                world_datetime=msg_dt,
            )
        except (KeyError, ChatAuthorizationError) as exc:
            return _failure(exc)
        return jsonify({"message": message})

    @app.route('/api/commons/mode', methods=['POST'])
    def commons_set_mode():
        world = getattr(app, "world", None)
        data = request.get_json(silent=True) or {}
        use_viwo = bool(data.get("use_viwo_state", True))
        app._commons_use_viwo_state = use_viwo
        if not use_viwo:
            _ensure_standalone_chat(world)
        return jsonify({"use_viwo_state": use_viwo, "clock_mode": "scenario" if use_viwo else "standalone"})

    @app.route('/api/commons/clock', methods=['POST'])
    def commons_set_clock():
        world, chat, error = _world_chat()
        if error:
            return error
        data = request.get_json(silent=True) or {}
        anchor = data.get("anchor_datetime")
        if not anchor and (data.get("date") or data.get("time")):
            cur = chat.current_anchored_iso()
            d_part = str(data.get("date") or cur[:10]).strip()
            t_part = str(data.get("time") or cur[11:16]).strip()
            anchor = f"{d_part}T{t_part}:00" if len(t_part) == 5 else f"{d_part}T{t_part}"
        try:
            clk = chat.set_anchored_clock(anchor)
        except ValueError as exc:
            return jsonify({"error": f"Invalid datetime: {exc}"}), 400
        cur_iso = chat.current_anchored_iso()
        return jsonify({
            "anchored_clock": clk,
            "current_datetime": cur_iso,
            "current_time_label": chat.format_iso_label(cur_iso),
        })

    @app.route('/api/commons/branches', methods=['POST'])
    def commons_fork_branch():
        world, chat, error = _world_chat()
        if error:
            return error
        data = request.get_json(silent=True) or {}
        name = str(data.get("name") or "").strip()
        from_msg_id = data.get("from_message_id")
        branch = chat.fork_branch(name=name, from_message_id=int(from_msg_id) if from_msg_id is not None else None)
        return jsonify({"branch": branch, "branches": chat.list_branches(), "active_branch_id": chat.active_branch_id}), 201

    @app.route('/api/commons/branches/switch', methods=['POST'])
    def commons_switch_branch():
        world, chat, error = _world_chat()
        if error:
            return error
        data = request.get_json(silent=True) or {}
        branch_id = str(data.get("branch_id") or "").strip()
        try:
            branch = chat.switch_branch(branch_id)
        except KeyError as exc:
            return _failure(exc)
        return jsonify({"branch": branch, "branches": chat.list_branches(), "active_branch_id": chat.active_branch_id})

    @app.route('/api/commons/reset', methods=['POST'])
    def commons_reset():
        world, chat, error = _world_chat()
        if error:
            return error
        data = request.get_json(silent=True) or {}
        if not _is_standalone() and not bool(data.get("force")):
            return jsonify({"error": "Refusing to reset live Viwo Commons without force=true; switch to Standalone mode first"}), 400
        chat.reset_session(preserve_participants=True)
        return jsonify({"reset": True, "active_branch_id": chat.active_branch_id})

    @app.route('/api/commons/memories/<name>', methods=['GET', 'POST'])
    def commons_standalone_memories(name):
        world, chat, error = _world_chat()
        if error:
            return error
        if not _known_member(world, name):
            return jsonify({"error": "Character not found"}), 404
        if request.method == 'GET':
            mems = list(chat.standalone_memories.get(name, []))
            return jsonify({"memories": mems})
        data = request.get_json(silent=True) or {}
        mem = chat.add_standalone_memory(name, {
            "text": str(data.get("text") or "").strip(),
            "importance": int(data.get("importance", 5) or 5),
            "type": str(data.get("type") or "reflection"),
            "tags": list(data.get("tags") or []),
            "memory_emotions": data.get("memory_emotions"),
        })
        return jsonify({"memory": mem}), 201

    @app.route('/api/commons/messages/<int:message_id>', methods=['PATCH', 'DELETE'])
    def commons_message_detail(message_id):
        world, chat, error = _world_chat()
        if error:
            return error
        data = request.get_json(silent=True) or {}
        actor = str(data.get("author") or request.args.get("author") or "User").strip()
        if not _known_member(world, actor):
            return jsonify({"error": "Actor not found"}), 404
        if request.method == 'PATCH':
            text = str(data.get("text") or "").strip()
            if not text:
                return jsonify({"error": "Empty message text"}), 400
            try:
                msg = chat.edit_message(
                    message_id=message_id,
                    author=actor,
                    text=text,
                    players=getattr(world, "players", None),
                )
            except (KeyError, ChatAuthorizationError, ValueError) as exc:
                return _failure(exc)
            return jsonify({"message": msg})

        # DELETE
        try:
            msg = chat.delete_message(
                message_id=message_id,
                author=actor,
                players=getattr(world, "players", None),
            )
        except (KeyError, ChatAuthorizationError, ValueError) as exc:
            return _failure(exc)
        return jsonify({"message": msg, "deleted": True})

    @app.route('/api/commons/read', methods=['POST'])
    def commons_read():
        world, chat, error = _world_chat()
        if error:
            return error
        data = request.get_json() or {}
        character = str(data.get("character") or "").strip()
        if not _known_member(world, character):
            return jsonify({"error": "Character not found"}), 404
        channel_id = str(data.get("channel_id") or PUBLIC_CHANNEL_ID)
        channel = chat.channels.get(channel_id)
        if channel and not _channel_allowed(_theme(world), channel):
            return _unavailable_group()
        try:
            messages = chat.read_messages(
                character=character,
                channel_id=channel_id,
                mode=data.get("mode", "latest"),
                n=data.get("n", 3),
                from_id=data.get("from_id"),
                to_id=data.get("to_id"),
            )
        except (KeyError, ChatAuthorizationError) as exc:
            return _failure(exc)
        cursor = (chat.participants.get(character, {}).get("last_read_message_ids", {})
                  .get(channel_id))
        return jsonify({"messages": messages, "last_read_message_id": cursor})

    @app.route('/api/commons/participants/<name>', methods=['PATCH'])
    def commons_update_participant(name):
        world, chat, error = _world_chat()
        if error:
            return error
        if not _known_member(world, name):
            return jsonify({"error": "Character not found"}), 404
        data = request.get_json() or {}
        participant = chat.set_participant(
            name,
            active=data.get("active"),
            blocked=data.get("blocked"),
        )
        return jsonify({"participant": participant})

    UPLOAD_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    UPLOAD_MIMES = {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
    MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5 MB

    @app.route('/api/commons/attachments/upload', methods=['POST'])
    def commons_upload_attachment():
        world, chat, error = _world_chat()
        if error:
            return error
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({"error": "No file selected"}), 400
        caption = request.form.get('caption', '').strip()

        _, ext = os.path.splitext(file.filename.lower())
        if ext not in UPLOAD_EXTENSIONS:
            return jsonify({"error": f"Unsupported file extension: {ext}"}), 400

        data = file.read(MAX_ATTACHMENT_SIZE + 1)
        if len(data) > MAX_ATTACHMENT_SIZE:
            return jsonify({"error": "File exceeds 5MB size limit"}), 400

        mime = file.mimetype or 'image/png'
        if mime not in UPLOAD_MIMES:
            mime = 'image/png' if ext == '.png' else 'image/jpeg' if ext in ('.jpg', '.jpeg') else 'image/webp' if ext == '.webp' else 'image/gif'

        att_id = uuid.uuid4().hex[:12]
        upload_dir = os.path.join(app.config.get('DATA_DIR', 'data'), 'uploads', 'commons')
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"{att_id}{ext}"
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, 'wb') as out_f:
            out_f.write(data)

        url = f"/api/commons/attachments/{filename}"
        return jsonify({
            "id": att_id,
            "url": url,
            "filename": file.filename,
            "mime_type": mime,
            "size": len(data),
            "caption": caption,
        })

    @app.route('/api/commons/attachments/<filename>', methods=['GET'])
    def commons_get_attachment(filename):
        upload_dir = os.path.join(app.config.get('DATA_DIR', 'data'), 'uploads', 'commons')
        filepath = os.path.join(upload_dir, filename)
        if not os.path.exists(filepath):
            return jsonify({"error": "Attachment not found"}), 404
        return send_file(filepath)
