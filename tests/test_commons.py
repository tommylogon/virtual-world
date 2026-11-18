import json
from types import SimpleNamespace
from pathlib import Path

from flask import Flask

from engine.commons import ChatAuthorizationError, Commons
from routes.action_handlers import handle_get_state
from routes.memories import register_memories_routes
from routes.commons import register_commons_routes
from routes.pages import register_pages_routes
from player import Player
from virtual_world_engine import VirtualWorld


def _commons_app():
    character = SimpleNamespace(
        name="Mira",
        traits={"patient": True},
        personality="Careful and dry-witted.",
        description="A quiet traveler.",
        base_description="",
        current_area="Kitchen",
        inventory=["not part of the commons"],
    )
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.world = SimpleNamespace(
        players={"Mira": character, "Lysa": SimpleNamespace(name="Lysa")},
        commons=Commons(),
        time_ticks=0,
    )
    register_commons_routes(app)
    return app


def test_public_chat_read_cursor_advances_only_on_explicit_read():
    chat = Commons()
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
    chat = Commons()
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
    chat = Commons()
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
    chat = Commons()
    group = chat.create_group("Mira", "Camp plans", ["Mira", "Lysa"])
    chat.update_group_members(group["id"], "Mira", add=["User"])
    chat.post_message("User", "I will bring the map.", channel_id=group["id"])

    restored = Commons()
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
    app = _commons_app()
    client = app.test_client()
    chat = app.world.commons
    group = chat.create_group("Mira", "The night watch", ["Mira", "Lysa"])
    chat.post_message("Mira", "Private detail.", channel_id=group["id"])

    user_state = client.get("/api/commons/state?as=User").get_json()
    mira_state = client.get("/api/commons/state?as=Mira").get_json()
    assert [channel["id"] for channel in user_state["channels"]] == ["public"]
    assert [channel["id"] for channel in mira_state["channels"]] == ["public", group["id"]]

    denied_read = client.post("/api/commons/read", json={
        "character": "User", "channel_id": group["id"], "mode": "all",
    })
    denied_send = client.post("/api/commons/messages", json={
        "author": "User", "channel_id": group["id"], "text": "Not allowed.",
    })
    allowed_read = client.post("/api/commons/read", json={
        "character": "Mira", "channel_id": group["id"], "mode": "all",
    })
    assert denied_read.status_code == 403
    assert denied_send.status_code == 403
    assert "Private detail." not in denied_read.get_data(as_text=True)
    assert [message["text"] for message in allowed_read.get_json()["messages"]] == ["Private detail."]


def test_town_board_theme_allows_posts_and_letters_but_disables_group_conversations():
    app = _commons_app()
    client = app.test_client()
    chat = app.world.commons
    group = chat.create_group("Mira", "Night watch", ["Mira", "Lysa"])
    chat.post_message("Mira", "Keep watch.", channel_id=group["id"])

    changed = client.post("/api/commons/theme", json={"theme": "town_board"})
    state = client.get("/api/commons/state?as=Mira").get_json()
    denied_create = client.post("/api/commons/channels", json={
        "creator": "Mira", "kind": "group", "name": "Secret plans", "members": ["Mira", "Lysa"],
    })
    denied_read = client.post("/api/commons/read", json={
        "character": "Mira", "channel_id": group["id"], "mode": "all",
    })
    denied_send = client.post("/api/commons/messages", json={
        "author": "Mira", "channel_id": group["id"], "text": "Still unavailable.",
    })
    dm = client.post("/api/commons/channels", json={
        "creator": "Mira", "kind": "dm", "other": "Lysa",
    })

    assert changed.status_code == 200
    assert changed.get_json()["theme"] == "town_board"
    assert state["theme"] == "town_board"
    assert {channel["kind"] for channel in state["channels"]} == {"public"}
    assert denied_create.status_code == 403
    assert denied_read.status_code == 403
    assert denied_send.status_code == 403
    assert dm.status_code == 201
    assert dm.get_json()["channel"]["kind"] == "dm"
    assert chat.channels[group["id"]]["members"] == ["Mira", "Lysa"]

    switched_back = client.post("/api/commons/theme", json={"theme": "live_social"})
    restored_channels = client.get("/api/commons/state?as=Mira").get_json()["channels"]
    assert switched_back.status_code == 200
    assert {channel["kind"] for channel in restored_channels} == {"public", "group", "dm"}


