"""Tests for task-958: hide and unhide character verbs over triggers/behaviors.py
hiding edges and unified hidden state perception across room perception,
scene snapshot, examine_actions, and combat."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
import engine.actions as av
from engine.scene_snapshot import build_scene
from engine.triggers.behaviors import (
    hide_character,
    is_character_hidden,
    unhide_character,
)
from graph import EDGE_IN, Edge, Node


def _setup_two_player_room():
    app = create_app({"TESTING": True})
    w = app.world
    names = list(w.players.keys())
    assert len(names) >= 2
    hero_name, other_name = names[0], names[1]
    hero = w.players[hero_name]
    other = w.players[other_name]

    area_name = hero.current_area or "Town Square"
    w.player_manager.set_active_player(hero_name)
    w.player_manager._set_player_area(hero_name, area_name)
    other.current_area = area_name
    w.player_manager._set_player_area(other_name, area_name)

    area_id = w._get_current_area_id()
    crate = Node(
        "test_hideable_crate",
        type="item",
        name="Oak Crate",
        properties={
            "tags": ["hideable", "container"],
            "description": "A large oak crate big enough to crouch behind or inside.",
        },
    )
    rock = Node(
        "test_pebble",
        type="item",
        name="Small Pebble",
        properties={
            "tags": ["stone"],
            "description": "A tiny pebble on the floor.",
        },
    )
    w.graph.add_node(crate)
    w.graph.add_node(rock)
    w.graph.add_edge(Edge(crate.id, area_id, EDGE_IN))
    w.graph.add_edge(Edge(rock.id, area_id, EDGE_IN))
    return app, w, hero, other, area_name, area_id


def test_hide_and_unhide_registered_in_actions():
    assert av.is_valid_action("hide")
    assert av.is_valid_action("sneak")
    assert av.is_valid_action("conceal")
    assert av.is_valid_action("unhide")
    assert av.is_valid_action("reveal")
    assert av.get_action("sneak").id == "hide"
    assert av.get_action("reveal").id == "unhide"


def test_hide_and_unhide_commands_manage_edges_and_player_hidden():
    app, w, hero, other, area_name, area_id = _setup_two_player_room()
    client = app.test_client()

    # Targeted hide behind a hideable prop
    resp = client.post("/api/action", json={"action": "hide behind Oak Crate", "character": hero.name})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "hides behind Oak Crate" in data["output"]
    assert hero.hidden is True
    hidden_edges = [e for e in w.graph.edges if e.type == "hidden" and e.source == hero.name]
    assert len(hidden_edges) == 1
    assert hidden_edges[0].target == "test_hideable_crate"
    assert hidden_edges[0].properties.get("relation") == "behind"

    # Switch to hide in / hide under
    resp_in = client.post("/api/action", json={"action": "hide in Oak Crate", "character": hero.name})
    assert resp_in.get_json()["success"] is True
    assert "hides inside Oak Crate" in resp_in.get_json()["output"]
    hidden_edges = [e for e in w.graph.edges if e.type == "hidden" and e.source == hero.name]
    assert len(hidden_edges) == 1
    assert hidden_edges[0].properties.get("relation") == "in"

    resp_under = client.post("/api/action", json={"action": "hide under Oak Crate", "character": hero.name})
    assert resp_under.get_json()["success"] is True
    assert "hides under Oak Crate" in resp_under.get_json()["output"]
    hidden_edges = [e for e in w.graph.edges if e.type == "hidden" and e.source == hero.name]
    assert len(hidden_edges) == 1
    assert hidden_edges[0].properties.get("relation") == "under"

    # Reject non-hideable prop
    resp_bad = client.post("/api/action", json={"action": "hide behind Small Pebble", "character": hero.name})
    assert resp_bad.get_json()["success"] is False
    assert "not hideable" in resp_bad.get_json()["output"]

    # Unhide clears player.hidden and removes hidden edges
    resp_unhide = client.post("/api/action", json={"action": "unhide", "character": hero.name})
    assert resp_unhide.get_json()["success"] is True
    assert "steps out of hiding" in resp_unhide.get_json()["output"]
    assert hero.hidden is False
    assert not [e for e in w.graph.edges if e.type == "hidden" and e.source == hero.name]


def test_bare_hide_in_shadows_without_hideable_prop():
    app, w, hero, other, area_name, area_id = _setup_two_player_room()
    client = app.test_client()
    # Remove the crate so no hideable prop exists
    w.graph.remove_edge("test_hideable_crate", area_id, EDGE_IN)
    w.graph.remove_node("test_hideable_crate")

    resp = client.post("/api/action", json={"action": "hide", "character": hero.name})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    assert "shadows" in resp.get_json()["output"]
    assert hero.hidden is True
    hidden_edges = [e for e in w.graph.edges if e.type == "hidden" and e.source == hero.name]
    assert len(hidden_edges) == 1
    assert hidden_edges[0].properties.get("relation") == "shadows"


def test_hidden_character_masked_across_perception_scene_examine_and_combat():
    app, w, hero, other, area_name, area_id = _setup_two_player_room()
    client = app.test_client()

    # Hero hides behind the crate
    ok, _ = hide_character(w, hero.name, target="Oak Crate", relation="behind", player=hero)
    assert ok is True
    assert is_character_hidden(w, hero.name) is True
    assert w.player_manager.is_visible(hero.name) is False

    # Switch active viewer to `other`
    w.player_manager.set_active_player(other.name)

    # 1. get_players_in_area and get_area_description omit hero
    present_names = [p["name"] for p in w.player_manager.get_players_in_area(area_name)]
    assert hero.name not in present_names
    area_desc = w.get_area_description()
    assert hero.name not in area_desc

    # 2. scene_snapshot omits hero from people
    scene = build_scene(w, other.name)
    scene_people_ids = [p["id"] for p in scene["people"]]
    assert w.player_manager.get_player_node_id(hero.name) not in scene_people_ids
    hero_scene = build_scene(w, hero.name)
    assert hero_scene["you"]["hidden"] is True

    # 3. examine_actions: direct examine of hidden hero fails, and fallback people list omits hero
    with pytest.raises(ValueError) as exc_info:
        w.get_item_desc(hero.name)
    err_text = str(exc_info.value)
    things_part = err_text.split("Things you can examine right now:", 1)[1]
    assert hero.name not in things_part
    assert hero.unknown_display_name() not in things_part

    # Also verify player.state == 'stealthed' (without player.hidden) is treated identically
    unhide_character(w, hero.name, player=hero)
    hero.state = "stealthed"
    assert w.player_manager.is_visible(hero.name) is False
    scene_stealthed = build_scene(w, other.name)
    assert w.player_manager.get_player_node_id(hero.name) not in [p["id"] for p in scene_stealthed["people"]]
    with pytest.raises(ValueError) as exc_info2:
        w.get_item_desc("nonexistent_thing_xyz")
    assert hero.name not in str(exc_info2.value)

    # 4. Combat targeting: attacking hidden hero misses into empty air
    atk_msg = w._player_attack(other.name, hero.name)
    assert "not there to hit" in atk_msg

    # 5. Overt attack by hidden character clears concealment and hidden edges
    hide_character(w, hero.name, target="Oak Crate", relation="behind", player=hero)
    assert hero.hidden is True
    resp_atk = client.post("/api/action", json={"action": f"attack {other.name}", "character": hero.name})
    assert resp_atk.status_code == 200
    assert hero.hidden is False
    assert hero.state != "stealthed"
    assert not [e for e in w.graph.edges if e.type == "hidden" and e.source == hero.name]
    assert w.player_manager.is_visible(hero.name) is True


def test_active_search_reveals_hidden_character_on_perception_success(monkeypatch):
    app, w, hero, other, area_name, area_id = _setup_two_player_room()
    client = app.test_client()

    hide_character(w, hero.name, target="Oak Crate", relation="behind", player=hero)
    assert hero.hidden is True

    # Force searcher's Perception check to succeed with total 18
    monkeypatch.setattr(
        w.skills,
        "skill_check",
        lambda skill, dc, *a, **kw: (True, 18, "[Perception 18 vs DC 12: SUCCESS]"),
    )
    resp = client.post("/api/action", json={"action": "search", "character": other.name})
    assert resp.status_code == 200
    out = resp.get_json()["output"]
    assert f"You spot {hero.name} hiding nearby" in out
    assert hero.hidden is False
    assert not [e for e in w.graph.edges if e.type == "hidden" and e.source == hero.name]
