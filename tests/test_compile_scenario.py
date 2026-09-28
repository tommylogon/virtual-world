"""Tests for the folder-authoring scenario compiler (task-408)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.compile_scenario import compile_scenario


def _author(tmp_path: Path) -> Path:
    folder = tmp_path / "foldtest"
    (folder / "rooms").mkdir(parents=True)
    (folder / "ways").mkdir()
    (folder / "characters").mkdir()

    (folder / "scenario.json").write_text(json.dumps({
        "name": "Fold Test",
        "active_player": "Alice",
        "clock_start_hour": 8,
    }), encoding="utf-8")

    (folder / "rooms" / "hall.json").write_text(json.dumps({
        "name": "Hall", "description": "A narrow hall.", "tags": ["test"],
    }), encoding="utf-8")
    (folder / "rooms" / "kitchen.json").write_text(json.dumps({
        "name": "Kitchen", "description": "A steamy kitchen.",
        "tags": ["test", "kitchen"],
    }), encoding="utf-8")
    (folder / "ways" / "hall_to_kitchen.json").write_text(json.dumps({
        "name": "Hall to Kitchen",
        "properties": {"area_from": "area_hall", "area_to": "area_kitchen",
                       "pass_message": "You pass into the kitchen."},
    }), encoding="utf-8")
    (folder / "characters" / "alice.json").write_text(json.dumps({
        "name": "Alice", "description": "The cook.", "personality": "You are Alice.",
        "current_area": "area_hall", "tags": ["human"],
        "traits": {"high_metabolism": True},
    }), encoding="utf-8")
    return folder


def test_compile_is_deterministic(tmp_path):
    folder = _author(tmp_path)
    a = json.dumps(compile_scenario(folder), sort_keys=True, ensure_ascii=False)
    b = json.dumps(compile_scenario(folder), sort_keys=True, ensure_ascii=False)
    assert a == b, "same source folder must compile byte-identically"


def test_compiled_ids_and_players(tmp_path):
    scenario = compile_scenario(_author(tmp_path))
    nodes = scenario["graph"]["nodes"]
    assert "area_hall" in nodes and "area_kitchen" in nodes
    assert "player_Alice" in nodes
    assert scenario["_scenario_name"] == "Fold Test"
    assert scenario["active_player"] == "Alice"

    alice = scenario["players"]["Alice"]
    # engine convention: current_area is the area DISPLAY NAME, not the node id
    assert alice["current_area"] == "Hall"
    assert alice["traits"] == {"high_metabolism": True}


def test_compiled_scenario_carries_the_title(tmp_path):
    scenario = compile_scenario(_author(tmp_path))
    assert scenario["name"] == "Fold Test"
    assert scenario["meta"]["title"] == "Fold Test"


def test_compiled_character_keeps_the_authored_alias(tmp_path):
    """A compiled scenario must satisfy the same identity contract as the camp.

    ``engine/character_identity.collapse_character_identity`` merges the authored
    ``character_<slug>`` node into the ``player_<Name>`` anchor at load time and
    keeps the retired id resolvable, so a folder-compiled scenario that shipped
    only the anchor would lose that alias (task-408).
    """
    scenario = compile_scenario(_author(tmp_path))
    nodes = scenario["graph"]["nodes"]

    assert "character_alice" in nodes
    authored = nodes["character_alice"]
    assert authored["type"] == "character"
    assert authored["name"] == "Alice"
    assert authored["properties"]["description"] == "The cook."
    assert authored["properties"]["personality"] == "You are Alice."
    assert authored["properties"]["traits"] == {"high_metabolism": True}

    located = [e for e in scenario["graph"]["edges"]
               if e.get("type") == "in" and e.get("source") == "character_alice"]
    assert [e["target"] for e in located] == ["area_hall"]

    from engine.character_identity import collapse_character_identity
    report = collapse_character_identity(scenario["graph"], scenario["players"])
    assert report["collapsed"] == [("character_alice", "player_Alice")]
    assert report["aliases"]["character_alice"] == "player_Alice"
    assert "character_alice" not in scenario["graph"]["nodes"]
    # The collapse merges the two location edges into one, so the character is
    # still exactly where the authoring put them.
    ins = [e for e in scenario["graph"]["edges"]
           if e.get("type") == "in" and e.get("source") == "player_Alice"]
    assert [e["target"] for e in ins] == ["area_hall"]


def test_compiled_way_has_connection_edges(tmp_path):
    scenario = compile_scenario(_author(tmp_path))
    nodes = scenario["graph"]["nodes"]
    way_id = next(k for k, v in nodes.items() if v.get("type") == "way")
    conn = [e for e in scenario["graph"]["edges"]
            if e.get("type") == "connection" and e.get("target") == way_id]
    assert len(conn) == 2  # both area sides point at the way
    assert {e["source"] for e in conn} == {"area_hall", "area_kitchen"}
    assert nodes[way_id]["properties"]["pass_message"] == "You pass into the kitchen."


def test_compiled_scenario_loads_and_places_character(tmp_path):
    from app import create_app
    scenario = compile_scenario(_author(tmp_path))
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path / "data")})
    client = app.test_client()
    assert client.post("/api/load", json=scenario).status_code == 200
    scene = client.get("/api/scene/Alice").get_json()
    assert scene["area"]["name"] == "Hall"
    ids = [p["id"] for p in (scene.get("people") or [])]
    assert len(ids) == len(set(ids)), "no duplicate characters after load"
