"""Tests for auto-generated inverse item actions.

Toggling ``take`` on an item should also expose ``drop``, and toggling
``equip`` should also expose ``unequip`` — both in the stored node
properties and in the available-actions list the UI renders.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.item_actions import normalize_item_actions, INVERSE_ACTIONS


def test_take_implies_drop():
    assert normalize_item_actions(["examine", "take"]) == ["examine", "take", "drop"]


def test_equip_implies_unequip():
    assert normalize_item_actions(["examine", "equip"]) == ["examine", "equip", "unequip"]


def test_open_implies_close():
    assert normalize_item_actions(["examine", "open"]) == ["examine", "open", "close"]


def test_close_implies_open():
    assert normalize_item_actions(["examine", "close"]) == ["examine", "close", "open"]


def test_existing_inverse_not_duplicated():
    result = normalize_item_actions(["take", "drop"])
    assert result.count("drop") == 1
    assert result.count("take") == 1


def test_string_input_parsed_and_deduped():
    result = normalize_item_actions("examine, take, equip")
    assert sorted(result) == ["drop", "equip", "examine", "take", "unequip"]


def test_inverse_map_is_bidirectional():
    for action, inverse in INVERSE_ACTIONS.items():
        assert INVERSE_ACTIONS[inverse] == action


def test_empty_and_none_inputs():
    assert normalize_item_actions([]) == []
    assert normalize_item_actions("") == []
    assert normalize_item_actions(None) == []


def test_unknown_actions_preserved():
    assert normalize_item_actions(["examine", "break"]) == ["examine", "break"]


def test_update_node_normalizes_actions():
    from app import create_app
    app = create_app({'TESTING': True})
    client = app.test_client()

    resp = client.post('/api/graph/node', json={
        'type': 'item',
        'name': 'Sword',
        'properties': {'actions': ['equip']},
    })
    assert resp.status_code == 200
    node_id = resp.get_json()['id']

    resp = client.patch(f'/api/graph/node/{node_id}', json={
        'properties': {'actions': ['take', 'equip']},
    })
    assert resp.status_code == 200

    node = app.world.graph.get_node(node_id)
    assert node is not None
    assert set(node.properties['actions']) == {'take', 'drop', 'equip', 'unequip'}


def test_build_item_legacy_normalizes_actions():
    from app import create_app
    app = create_app({'TESTING': True})
    client = app.test_client()

    resp = client.post('/api/build/item', json={
        'name': 'Backpack',
        'area': sorted(app.world.areas)[0],
        'actions': 'examine,equip',
    })
    assert resp.status_code == 200

    node_id = next(
        (n.id for n in app.world.graph.nodes.values()
         if n.type == 'item' and n.name == 'Backpack'),
        None
    )
    assert node_id is not None
    node = app.world.graph.get_node(node_id)
    assert 'unequip' in node.properties['actions']


def test_graph_load_normalizes_item_actions():
    """The graph-node load path (used by scenario files) must canonicalize
    action inverses, so a stored `take` without `drop` loads as both."""
    from app import create_app
    app = create_app({'TESTING': True})
    world = app.world

    # Build a bare graph payload with an un-expanded actions list.
    graph_data = {
        "nodes": {
            "item_Key": {
                "id": "item_Key", "type": "item", "name": "Key",
                "properties": {"actions": ["examine", "take", "open"]},
            }
        },
        "edges": [],
    }
    data_payload = {
        "graph": graph_data,
        "areas": {}, "rooms": {}, "players": {}, "ways": {},
        "world_lore": [], "turn_events": [], "game_log": [],
        "time_ticks": 0, "turn_number": 0,
    }
    world.serializer.load_from_dict(data_payload)

    node = world.graph.get_node("item_Key")
    assert node is not None
    actions = set(node.properties["actions"])
    assert {"take", "drop", "open", "close"} <= actions