def test_commons_theme_route_rejects_unknown_or_non_string_modes():
    app = _commons_app()
    client = app.test_client()

    assert client.post("/api/commons/theme", json={"theme": "letters"}).status_code == 400
    assert client.post("/api/commons/theme", json={"theme": []}).status_code == 400


def test_commons_state_lists_only_characters_whose_names_the_perspective_knows():
    mira = Player("Mira")
    lysa = Player("Lysa")
    lysa.autonomy = False
    stranger = Player("Stranger")
    stranger.simple_npc = True
    mira.relationships = {
        "Lysa": {"first_sighting": False},
        "Stranger": {"first_sighting": True},
    }
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.world = SimpleNamespace(
        players={
            "Mira": mira,
            "Lysa": lysa,
            "Stranger": stranger,
        },
        commons=Commons(),
        time_ticks=0,
    )
    register_commons_routes(app)

    response = app.test_client().get("/api/commons/state?as=Mira")

    assert response.status_code == 200
    assert response.get_json()["known_characters"] == ["Lysa"]
    participants = response.get_json()["participants"]
    assert participants["Mira"]["control_mode"] == "llm"
    assert participants["Lysa"]["control_mode"] == "human"
    assert participants["Stranger"]["control_mode"] == "npc"


def test_former_page_url_redirects_to_commons():
    template_root = Path(__file__).resolve().parents[1] / "templates"
    app = Flask(__name__, template_folder=str(template_root))
    register_pages_routes(app)
    client = app.test_client()

    old_page = client.get("/stage-chat")
    current_page = client.get("/commons")

    assert old_page.status_code == 301
    assert old_page.headers["Location"].endswith("/commons")
    assert current_page.status_code == 200
    assert "The Commons" in current_page.get_data(as_text=True)


def test_commons_context_projects_existing_player_identity_without_world_state():
    app = _commons_app()
    client = app.test_client()
    response = client.get("/api/commons/characters/Mira")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["name"] == "Mira"
    assert payload["traits"] == {"patient": True}
    assert payload["personality"] == "Careful and dry-witted."
    assert payload["description"] == "A quiet traveler."
    assert payload["current_area"] == "Kitchen"
    assert "inventory" not in payload
    assert client.get("/api/commons/characters/Unknown").status_code == 404


def test_commons_character_context_with_live_world_and_player_manager():
    world = VirtualWorld()
    world.add_player(Player("Elena"))
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.world = world
    register_commons_routes(app)
    client = app.test_client()

    response = client.get("/api/commons/characters/Elena")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["name"] == "Elena"
    assert "state" in payload


def test_commons_memory_uses_existing_player_memories_collection():
    app = _commons_app()
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
    assert not hasattr(player, "commons_memories")


def test_world_state_payload_does_not_publish_private_commons_channels():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.world = SimpleNamespace(
        to_dict=lambda lite=False: {"players": {}, "commons": {"secret": "private text"}},
        scenario_ended=False,
        _restart_requested=False,
    )
    with app.test_request_context("/api/state"):
        response = handle_get_state(app)
    assert response.get_json().get("commons") is None


def test_saved_world_round_trips_chat_communication_but_scenario_export_drops_runtime_chat():
    world = VirtualWorld()
    world.commons_theme = "town_board"
    group = world.commons.create_group("Mira", "Night watch", ["Mira", "Lysa"])
    world.commons.post_message("Mira", "I will take first watch.", channel_id=group["id"])
    world.commons.read_messages("Lysa", mode="all", channel_id=group["id"])

    saved = world.to_dict()
    assert "commons" in saved
    assert "stage_chat" not in saved
    restored = VirtualWorld()
    restored.load_from_dict(saved)
    assert restored.commons.channels[group["id"]]["members"] == ["Mira", "Lysa"]
    assert restored.commons.read_messages("Mira", mode="all", channel_id=group["id"])[0]["text"] == "I will take first watch."
    assert restored.commons.participants["Lysa"]["last_read_message_ids"][group["id"]] == 1
    scenario = world.to_scenario_dict()
    assert "commons" not in scenario
    assert scenario["commons_theme"] == "town_board"
    assert restored.commons_theme == "town_board"


