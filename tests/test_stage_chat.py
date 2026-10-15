import json
from types import SimpleNamespace
from pathlib import Path

from flask import Flask

from engine.stage_chat import ChatAuthorizationError, StageChat
from routes.action_handlers import handle_get_state
from routes.memories import register_memories_routes
from routes.stage_chat import register_stage_chat_routes
from virtual_world_engine import VirtualWorld


def _stage_chat_app():
    character = SimpleNamespace(
        name="Mira",
        traits={"patient": True},
        personality="Careful and dry-witted.",
        description="A quiet traveler.",
        base_description="",
        current_area="Kitchen",
        inventory=["not part of stage chat"],
    )
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.world = SimpleNamespace(
        players={"Mira": character, "Lysa": SimpleNamespace(name="Lysa")},
        stage_chat=StageChat(),
        time_ticks=0,
    )
    register_stage_chat_routes(app)
    return app


def test_public_chat_read_cursor_advances_only_on_explicit_read():
    chat = StageChat()
    chat.set_participant("Mira")
    first = chat.post_message("Lysa", "The door is open.")
    second = chat.post_message("User", "Come by when ready.")

    assert first["channel_id"] == "public"
    assert second["channel_id"] == "public"
    assert chat.get_unread_count("Mira", "public") == 2
    assert chat.participants["Mira"]["last_read_message_ids"] == {}

    messages = chat.read_messages("Mira", mode="range", from_id=2, to_id=2)
    assert [message["id"] for message in messages] == [2]
    assert chat.participants["Mira"]["last_read_message_ids"]["public"] == 2

    chat.post_message("Lysa", "I will wait.")
    unread = chat.read_messages("Mira", mode="all")
    assert [message["id"] for message in unread] == [3]
    assert chat.participants["Mira"]["last_read_message_ids"]["public"] == 3


def test_private_group_authorizes_members_for_reads_and_sends_only():
    chat = StageChat()
    group = chat.create_group("Mira", "The night watch", ["Mira", "Lysa"])
    message = chat.post_message("Mira", "Meet by the north gate.", channel_id=group["id"])

    assert message["channel_id"] == group["id"]
    assert [channel["id"] for channel in chat.list_channels("Lysa")] == ["public", group["id"]]
    assert [channel["id"] for channel in chat.list_channels("User")] == ["public"]
    assert chat.read_messages("Lysa", mode="all", channel_id=group["id"]) == [message]
    try:
        chat.read_messages("User", mode="all", channel_id=group["id"])
    except ChatAuthorizationError as exc:
        assert str(exc) == "Not a member of this conversation"
    else:
        raise AssertionError("non-member read was not rejected")
    try:
        chat.post_message("User", "I should not see this.", channel_id=group["id"])
    except ChatAuthorizationError:
        pass
    else:
        raise AssertionError("non-member send was not rejected")


def test_dm_has_exactly_two_members_and_cursors_are_per_conversation():
    chat = StageChat()
    dm = chat.create_dm("Mira", "Lysa")
    assert set(dm["members"]) == {"Mira", "Lysa"}
    chat.post_message("Lysa", "Can we speak privately?", channel_id=dm["id"])
    chat.post_message("Lysa", "Everyone can see this.", channel_id="public")

    chat.read_messages("Mira", mode="all", channel_id=dm["id"])
    cursors = chat.participants["Mira"]["last_read_message_ids"]
    assert cursors == {dm["id"]: 1}
    assert chat.get_unread_count("Mira", "public") == 1
    assert chat.list_channels("User")[0]["id"] == "public"


def test_group_membership_changes_are_creator_only_and_persist_with_messages():
    chat = StageChat()
    group = chat.create_group("Mira", "Camp plans", ["Mira", "Lysa"])
    chat.update_group_members(group["id"], "Mira", add=["User"])
    chat.post_message("User", "I will bring the map.", channel_id=group["id"])

    restored = StageChat()
    restored.from_dict(chat.to_dict())
    assert restored.list_channels("User")[1]["members"] == ["Mira", "Lysa", "User"]
    assert restored.read_messages("User", mode="all", channel_id=group["id"])[0]["text"] == "I will bring the map."
    try:
        restored.update_group_members(group["id"], "Lysa", remove=["User"])
    except ChatAuthorizationError:
        pass
    else:
        raise AssertionError("non-creator membership edit was not rejected")


def test_routes_filter_channels_by_perspective_and_reject_private_reads_and_sends():
    app = _stage_chat_app()
    client = app.test_client()
    chat = app.world.stage_chat
    group = chat.create_group("Mira", "The night watch", ["Mira", "Lysa"])
    chat.post_message("Mira", "Private detail.", channel_id=group["id"])

    user_state = client.get("/api/stage-chat/state?as=User").get_json()
    mira_state = client.get("/api/stage-chat/state?as=Mira").get_json()
    assert [channel["id"] for channel in user_state["channels"]] == ["public"]
    assert [channel["id"] for channel in mira_state["channels"]] == ["public", group["id"]]

    denied_read = client.post("/api/stage-chat/read", json={
        "character": "User", "channel_id": group["id"], "mode": "all",
    })
    denied_send = client.post("/api/stage-chat/messages", json={
        "author": "User", "channel_id": group["id"], "text": "Not allowed.",
    })
    allowed_read = client.post("/api/stage-chat/read", json={
        "character": "Mira", "channel_id": group["id"], "mode": "all",
    })
    assert denied_read.status_code == 403
    assert denied_send.status_code == 403
    assert "Private detail." not in denied_read.get_data(as_text=True)
    assert [message["text"] for message in allowed_read.get_json()["messages"]] == ["Private detail."]


