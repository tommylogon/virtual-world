"""HTTP endpoints for the Stage Chat page.

@module stage_chat_routes
@contributes state, participant, and message endpoints for Stage Chat
@powers Stage Chat
@relates engine/stage_chat.py, routes/pages.py
@docs none
"""
from flask import request, jsonify, current_app


def register_stage_chat_routes(app):
    @app.route('/api/stage-chat/state', methods=['GET'])
    def stage_chat_state():
        world = getattr(app, 'world', None)
        if not world or not hasattr(world, 'stage_chat'):
            return jsonify({"error": "Stage chat not initialized"}), 500
        chat = world.stage_chat

        # Sync scenario characters into participants if not present
        if hasattr(world, 'players') and world.players:
            for char_name in world.players.keys():
                chat.set_participant(char_name)

        participants_data = {}
        for name, pstate in chat.participants.items():
            participants_data[name] = {
                **pstate,
                "unread_count": chat.get_unread_count(name)
            }

        return jsonify({
            "messages": chat.messages,
            "participants": participants_data,
            "next_message_id": chat.next_message_id
        })

    @app.route('/api/stage-chat/messages', methods=['GET', 'POST'])
    def stage_chat_messages():
        world = getattr(app, 'world', None)
        if not world or not hasattr(world, 'stage_chat'):
            return jsonify({"error": "Stage chat not initialized"}), 500
        chat = world.stage_chat

        if request.method == 'GET':
            since_id = request.args.get('since_id', type=int)
            if since_id is not None:
                msgs = [m for m in chat.messages if m["id"] > since_id]
            else:
                msgs = chat.messages
            return jsonify({"messages": msgs})

        data = request.get_json() or {}
        author = data.get("author", "User")
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "Empty message text"}), 400

        tick = getattr(world, 'time_ticks', 0)
        msg = chat.post_message(author=author, text=text, tick=tick)
        return jsonify({"message": msg})

    @app.route('/api/stage-chat/read', methods=['POST'])
    def stage_chat_read():
        world = getattr(app, 'world', None)
        if not world or not hasattr(world, 'stage_chat'):
            return jsonify({"error": "Stage chat not initialized"}), 500
        chat = world.stage_chat

        data = request.get_json() or {}
        character = data.get("character")
        if not character:
            return jsonify({"error": "character required"}), 400

        mode = data.get("mode", "latest")
        n = data.get("n", 3)
        from_id = data.get("from_id")
        to_id = data.get("to_id")

        read_msgs = chat.read_messages(character=character, mode=mode, n=n, from_id=from_id, to_id=to_id)
        return jsonify({
            "messages": read_msgs,
            "last_read_message_id": chat.participants.get(character, {}).get("last_read_message_id")
        })

    @app.route('/api/stage-chat/participants/<name>', methods=['PATCH'])
    def stage_chat_update_participant(name):
        world = getattr(app, 'world', None)
        if not world or not hasattr(world, 'stage_chat'):
            return jsonify({"error": "Stage chat not initialized"}), 500
        chat = world.stage_chat

        data = request.get_json() or {}
        active = data.get("active")
        blocked = data.get("blocked")
        chat.set_participant(name, active=active, blocked=blocked)
        return jsonify({"participant": chat.participants.get(name)})
