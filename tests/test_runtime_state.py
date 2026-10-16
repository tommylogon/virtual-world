from player import Player
from graph import EDGE_CONNECTION, EDGE_IN, Edge, Node
from app import create_app


def test_runtime_state_returns_only_the_selected_characters_scope(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    world = app.world
    world.world_scopes = {
        "room_scope": {"id": "room_scope", "name": "Room Scope"},
        "far_scope": {"id": "far_scope", "name": "Far Scope"},
    }
    world.graph.add_node(Node(
        id="area_room", type="area", name="Room",
        properties={"world_scope_id": "room_scope"}))
    world.graph.add_node(Node(
        id="area_far", type="area", name="Far Away",
        properties={"world_scope_id": "far_scope"}))
    world.graph.add_node(Node(id="item_lamp_runtime", type="item", name="Lamp"))
    world.graph.add_edge(Edge(
        source="item_lamp_runtime", target="area_room", type=EDGE_IN))
    world.graph.add_node(Node(
        id="way_gate", type="way", name="Gateway",
        properties={
            "area_from_id": "area_room",
            "area_to_id": "area_far",
            "target_area_id": "area_far",
            "target_scope_id": "far_scope",
            "world_scope_id": "room_scope",
        }))
    world.graph.add_edge(Edge(
        source="area_room", target="way_gate", type=EDGE_CONNECTION))
    world.graph.add_edge(Edge(
        source="way_gate", target="area_far", type=EDGE_CONNECTION))

    player = Player("Alice")
    player.current_area = "Room"
    world.player_manager.add_player(player)
    world.record_turn_event("Alice", "move", "entered the room", area_name="Room")
    world.record_turn_event("Far Resident", "move", "left the far room", area_name="Far Away")
    world.world_index.reindex(world.graph, world.world_scopes)
    world.world_index.unload(world.graph, "room_scope")

    response = app.test_client().get(
        f"/api/runtime/state?character_id={player.id}")

    assert response.status_code == 200
    state = response.get_json()
    assert state["snapshot_type"] == "character_runtime"
    assert state["character_ids"] == [player.id]
    assert state["scope_ids"] == ["room_scope"]
    assert set(state["players"]) == {"Alice"}
    assert state["player_node_ids"] == {"Alice": player.node_id}
    assert [event["actor"] for event in state["turn_events"]] == ["Alice"]
    assert set(state["areas_by_id"]) == {"area_room"}
    assert set(state["graph"]["nodes"]) == {
        "area_room", "item_lamp_runtime", "way_gate", player.node_id}
    assert "area_far" not in state["graph"]["nodes"]


def test_runtime_state_requires_a_known_stable_character_id(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})

    assert app.test_client().get("/api/runtime/state").status_code == 400
    assert app.test_client().get(
        "/api/runtime/state?character_id=not-a-character").status_code == 404


def test_runtime_state_unions_the_scopes_of_multiple_characters(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    world = app.world
    world.world_scopes = {
        "north_scope": {"id": "north_scope", "name": "North"},
        "south_scope": {"id": "south_scope", "name": "South"},
    }
    for area_id, name, scope_id in (
            ("area_north_room", "North Room", "north_scope"),
            ("area_south_room", "South Room", "south_scope")):
        world.graph.add_node(Node(
            id=area_id, type="area", name=name,
            properties={"world_scope_id": scope_id}))

    north = Player("North Resident")
    north.current_area = "North Room"
    south = Player("South Resident")
    south.current_area = "South Room"
    world.player_manager.add_player(north)
    world.player_manager.add_player(south)

    response = app.test_client().get(
        "/api/runtime/state"
        f"?character_id={north.id}&character_id={south.id}")

    assert response.status_code == 200
    state = response.get_json()
    assert state["character_ids"] == [north.id, south.id]
    assert state["scope_ids"] == ["north_scope", "south_scope"]
    assert set(state["players"]) == {"North Resident", "South Resident"}
    assert set(state["areas_by_id"]) == {"area_north_room", "area_south_room"}