def test_legacy_saved_communication_key_migrates_to_commons():
    world = VirtualWorld()
    group = world.commons.create_group("Mira", "Night watch", ["Mira", "Lysa"])
    world.commons.post_message("Mira", "I will take first watch.", channel_id=group["id"])
    old_save = world.to_dict()
    old_save["stage_chat"] = old_save.pop("commons")

    restored = VirtualWorld()
    restored.load_from_dict(old_save)

    assert restored.commons.channels[group["id"]]["members"] == ["Mira", "Lysa"]
    assert restored.commons.messages[0]["text"] == "I will take first watch."
    assert "commons" in restored.to_dict()
    assert "stage_chat" not in restored.to_dict()


def test_kraktooth_scenario_authors_public_group_and_dm_conversations():
    scenario_path = Path(__file__).resolve().parents[1] / "data" / "scenarios" / "kraktooth_goblin_camp.json"
    with scenario_path.open(encoding="utf-8") as source:
        scenario = json.load(source)

    world = VirtualWorld()
    world.load_from_dict(scenario)
    channels = world.commons.list_channels("Vekka")
    channel_kinds = {channel["kind"] for channel in channels}
    scenario_players = set(world.players)

    assert channel_kinds == {"public", "group", "dm"}
    assert {"Vekka", "Zikka", "Gribba"} <= scenario_players
    assert all(set(channel["members"]) <= scenario_players
               for channel in channels if channel["kind"] != "public")
    assert world.commons.list_channels("Rag-Tail") == [
        channel for channel in world.commons.list_channels("Rag-Tail")
        if channel["kind"] == "public"
    ]
    assert [message["text"] for message in world.commons.messages] == [
        "Human tracks cross the north trail and turn toward the ravine.",
        "I will take first watch. Gribba, keep the fire low.",
        "I found human tracks beyond camp. I wanted you to know first.",
    ]


def test_commons_messages_and_read_cursors_use_standard_autosave(monkeypatch):
    import app as app_module

    flask_app = app_module.create_app({"TESTING": True})
    saved_worlds = []
    monkeypatch.setattr(app_module, "save_autosave", lambda world: saved_worlds.append(world))
    # Boot safely without loading a user's autosave, then exercise the real
    # production after_request hook with its save call replaced by a spy.
    flask_app.config["TESTING"] = False
    client = flask_app.test_client()

    posted = client.post("/api/commons/messages", json={
        "author": "User", "channel_id": "public", "text": "Autosave smoke check",
    })
    read = client.post("/api/commons/read", json={
        "character": "User", "channel_id": "public", "mode": "all",
    })

    assert posted.status_code == 200
    assert read.status_code == 200
    assert saved_worlds == [flask_app.world, flask_app.world]
    assert flask_app.world.commons.participants["User"]["last_read_message_ids"]["public"] == 1


def test_commons_inner_drawer_css_dark_theme():
    """task-893: The inner world drawer uses the dark theme palette and no white panel."""
    import re
    css_path = Path(__file__).resolve().parent.parent / "static" / "css" / "commons.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".commons-inner-drawer" in css
    # Ensure white panel background is gone
    assert not re.search(r"\.commons-inner-drawer\s*\{[^}]*background:\s*#ffffff", css)
    # Ensure dark block includes .commons-inner-drawer
    assert re.search(r"\.commons-topbar,[^}]*\.commons-inner-drawer\s*\{", css)


def test_commons_edit_message_engine_and_memory():
    chat = Commons()
    chat.set_participant("Mira")
    msg = chat.post_message("Mira", "I will head to the river.", tick=5)
    msg_id = msg["id"]

    mira = SimpleNamespace(name="Mira", memories=[{"text": "I will head to the river.", "tick": 5}])
    players = {"Mira": mira}

    edited = chat.edit_message(msg_id, "Mira", "I will head to the forest.", players=players)
    assert edited["text"] == "I will head to the forest."
    assert edited["edited"] is True
    assert edited["original_text"] == "I will head to the river."
    assert "edited_at" in edited
    assert mira.memories[0]["text"] == "I will head to the forest."
    assert mira.memories[0]["edited"] is True

    # Authorization failure on editing another author's message
    try:
        chat.edit_message(msg_id, "Lysa", "Trying to change your words.")
    except ChatAuthorizationError:
        pass
    else:
        raise AssertionError("Expected ChatAuthorizationError when non-author edits message")


