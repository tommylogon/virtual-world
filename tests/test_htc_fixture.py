"""Tests for the HTC Fixture scenario (task-694).

Validates the dedicated HTC fixture world authored to exercise turn-panel surfaces:
- Painted cell + world_scope_id on every area for minimap lattice rendering
- Duplicate character display names in one area (task-446/task-448/bug-521)
- Shared nickname across areas (task-447/task-448)
- Hidden false wall (bug-23 negative), locked door, and blocked way
- Scripted simple NPC with zombie behavior shapes
- Human player with preconceived knowledge
- Item with flavor trigger and grapple-ready prop
- Integrity checks pass cleanly on load
"""

import json
from pathlib import Path
import pytest

from app import create_app
from engine.scene_snapshot import build_scene
from tools.validate_scenario import validate_scenario


FIXTURE_PATH = Path(__file__).parent.parent / "data" / "scenarios" / "htc_fixture.json"


@pytest.fixture
def fixture_data():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def app():
    application = create_app({"TESTING": True})
    return application


@pytest.fixture
def loaded_world(app, fixture_data):
    with app.app_context():
        app.world.load_from_dict(fixture_data)
        return app.world


def test_scenario_validation_passes(fixture_data):
    """The scenario must be authoring-error free under validate_scenario."""
    issues = validate_scenario(fixture_data)
    assert not issues, f"Scenario validation issues: {issues}"


def test_areas_painted_cell_and_world_scope(fixture_data, loaded_world):
    """Every area must carry painted cell coordinates and world_scope_id for the minimap lattice."""
    nodes = fixture_data["graph"]["nodes"]
    areas = [n for n in nodes.values() if n.get("type") == "area"]
    assert 10 <= len(areas) <= 20, f"Expected 10-20 areas, found {len(areas)}"

    scope_id = "htc_scope"
    assert scope_id in fixture_data.get("world_scopes", {})

    for area in areas:
        aid = area["id"]
        props = area.get("properties", {})
        assert "cell" in props, f"Area {aid} missing cell coordinates"
        cell = props["cell"]
        assert "x" in cell and "y" in cell, f"Area {aid} cell missing x or y"
        assert props.get("world_scope_id") == scope_id, f"Area {aid} missing or mismatch world_scope_id"


def test_duplicate_display_names_and_shared_nicknames(loaded_world):
    """Tests two characters sharing a display name in one area, and two sharing a nickname across areas."""
    guards = [p for p in loaded_world.players.values() if p.name == "Guard"]
    assert len(guards) == 2, f"Expected 2 characters named Guard, found {len(guards)}"
    assert guards[0].current_area == "Guard Room"
    assert guards[1].current_area == "Guard Room"
    assert guards[0].id != guards[1].id, "Guards must have distinct node IDs"

    # Matcher disambiguation in Guard Room
    loaded_world.set_player_area("Explorer", "Guard Room")
    resolved, candidates = loaded_world._match_character_name("Guard")
    assert resolved is None, "Ambiguous target name must not resolve silently"
    assert len(candidates) == 2
    choices = loaded_world.character_candidate_details(candidates)
    assert len(choices) == 2
    assert all(c["label"] == "Guard" for c in choices)
    assert all(c["detail"] for c in choices)
    assert choices[0]["detail"] != choices[1]["detail"], "Disambiguation details must differ"

    # Shared nickname "Doc" across areas
    doc_brown = loaded_world.players["Doctor Brown"]
    doc_holliday = loaded_world.players["Doc Holliday"]
    assert doc_brown.current_area == "Library"
    assert doc_holliday.current_area == "Courtyard"

    brown_node = loaded_world.graph.get_node("player_doctor_brown")
    holliday_node = loaded_world.graph.get_node("player_doc_holliday")
    assert "Doc" in brown_node.properties.get("aliases", [])
    assert "Doc" in holliday_node.properties.get("aliases", [])


def test_hidden_locked_and_blocked_ways(loaded_world):
    """Verifies hidden way stays absent (bug-23), locked door reports closed until discovered, and blocked way."""
    explorer = loaded_world.players["Explorer"]

    # 1. Hidden way at Library
    loaded_world.set_player_area("Explorer", "Library")
    scene_lib = build_scene(loaded_world, "Explorer")
    way_names = [w["name"] for w in scene_lib["ways"]]
    assert "false bookcase wall" not in way_names, "Hidden way must stay absent from scene"

    # 2. Locked way at Great Hall
    loaded_world.set_player_area("Explorer", "Great Hall")
    scene_hall = build_scene(loaded_world, "Explorer")
    armory_way = next((w for w in scene_hall["ways"] if "heavy oak door" in w["name"]), None)
    assert armory_way is not None
    assert armory_way["state"] == "closed"
    assert armory_way.get("known_locked") is False

    # After discovering locked aspect
    explorer.learn_way_aspect("Great Hall", "east", "locked")
    scene_hall_discovered = build_scene(loaded_world, "Explorer")
    armory_way_disc = next((w for w in scene_hall_discovered["ways"] if "heavy oak door" in w["name"]), None)
    assert armory_way_disc["state"] == "locked"
    assert armory_way_disc.get("known_locked") is True

    # 3. Blocked way at Secret Vault
    loaded_world.set_player_area("Explorer", "Secret Vault")
    scene_vault = build_scene(loaded_world, "Explorer")
    dungeon_way = next((w for w in scene_vault["ways"] if "collapsed passage" in w["name"]), None)
    assert dungeon_way is not None
    assert dungeon_way["state"] == "closed"
    explorer.learn_way_aspect("Secret Vault", "east", "blocked")
    scene_vault_disc = build_scene(loaded_world, "Explorer")
    dungeon_way_disc = next((w for w in scene_vault_disc["ways"] if "collapsed passage" in w["name"]), None)
    assert dungeon_way_disc["state"] == "blocked"


def test_scripted_simple_npc_and_human_preconceived_knowledge(loaded_world):
    """Verifies simple NPC with zombie behaviors and human player starting knowledge."""
    ghoul = loaded_world.players["Crypt Ghoul"]
    assert ghoul.simple_npc is True
    assert ghoul.current_area == "Dungeon Cell"
    triggers = {b.get("trigger") for b in ghoul.behaviors}
    assert "on_player_enter_room" in triggers
    assert "on_player_enter_area" in triggers
    assert "on_tick" in triggers

    # Human player knowledge
    explorer = loaded_world.players["Explorer"]
    assert "Courtyard" in explorer.known or "area_courtyard" in explorer.known
    assert "Great Hall" in explorer.known or "area_hall" in explorer.known


def test_flavor_trigger_item_and_grapple_prop(app, loaded_world):
    """Verifies item flavor triggers on examine and grapple prop can be targeted."""
    client = app.test_client()
    res = client.post("/api/action", json={"character": "Explorer", "action": "examine ancient_relic"}).get_json()
    assert "The runes flare with azure light as faint whispers fill your mind." in res.get("output", "")

    # Sparring dummy can be targeted with grab
    res_grab = client.post("/api/action", json={"character": "Explorer", "action": "grab sparring_dummy"}).get_json()
    assert "sparring_dummy" in res_grab.get("output", "")
