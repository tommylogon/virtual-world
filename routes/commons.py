"""HTTP endpoints for The Commons conversations.

@module commons_routes
@contributes conversation listing, membership, and authorized message endpoints
@powers The Commons communication
@relates engine/commons.py, routes/pages.py
@docs docs/virtualWorld/Gameplay/The Commons.md
"""
from flask import jsonify, request

from engine.commons import ChatAuthorizationError, PUBLIC_CHANNEL_ID


def register_commons_routes(app):
    def _world_chat():
        world = getattr(app, "world", None)
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
        manager = getattr(world, "player_manager", None)
        graph = getattr(world, "graph", None)
        node_id = manager.player_node_id(name) if manager else None
        node = graph.get_node(node_id) if graph is not None and node_id else None
        properties = node.properties if node is not None else {}
        return jsonify({
            "name": name,
            "traits": getattr(player, "traits", {}) or {},
            "personality": properties.get("personality") or getattr(player, "personality", "") or "",
            "personality_dials": getattr(player, "personality_dials", {}) or {},
            "description": getattr(player, "description", "") or properties.get("description", "") or properties.get("base_description", "") or "",
            "tags": getattr(player, "tags", []) or [],
            "state": getattr(player, "state", "awake"),
        })

    @app.route('/api/commons/state', methods=['GET'])
    def commons_state():
        world, chat, error = _world_chat()
        if error:
            return error
        perspective = request.args.get("as", "User")
        if not _known_member(world, perspective):
            return jsonify({"error": "Character not found"}), 404
        participant_data = {
            name: {"active": bool(row.get("active", True)), "blocked": bool(row.get("blocked", False))}
            for name, row in chat.participants.items()
        }
        return jsonify({
            "perspective": perspective,
            "channels": chat.list_channels(perspective),
            "participants": participant_data,
        })

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
        add, remove = data.get("add") or [], data.get("remove") or []
        if (not isinstance(add, list) or not isinstance(remove, list)
                or any(not _known_member(world, str(name)) for name in add + remove)):
            return jsonify({"error": "Every member must be User or an existing character"}), 400
        try:
            channel = chat.update_group_members(channel_id, actor, add, remove)
        except (ValueError, KeyError, ChatAuthorizationError) as exc:
            return _failure(exc)
        return jsonify({"channel": channel})

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
                chat.require_access(perspective, channel_id)
            except (KeyError, ChatAuthorizationError) as exc:
                return _failure(exc)
            since_id = request.args.get('since_id', type=int)
            msgs = [
                dict(message) for message in chat.messages
                if message.get("channel_id", PUBLIC_CHANNEL_ID) == channel_id
                and (since_id is None or message["id"] > since_id)
            ]
            return jsonify({"messages": msgs})

        data = request.get_json() or {}
        author = str(data.get("author", "User") or "User").strip()
        channel_id = str(data.get("channel_id") or PUBLIC_CHANNEL_ID)
        text = str(data.get("text") or "").strip()
        if not _known_member(world, author):
            return jsonify({"error": "Author not found"}), 404
        if not text:
            return jsonify({"error": "Empty message text"}), 400
        try:
            message = chat.post_message(
                author=author,
                text=text,
                tick=getattr(world, 'time_ticks', 0),
                channel_id=channel_id,
            )
        except (KeyError, ChatAuthorizationError) as exc:
            return _failure(exc)
        return jsonify({"message": message})

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