def test_commons_delete_message_keeps_tombstone_and_updates_memory():
    chat = Commons()
    chat.set_participant("Mira")
    chat.set_participant("Lysa")
    first = chat.post_message("Mira", "First message")
    second = chat.post_message("Mira", "Mistake to be retracted")
    third = chat.post_message("Lysa", "Third message")

    mira = SimpleNamespace(name="Mira", memories=[{"text": "Said: Mistake to be retracted"}])
    players = {"Mira": mira}

    # Non-author cannot delete
    try:
        chat.delete_message(second["id"], "Lysa", players=players)
    except ChatAuthorizationError:
        pass
    else:
        raise AssertionError("Expected ChatAuthorizationError when non-author deletes message")

    # Author deletes message
    deleted = chat.delete_message(second["id"], "Mira", players=players)
    assert deleted["deleted"] is True
    assert deleted["text"] == ""
    assert deleted["original_text"] == "Mistake to be retracted"
    assert "deleted_at" in deleted
    assert mira.memories[0]["retracted"] is True
    assert "[Retracted by Mira]" in mira.memories[0]["text"]

    # Verify ID sequence in chat.messages is preserved (tombstone)
    msg_ids = [m["id"] for m in chat.messages]
    assert msg_ids == [first["id"], second["id"], third["id"]]

    # Read messages ignores deleted messages by default
    read = chat.read_messages("Lysa", mode="all")
    assert [m["id"] for m in read] == [first["id"], third["id"]]
    assert chat.participants["Lysa"]["last_read_message_ids"]["public"] == third["id"]

    # Unread count ignores deleted messages
    assert chat.get_unread_count("Lysa", "public") == 0


def test_commons_routes_edit_and_delete_message():
    app = _commons_app()
    client = app.test_client()

    posted = client.post("/api/commons/messages", json={
        "author": "Mira", "channel_id": "public", "text": "Heading south",
    })
    assert posted.status_code == 200
    msg_id = posted.get_json()["message"]["id"]

    # 403 on non-author edit
    bad_edit = client.patch(f"/api/commons/messages/{msg_id}", json={
        "author": "Lysa", "text": "Heading north",
    })
    assert bad_edit.status_code == 403

    # 200 on author edit
    good_edit = client.patch(f"/api/commons/messages/{msg_id}", json={
        "author": "Mira", "text": "Heading north actually",
    })
    assert good_edit.status_code == 200
    assert good_edit.get_json()["message"]["text"] == "Heading north actually"
    assert good_edit.get_json()["message"]["edited"] is True

    # 403 on non-author delete
    bad_del = client.delete(f"/api/commons/messages/{msg_id}", json={
        "author": "Lysa",
    })
    assert bad_del.status_code == 403

    # 200 on author delete
    good_del = client.delete(f"/api/commons/messages/{msg_id}", json={
        "author": "Mira",
    })
    assert good_del.status_code == 200
    assert good_del.get_json()["deleted"] is True

    # GET messages does not return the deleted message
    feed = client.get("/api/commons/messages?as=Mira&channel_id=public")
    assert feed.status_code == 200
    msg_ids = [m["id"] for m in feed.get_json()["messages"]]
    assert msg_id not in msg_ids


def test_message_with_attachment_and_no_text_succeeds():
    app = _commons_app()
    client = app.test_client()
    posted = client.post("/api/commons/messages", json={
        "author": "Mira",
        "channel_id": "public",
        "text": "",
        "attachments": [
            {
                "id": "att1",
                "url": "/api/commons/attachments/att1.png",
                "caption": "Map of the ruins",
                "mime_type": "image/png",
                "size": 1024,
            }
        ]
    })
    assert posted.status_code == 200
    msg = posted.get_json()["message"]
    assert msg["text"] == ""
    assert len(msg["attachments"]) == 1
    assert msg["attachments"][0]["caption"] == "Map of the ruins"


