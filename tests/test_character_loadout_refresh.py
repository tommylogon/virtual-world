"""bug-516 / task-519: one equipped shape, materialized losslessly.

The library character `equipped` field used to mean two different things:
import rewrote it to node-id strings, refresh-to-world wrote the raw template
value through. A dict entry therefore landed on the live player and
`is_exposed` -> `graph.get_node(dict)` raised TypeError, taking down
`GET /api/state` for anybody who had refreshed that character.

These tests pin the single shape:
  - `inventory` is a list of library-id references (string) or dict entries
    (node_id / library_id / per-instance properties);
  - `equipped` is a dict of slot -> list of references, resolved against the
    loaded inventory (by node id, library id, or name) to node-id strings;
  - importing and refreshing a character are the same operation for equipment.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from routes.helpers import save_registry
from graph import EDGE_TRIGGERS

WEAPON = {
    "name": "Goblin Cleaver",
    "description": "a notched cleaver",
    "actions": "examine,take,equip,unequip",
    "uses": -1,
    "weight": 2.5,
    "equip_slots": ["hand_right"],
    "current_state": "normal",
    "light_level": "dim",
    "defense": 0,
    "damage": 7,
    "damage_type": "slashing",
    "insulation": 0,
    "tags": ["weapon", "cleaver"],
    "triggers": [{
        "trigger_type": "on_examine",
        "effect_type": "message",
        "effect_params": {"message": "Notched and hungry."},
    }],
    "contents": [],
}

ARMOR = {
    "name": "Scavenged Plate",
    "description": "bent metal lashed to leather",
    "actions": "examine,take,equip,unequip",
    "uses": -1,
    "weight": 4.0,
    "equip_slots": ["torso"],
    "current_state": "normal",
    "light_level": "dim",
    "defense": 3,
    "damage": 0,
    "damage_type": "bludgeoning",
    "insulation": 1,
    "tags": ["armor"],
    "triggers": [],
    "contents": [],
}


def _fresh(tmp_path):
    (tmp_path / "library" / "items").mkdir(parents=True, exist_ok=True)
    (tmp_path / "library" / "characters").mkdir(parents=True, exist_ok=True)
    save_registry(str(tmp_path), "items.json", {
        "goblin_cleaver": dict(WEAPON),
        "scavenged_plate": dict(ARMOR),
    })
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    return app.test_client(), app


def _write_char(tmp_path, char_id, card):
    with open(tmp_path / "library" / "characters" / f"{char_id}.json",
              "w", encoding="utf-8") as handle:
        json.dump(card, handle)


def _char_node_id(app, name):
    for nid in list(app.world.graph.nodes):
        node = app.world.graph.get_node(nid)
        if node and node.type == "character" and node.name == name:
            return node.id
    return None


def _carried(app, player_name):
    from player import Player
    node_id = Player.node_id_for(player_name)
    out = []
    for edge in app.world.graph.get_edges_for_target(node_id, "carrying"):
        node = app.world.graph.get_node(edge.source)
        if node:
            out.append(node)
    return out


def test_string_inventory_materializes_full_item_stats(tmp_path):
    """task-519: `inventory: ["<lib_id>"]` preserves every template field."""
    client, app = _fresh(tmp_path)
    _write_char(tmp_path, "StringChar", {
        "name": "String Char",
        "inventory": ["goblin_cleaver"],
    })
    assert client.post("/api/library/import/character/StringChar",
                       json={"active": False}).status_code == 200

    items = _carried(app, "String Char")
    assert len(items) == 1
    props = items[0].properties
    assert props["equip_slots"] == ["hand_right"]
    assert props["damage"] == 7
    assert props["damage_type"] == "slashing"
    assert props["defense"] == 0
    assert props["insulation"] == 0
    assert props["light_level"] == "dim"
    assert props["library_id"] == "goblin_cleaver"
    # triggers survive the character path, not just the place-item path.
    trigger_edges = app.world.graph.get_edges_for_source(items[0].id, EDGE_TRIGGERS)
    assert trigger_edges, "on_examine trigger was dropped on import"


def test_dict_reference_without_properties_uses_template(tmp_path):
    """A dict entry with only node_id + library_id is a template reference."""
    client, app = _fresh(tmp_path)
    _write_char(tmp_path, "DictRef", {
        "name": "Dict Ref",
        "inventory": [{"library_id": "scavenged_plate", "node_id": "item_dictref_plate"}],
    })
    assert client.post("/api/library/import/character/DictRef",
                       json={"active": False}).status_code == 200
    node = app.world.graph.get_node("item_dictref_plate")
    assert node is not None
    assert node.properties["defense"] == 3
    assert node.properties["equip_slots"] == ["torso"]


def test_equipped_may_reference_a_library_id(tmp_path):
    """task-519: an equipped entry can name a library item and lands on a slot."""
    client, app = _fresh(tmp_path)
    _write_char(tmp_path, "Wearer", {
        "name": "Wearer",
        "inventory": ["goblin_cleaver"],
        "equipped": {"hand_right": ["goblin_cleaver"]},
    })
    assert client.post("/api/library/import/character/Wearer",
                       json={"active": False}).status_code == 200
    player = app.world.player_manager.players["Wearer"]
    assert len(player.equipped["hand_right"]) == 1
    item_id = player.equipped["hand_right"][0]
    assert isinstance(item_id, str)
    assert app.world.graph.get_node(item_id) is not None


def test_equipped_may_reference_an_inventory_node_id(tmp_path):
    """The legacy shape standalone_test.json uses must round-trip, not vanish."""
    client, app = _fresh(tmp_path)
    _write_char(tmp_path, "NodeRef", {
        "name": "Node Ref",
        "inventory": [{
            "name": "Scavenged Plate",
            "node_id": "item_noderef_plate",
            "library_id": "scavenged_plate",
        }],
        "equipped": {"torso": ["item_noderef_plate"]},
    })
    assert client.post("/api/library/import/character/NodeRef",
                       json={"active": False}).status_code == 200
    player = app.world.player_manager.players["Node Ref"]
    assert player.equipped["torso"] == ["item_noderef_plate"]


def test_refresh_with_dict_equipped_does_not_crash_state(tmp_path):
    """bug-516 regression: a template whose equipped holds dicts is refreshed,
    then GET /api/state returns 200 and the slot holds a node-id string."""
    client, app = _fresh(tmp_path)
    _write_char(tmp_path, "Victim", {
        "name": "Victim",
        "inventory": [{
            "name": "Scavenged Plate",
            "node_id": "item_victim_plate",
            "library_id": "scavenged_plate",
        }],
        "equipped": {"torso": [{"name": "Scavenged Plate", "node_id": "item_victim_plate"}]},
    })
    assert client.post("/api/library/import/character/Victim",
                       json={"active": True}).status_code == 200
    node_id = _char_node_id(app, "Victim")
    assert node_id

    resp = client.post("/api/library/refresh-to-world",
                       json={"node_id": node_id, "template_id": "Victim"})
    assert resp.status_code == 200, resp.get_data(as_text=True)

    player = app.world.player_manager.players["Victim"]
    assert player.equipped["torso"] == ["item_victim_plate"]

    state = client.get("/api/state")
    assert state.status_code == 200, state.get_data(as_text=True)


def test_refresh_is_idempotent_for_inventory(tmp_path):
    """Refreshing twice must not duplicate carried items."""
    client, app = _fresh(tmp_path)
    _write_char(tmp_path, "Twice", {
        "name": "Twice",
        "inventory": ["goblin_cleaver", "scavenged_plate"],
    })
    client.post("/api/library/import/character/Twice", json={"active": False})
    node_id = _char_node_id(app, "Twice")
    for _ in range(2):
        resp = client.post("/api/library/refresh-to-world",
                           json={"node_id": node_id, "template_id": "Twice"})
        assert resp.status_code == 200, resp.get_data(as_text=True)
    assert len(_carried(app, "Twice")) == 2
