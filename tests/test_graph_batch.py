"""NL-editor batch apply (task-387): POST /api/graph/batch is ONE undo snapshot.

Regression: the NL Editor staged Apply used per-op API calls, each of which
pushed its own undo snapshot — a single Undo could never revert a whole
Apply, and several op types hit wrong routes/methods (405) or resolved to
silent no-ops. The batch endpoint replays ops topologically and records one
PRE-state snapshot so one Undo restores the pre-Apply world.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


def _fresh_client():
    app = create_app({'TESTING': True})
    return app.test_client(), app


def test_batch_creates_are_one_undo_snapshot():
    client, app = _fresh_client()
    stack_before = len(app._undo_stack)

    resp = client.post('/api/graph/batch', json={'ops': [
        {'type': 'create_node', 'payload': {'node': {'id': 'area_nl_alpha', 'type': 'area', 'name': 'NL Alpha', 'properties': {'description': 'first'}}}},
        {'type': 'create_node', 'payload': {'node': {'id': 'area_nl_beta', 'type': 'area', 'name': 'NL Beta', 'properties': {'description': 'second'}}}},
    ]})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    assert len(data['applied']) == 2
    assert app.world.graph.get_node('area_nl_alpha') is not None
    assert app.world.graph.get_node('area_nl_beta') is not None

    # Exactly ONE undo entry for the whole batch (a pre-state snapshot).
    labels = [entry[2] for entry in app._undo_stack[stack_before:]]
    assert len(labels) == 1
    assert 'NL editor batch (2 ops)' in labels[0]

    # One Undo removes BOTH nodes.
    resp = client.post('/api/undo')
    assert resp.get_json()['steps'] == 1
    assert app.world.graph.get_node('area_nl_alpha') is None
    assert app.world.graph.get_node('area_nl_beta') is None


def test_batch_partial_reports_failed_ops():
    client, app = _fresh_client()
    resp = client.post('/api/graph/batch', json={'ops': [
        {'type': 'create_node', 'payload': {'node': {'id': 'area_nl_good', 'type': 'area', 'name': 'NL Good'}}},
        {'type': 'create_node', 'payload': {'node': {'id': 'area_nl_bad', 'type': 'area'}}},  # no name
        {'type': 'update_node', 'payload': {'node_id': 'does_not_exist', 'patch': {'description': 'x'}}},
    ]})
    assert resp.status_code == 207
    data = resp.get_json()
    assert data['status'] == 'partial'
    assert len(data['applied']) == 1
    assert len(data['errors']) == 2
    assert data['errors'][0]['index'] == 1
    assert data['errors'][1]['index'] == 2
    assert app.world.graph.get_node('area_nl_good') is not None
    assert app.world.graph.get_node('area_nl_bad') is None


def test_batch_requires_ops_array():
    client, _ = _fresh_client()
    assert client.post('/api/graph/batch', json={'ops': []}).status_code == 400
    assert client.post('/api/graph/batch', json={}).status_code == 400


def test_batch_update_node_flat_patch():
    """NL-editor agents hand a FLAT property map; it must land in properties."""
    client, app = _fresh_client()
    area = next(n for n in app.world.graph.nodes.values() if n.type == 'area')
    resp = client.post('/api/graph/batch', json={'ops': [
        {'type': 'update_node', 'payload': {'node_id': area.id, 'patch': {'description': 'flat patch works'}}},
    ]})
    assert resp.status_code == 200
    assert app.world.graph.get_node(area.id).properties.get('description') == 'flat patch works'


def test_batch_spawn_library_item_relation_and_rename():
    client, app = _fresh_client()
    area_name = sorted(app.world.areas)[0]
    area_node = next(n for n in app.world.graph.nodes.values()
                     if n.type == 'area' and n.name == area_name)
    resp = client.post('/api/graph/batch', json={'ops': [
        {'type': 'spawn_library_item',
         'payload': {'library_id': 'jumpsuit', 'parent_id': area_node.id,
                     'relation': 'on', 'rename': 'Pristine Jumpsuit'}},
    ]})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    node_id = data['applied'][0]['node_id']
    node = app.world.graph.get_node(node_id)
    assert node is not None
    assert node.name == 'Pristine Jumpsuit'
    # placement edge honors the staged relation ('on', not the default 'in');
    # trigger attachments may add extra edges, so assert the placement edge
    # directly rather than the full set.
    place_edges = [(e.source, e.target, e.type) for e in app.world.graph.edges
                   if e.source == node_id and e.target == area_node.id]
    assert place_edges == [(node_id, area_node.id, 'on')]


def test_batch_connect_areas_authors_directions():
    """connect_areas must author direction props so exits actually resolve."""
    client, app = _fresh_client()
    areas = [n for n in app.world.graph.nodes.values() if n.type == 'area'][:2]
    area_a, area_b = areas[0], areas[1]
    resp = client.post('/api/graph/batch', json={'ops': [
        {'type': 'connect_areas',
         'payload': {'way_id': 'way_nl_gate', 'area_a_id': area_a.id,
                     'area_b_id': area_b.id, 'way_name': 'NL Gate',
                     'direction_a': 'east', 'direction_b': 'west'}},
    ]})
    assert resp.status_code == 200
    way = app.world.graph.get_node('way_nl_gate')
    assert way is not None and way.type == 'way'

    def props(src, tgt):
        for e in app.world.graph.edges:
            if e.source == src and e.target == tgt and e.type == 'connection':
                return e.properties
        return None

    assert props(area_a.id, 'way_nl_gate') == {'direction': 'east', 'visible_in_direction': ''}
    assert props('way_nl_gate', area_b.id) == {'direction': 'west'}
    assert props(area_b.id, 'way_nl_gate') == {'direction': 'west', 'visible_in_direction': ''}
    assert props('way_nl_gate', area_a.id) == {'direction': 'east'}