def test_attachment_upload_size_limit_and_mime_validation():
    app = _commons_app()
    client = app.test_client()
    import io
    # Valid image upload
    data = {
        "file": (io.BytesIO(b"fake png data"), "map.png"),
        "caption": "Survey map",
    }
    upload_res = client.post("/api/commons/attachments/upload", data=data, content_type="multipart/form-data")
    assert upload_res.status_code == 200
    res_json = upload_res.get_json()
    assert res_json["caption"] == "Survey map"
    assert res_json["mime_type"] == "image/png"
    assert "url" in res_json

    # Invalid extension rejected
    bad_data = {
        "file": (io.BytesIO(b"malicious script"), "script.exe"),
    }
    bad_res = client.post("/api/commons/attachments/upload", data=bad_data, content_type="multipart/form-data")
    assert bad_res.status_code == 400
    assert "Unsupported file extension" in bad_res.get_json()["error"]


def test_commons_mute_unmute_and_serialization():
    chat = Commons()
    group = chat.create_group("Mira", "Night watch", ["Mira", "Lysa"])

    assert chat.set_muted("Mira", group["id"], True) is True
    assert chat.is_muted("Mira", group["id"]) is True
    assert chat.is_muted("Lysa", group["id"]) is False

    mira_channels = {ch["id"]: ch for ch in chat.list_channels("Mira")}
    lysa_channels = {ch["id"]: ch for ch in chat.list_channels("Lysa")}
    assert mira_channels[group["id"]]["muted"] is True
    assert mira_channels["public"]["muted"] is False
    assert lysa_channels[group["id"]]["muted"] is False

    saved = chat.to_dict()
    restored = Commons()
    restored.from_dict(saved)
    assert restored.is_muted("Mira", group["id"]) is True
    assert restored.is_muted("Lysa", group["id"]) is False
    restored_mira = {ch["id"]: ch for ch in restored.list_channels("Mira")}
    assert restored_mira[group["id"]]["muted"] is True

    assert restored.set_muted("Mira", group["id"], False) is False
    assert restored.is_muted("Mira", group["id"]) is False
    restored_mira_after = {ch["id"]: ch for ch in restored.list_channels("Mira")}
    assert restored_mira_after[group["id"]]["muted"] is False

    try:
        restored.set_muted("Outsider", group["id"], True)
        assert False, "Expected ChatAuthorizationError"
    except ChatAuthorizationError:
        pass


def test_commons_mute_route_and_state_perspective():
    app = _commons_app()
    client = app.test_client()
    group = app.world.commons.create_group("Mira", "Night watch", ["Mira", "Lysa"])

    mute_res = client.post(
        f"/api/commons/channels/{group['id']}/mute",
        json={"actor": "Mira", "muted": True},
    )
    assert mute_res.status_code == 200
    assert mute_res.get_json() == {"channel_id": group["id"], "muted": True}

    mira_state = client.get("/api/commons/state?as=Mira").get_json()
    mira_channels = {ch["id"]: ch for ch in mira_state["channels"]}
    assert mira_channels[group["id"]]["muted"] is True
    assert mira_channels["public"]["muted"] is False
    assert group["id"] in mira_state["participants"]["Mira"]["muted_channels"]

    lysa_state = client.get("/api/commons/state?as=Lysa").get_json()
    lysa_channels = {ch["id"]: ch for ch in lysa_state["channels"]}
    assert lysa_channels[group["id"]]["muted"] is False

    unmute_res = client.post(
        f"/api/commons/channels/{group['id']}/mute",
        json={"actor": "Mira", "muted": False},
    )
    assert unmute_res.status_code == 200
    assert unmute_res.get_json() == {"channel_id": group["id"], "muted": False}

    mira_state_after = client.get("/api/commons/state?as=Mira").get_json()
    mira_channels_after = {ch["id"]: ch for ch in mira_state_after["channels"]}
    assert mira_channels_after[group["id"]]["muted"] is False
    assert group["id"] not in mira_state_after["participants"]["Mira"]["muted_channels"]

    bad_actor = client.post(
        f"/api/commons/channels/{group['id']}/mute",
        json={"actor": "Nobody", "muted": True},
    )
    assert bad_actor.status_code == 404

    bad_channel = client.post(
        "/api/commons/channels/missing_channel/mute",
        json={"actor": "Mira", "muted": True},
    )
    assert bad_channel.status_code == 404