def test_stage_chat_context_projects_existing_player_identity_without_world_state():
    app = _stage_chat_app()
    client = app.test_client()
    response = client.get("/api/stage-chat/characters/Mira")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["name"] == "Mira"
    assert payload["traits"] == {"patient": True}
    assert payload["personality"] == "Careful and dry-witted."
    assert payload["description"] == "A quiet traveler."
    assert "current_area" not in payload
    assert "inventory" not in payload
    assert client.get("/api/stage-chat/characters/Unknown").status_code == 404


def test_stage_chat_memory_uses_existing_player_memories_collection():
    app = _stage_chat_app()
    player = app.world.players["Mira"]
    player.memories = []
    register_memories_routes(app)
    client = app.test_client()

    response = client.post("/api/players/Mira/memories/entry", json={
        "text": "I read Lysa's message and decided to warn her.",
        "type": "conversation",
        "category": "social",
        "tags": ["conversation", "chat"],
    })
    assert response.status_code == 201
    memory = response.get_json()["entry"]
    saved = client.get("/api/players/Mira/memories").get_json()["memories"]

    assert saved == [memory]
    assert memory["text"] == "I read Lysa's message and decided to warn her."
    assert memory["category"] == "social"
    assert not hasattr(player, "stage_chat_memories")


def test_world_state_payload_does_not_publish_private_stage_chat_channels():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.world = SimpleNamespace(
        to_dict=lambda lite=False: {"players": {}, "stage_chat": {"secret": "private text"}},
        scenario_ended=False,
        _restart_requested=False,
    )
    with app.test_request_context("/api/state"):
        response = handle_get_state(app)
    assert response.get_json().get("stage_chat") is None


def test_saved_world_round_trips_chat_communication_but_scenario_export_drops_runtime_chat():
    world = VirtualWorld()
    group = world.stage_chat.create_group("Mira", "Night watch", ["Mira", "Lysa"])
    world.stage_chat.post_message("Mira", "I will take first watch.", channel_id=group["id"])
    world.stage_chat.read_messages("Lysa", mode="all", channel_id=group["id"])

    saved = world.to_dict()
    restored = VirtualWorld()
    restored.load_from_dict(saved)
    assert restored.stage_chat.channels[group["id"]]["members"] == ["Mira", "Lysa"]
    assert restored.stage_chat.read_messages("Mira", mode="all", channel_id=group["id"])[0]["text"] == "I will take first watch."
    assert restored.stage_chat.participants["Lysa"]["last_read_message_ids"][group["id"]] == 1
    assert "stage_chat" not in world.to_scenario_dict()


def test_kraktooth_scenario_authors_public_group_and_dm_conversations():
    scenario_path = Path(__file__).resolve().parents[1] / "data" / "scenarios" / "kraktooth_goblin_camp.json"
    with scenario_path.open(encoding="utf-8") as source:
        scenario = json.load(source)

    world = VirtualWorld()
    world.load_from_dict(scenario)
    channels = world.stage_chat.list_channels("Vekka")
    channel_kinds = {channel["kind"] for channel in channels}
    scenario_players = set(world.players)

    assert channel_kinds == {"public", "group", "dm"}
    assert {"Vekka", "Zikka", "Gribba"} <= scenario_players
    assert all(set(channel["members"]) <= scenario_players
               for channel in channels if channel["kind"] != "public")
    assert world.stage_chat.list_channels("Rag-Tail") == [
        channel for channel in world.stage_chat.list_channels("Rag-Tail")
        if channel["kind"] == "public"
    ]
    assert [message["text"] for message in world.stage_chat.messages] == [
        "Human tracks cross the north trail and turn toward the ravine.",
        "I will take first watch. Gribba, keep the fire low.",
        "I found human tracks beyond camp. I wanted you to know first.",
    ]


def test_stage_chat_messages_and_read_cursors_use_standard_autosave(monkeypatch):
    import app as app_module

    flask_app = app_module.create_app({"TESTING": True})
    saved_worlds = []
    monkeypatch.setattr(app_module, "save_autosave", lambda world: saved_worlds.append(world))
    # Boot safely without loading a user's autosave, then exercise the real
    # production after_request hook with its save call replaced by a spy.
    flask_app.config["TESTING"] = False
    client = flask_app.test_client()

    posted = client.post("/api/stage-chat/messages", json={
        "author": "User", "channel_id": "public", "text": "Autosave smoke check",
    })
    read = client.post("/api/stage-chat/read", json={
        "character": "User", "channel_id": "public", "mode": "all",
    })

    assert posted.status_code == 200
    assert read.status_code == 200
    assert saved_worlds == [flask_app.world, flask_app.world]
    assert flask_app.world.stage_chat.participants["User"]["last_read_message_ids"]["public"] == 1
