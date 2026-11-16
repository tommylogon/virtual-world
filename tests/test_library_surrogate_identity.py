"""Tests for task-667: Library entries keyed by surrogate identity rather than display string."""

import os
import json
import tempfile
import shutil
from pathlib import Path
from flask import Flask

from app import create_app
from graph import Node
from player import Player
from engine import sync
from routes.helpers import load_registry, save_registry, get_surrogate_id
from routes.library_ops import handle_library_rename, handle_library_import_character, _refresh_character


def test_surrogate_key_indexing_and_alias_resolution():
    tmpdir = tempfile.mkdtemp()
    try:
        char_dir = Path(tmpdir) / "library" / "characters"
        char_dir.mkdir(parents=True, exist_ok=True)

        entry_data = {
            "character_id": "ch_test_1234",
            "name": "Test Blacksmith",
            "personality": "Gruff and careful smith.",
            "aliases": ["old_smith_name"],
        }
        with open(char_dir / "test_blacksmith.json", "w", encoding="utf-8") as f:
            json.dump(entry_data, f)

        reg = load_registry(tmpdir, "characters.json")

        # Resolvable by filename
        assert "test_blacksmith" in reg
        assert reg["test_blacksmith"]["personality"] == "Gruff and careful smith."

        # Resolvable by surrogate key
        assert "ch_test_1234" in reg
        assert reg["ch_test_1234"] is reg["test_blacksmith"]

        # Resolvable by recorded alias
        assert "old_smith_name" in reg
        assert reg["old_smith_name"] is reg["test_blacksmith"]

        # save_registry does not write surrogate key or alias as separate files
        save_registry(tmpdir, "characters.json", reg)
        files = os.listdir(char_dir)
        assert files == ["test_blacksmith.json"]
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_rename_preserves_bound_node_resolution_roundtrip():
    """Round-trip: rename Harren Cobb -> anything, refresh the blacksmith node,

    read player.personality back and confirm it is the blacksmith's and not a neighbour's.
    """
    app = create_app({"TESTING": True})
    scenario_path = Path(__file__).resolve().parents[1] / "data" / "scenarios" / "kraktooth_goblin_camp.json"
    with scenario_path.open(encoding="utf-8") as source:
        scenario = json.load(source)
    app.world.load_from_dict(scenario)

    client = app.test_client()

    # Get blacksmith node from world
    world = app.world
    pm = world.player_manager
    player = pm.get_player("Eldenford Blacksmith")
    assert player is not None

    node_id = pm.get_player_node_id("Eldenford Blacksmith")
    node = world.graph.get_node(node_id)
    assert node is not None
    # Current library link is harren_cobb or its surrogate key
    assert node.properties.get("library_id") in ("harren_cobb", "ch_b74fdf7f")

    # Rename harren_cobb -> eldenford_master_smith via API
    rename_resp = client.post("/api/library/characters/harren_cobb/rename", json={
        "new_id": "eldenford_master_smith"
    })
    try:
        assert rename_resp.status_code == 200

        # Refresh blacksmith node from library without re-linking
        refresh_resp = client.post("/api/library/refresh-to-world", json={
            "node_id": node_id
        })
        assert refresh_resp.status_code == 200

        # Verify player personality is still Harren Cobb's and not another character's
        refreshed_player = pm.get_player("Eldenford Blacksmith")
        assert "Harren Cobb" in refreshed_player.personality
        assert "forty-one" in refreshed_player.personality
        assert "Merchant" not in refreshed_player.personality
    finally:
        # Revert rename back to harren_cobb
        client.post("/api/library/characters/eldenford_master_smith/rename", json={
            "new_id": "harren_cobb"
        })


def test_name_guess_resolves_surrogate_and_fails_on_ambiguity():
    reg = {
        "harren_cobb": {"character_id": "ch_smith_1", "name": "Harren Cobb"},
        "ch_smith_1": {"character_id": "ch_smith_1", "name": "Harren Cobb"},
        "dup_a": {"character_id": "ch_dup_a", "name": "Merchant"},
        "ch_dup_a": {"character_id": "ch_dup_a", "name": "Merchant"},
        "dup_b": {"character_id": "ch_dup_b", "name": "Merchant"},
        "ch_dup_b": {"character_id": "ch_dup_b", "name": "Merchant"},
    }

    # Unique name guess returns the surrogate id
    node = Node(id="char_test_1", type="character", name="Harren Cobb", properties={})
    resolved = sync.resolve_template_id(node, registry=reg)
    assert resolved == "ch_smith_1"

    # Ambiguous name guess raises AmbiguousTemplateError
    ambig_node = Node(id="char_test_2", type="character", name="Merchant", properties={})
    try:
        sync.resolve_template_id(ambig_node, registry=reg)
    except sync.AmbiguousTemplateError as exc:
        assert "Ambiguous template name 'Merchant'" in str(exc)
    else:
        raise AssertionError("Expected AmbiguousTemplateError for duplicate names")


def test_spawning_two_instances_from_one_template_creates_distinct_players():
    app = create_app({"TESTING": True})
    client = app.test_client()

    resp1 = client.post("/api/library/import/character/harren_cobb", json={
        "area": "area_farm"
    })
    assert resp1.status_code == 200
    name1 = resp1.get_json()["player"]

    resp2 = client.post("/api/library/import/character/harren_cobb", json={
        "area": "area_farm"
    })
    assert resp2.status_code == 200
    name2 = resp2.get_json()["player"]

    pm = app.world.player_manager
    p1 = pm.get_player(name1)
    p2 = pm.get_player(name2)

    assert p1 is not None and p2 is not None
    assert p1.id != p2.id
    assert p1 is not p2