def test_commons_world_clock_and_optional_advance_tick():
    app = _commons_app()
    client = app.test_client()

    st = client.get("/api/commons/state?as=Mira")
    assert st.status_code == 200
    st_data = st.get_json()
    assert st_data["world_clock"]["time_ticks"] == 0

    r1 = client.post("/api/commons/messages", json={
        "author": "Mira",
        "channel_id": "public",
        "text": "Still at tick 0",
    })
    assert r1.status_code == 200
    assert r1.get_json()["message"]["tick"] == 0

    r2 = client.post("/api/commons/messages", json={
        "author": "Mira",
        "channel_id": "public",
        "text": "Late night text",
        "advance_tick": True,
    })
    assert r2.status_code == 200
    assert r2.get_json()["message"]["tick"] == 1

    st2 = client.get("/api/commons/state?as=Mira")
    assert st2.get_json()["world_clock"]["time_ticks"] == 1


def test_commons_anchored_clock_progression_and_standalone_isolation():
    chat = Commons()
    chat.set_anchored_clock("2016-10-14T23:00:00", now_epoch=1000.0)
    assert chat.current_anchored_iso(now_epoch=1125.0) == "2016-10-14T23:02:05"
    assert chat.format_iso_label("2016-10-14T23:02:05") == "Oct 14, 2016 23:02"

    app = _commons_app()
    client = app.test_client()
    # Seed a connected message
    client.post("/api/commons/messages", json={"author": "Mira", "text": "Connected msg"})
    assert len(app.world.commons.messages) == 1

    # Switch to Standalone mode
    mode_res = client.post("/api/commons/mode", json={"use_viwo_state": False})
    assert mode_res.status_code == 200
    assert mode_res.get_json()["clock_mode"] == "standalone"

    # Set 2016 Millwood anchor clock
    clk_res = client.post("/api/commons/clock", json={"date": "2016-10-14", "time": "23:15"})
    assert clk_res.status_code == 200
    assert clk_res.get_json()["current_datetime"].startswith("2016-10-14T23:15")

    # Post standalone message (does not touch live world.commons or world.time_ticks)
    s_msg = client.post("/api/commons/messages", json={
        "author": "Mira",
        "text": "Standalone late night",
        "advance_tick": True,
    })
    assert s_msg.status_code == 200
    assert s_msg.get_json()["message"]["world_datetime"].startswith("2016-10-14T23:15")
    assert len(app.world.commons.messages) == 1
    assert app.world.time_ticks == 0

    # Standalone memory does not mutate app.world.players["Mira"].memories
    m_res = client.post("/api/commons/memories/Mira", json={"text": "Texted late in 2016"})
    assert m_res.status_code == 201
    assert m_res.get_json()["memory"]["world_datetime"].startswith("2016-10-14T23:15")
    assert getattr(app.world.players["Mira"], "memories", []) == []

    # Fork a branch, post on fork, switch back to main -> zero contamination
    fork_res = client.post("/api/commons/branches", json={"name": "alt-night"})
    assert fork_res.status_code == 201
    fork_id = fork_res.get_json()["active_branch_id"]
    client.post("/api/commons/messages", json={"author": "Lysa", "text": "Only on fork"})
    fork_msgs = client.get("/api/commons/messages?channel_id=public&as=Mira").get_json()["messages"]
    assert len(fork_msgs) == 2

    sw_res = client.post("/api/commons/branches/switch", json={"branch_id": "main"})
    assert sw_res.status_code == 200
    main_msgs = client.get("/api/commons/messages?channel_id=public&as=Mira").get_json()["messages"]
    assert len(main_msgs) == 1
    assert main_msgs[0]["text"] == "Standalone late night"

    # Reset standalone session cleanly without affecting live Viwo
    rst = client.post("/api/commons/reset", json={})
    assert rst.status_code == 200
    assert len(client.get("/api/commons/messages?channel_id=public&as=Mira").get_json()["messages"]) == 0

    client.post("/api/commons/mode", json={"use_viwo_state": True})
    assert len(app.world.commons.messages) == 1
    assert client.post("/api/commons/reset", json={}).status_code == 400


