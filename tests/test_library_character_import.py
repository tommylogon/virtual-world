"""Tests for the character library import route (routes/library_routes.py).

Regression: importing a character 500'd with TypeError because add_edge was
called with keyword args (source=.../target=.../type=...) while the signature
takes a single Edge object — the browser then failed JSON.parse on the HTML
error page. Also covers the full canonical round-trip (tags/conditions/
equipped/inventory survive save → import).

All registry writes go to a per-test TEMP data dir so the real data/library
files are never touched.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app

TEST_ITEM_PROPS = {'damage': '1d6', 'description': 'A test sword.', 'name': 'test_sword'}


def _fresh_app(tmp_path):
    data_dir = str(tmp_path)
    os.makedirs(os.path.join(data_dir, 'library', 'items'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'library', 'characters'), exist_ok=True)
    # seed a library item so the string-inventory path has something to resolve
    from routes.helpers import save_registry
    save_registry(data_dir, 'items.json', {'test_sword': dict(TEST_ITEM_PROPS)})
    app = create_app({'TESTING': True, 'DATA_DIR': data_dir})
    return app.test_client(), app, data_dir


CANONICAL_CARD = {
    'name': 'Lib Test Char',
    'personality': 'test personality',
    'description': 'A test character.',
    'base_description': 'baseline look',
    'unknown_name': 'the stranger',
    'stats': {'STR': 12, 'DEX': 10, 'CON': 10, 'INT': 10, 'WIS': 10, 'CHA': 10},
    'vitals': {'HP': 70, 'Max_HP': 100, 'Energy': 50, 'Hunger': 40},
    'decay_rates': {'Hunger': 2},
    'skills': {'Athletics': 3},
    'traits': {'hostile': True},
    'tags': ['vampire', 'faction:guard'],
    'interest_tags': ['magic'],
    'state': 'awake',
    'conditions': {'poisoned': [{'duration': 5, 'source': 'test', 'level': 1}]},
    'equipped': {'head': ['__test__']},
    'current_area': None,
    'inventory': [{'name': 'test_sword', 'library_id': 'test_sword', 'node_id': None,
                   'properties': dict(TEST_ITEM_PROPS)}],
    'memories': [],
    'relationships': {},
    'simple_npc': False,
}


def test_import_character_round_trip_full_data(tmp_path):
    """Importing a canonical card preserves conditions/tags/equipped/inventory."""
    client, app, data_dir = _fresh_app(tmp_path)

    r = client.post('/api/library/characters', json={'id': 'LibTestChar', 'data': CANONICAL_CARD})
    assert r.status_code == 200, r.get_data(as_text=True)

    r = client.post('/api/library/import/character/LibTestChar', json={'active': True})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()['player'] == 'Lib Test Char'

    p = app.world.player_manager.players.get('Lib Test Char')
    assert p.tags == ['vampire', 'faction:guard']
    assert p.interest_tags == ['magic']
    assert p.traits.get('hostile') is True
    assert p.has_condition('poisoned')
    assert p.conditions['poisoned'][0]['duration'] == 5
    assert p.equipped.get('head') == ['__test__']
    assert p.vitals['HP'] == 70
    assert p.decay_rates.get('Hunger') == 2

    inv = []
    for e in app.world.graph.get_edges_for_target('player_Lib_Test_Char', 'carrying'):
        n = app.world.graph.get_node(e.source)
        if n:
            inv.append(n.name)
    assert 'test_sword' in inv


def test_import_character_accepts_legacy_string_inventory(tmp_path):
    """Legacy string inventory entries (bare library ids) still import."""
    client, app, data_dir = _fresh_app(tmp_path)
    legacy = dict(CANONICAL_CARD)
    legacy['name'] = 'Legacy Char'
    legacy['inventory'] = ['test_sword']
    r = client.post('/api/library/characters', json={'id': 'LegacyChar', 'data': legacy})
    assert r.status_code == 200, r.get_data(as_text=True)

    r2 = client.post('/api/library/import/character/LegacyChar', json={'active': False})
    assert r2.status_code == 200, r2.get_data(as_text=True)

    p = app.world.player_manager.players.get('Legacy Char')
    assert p is not None
    inv = []
    for e in app.world.graph.get_edges_for_target('player_Legacy_Char', 'carrying'):
        n = app.world.graph.get_node(e.source)
        if n:
            inv.append(n.name)
    assert 'test_sword' in inv


def test_import_character_missing_404(tmp_path):
    client, app, data_dir = _fresh_app(tmp_path)
    r = client.post('/api/library/import/character/NopeNotThere', json={'active': True})
    assert r.status_code == 404


def test_save_registry_never_deletes_unlisted_entries(tmp_path):
    """Regression: save_registry used to delete any file whose key wasn't in
    the passed dict — a partial save (e.g. a test or a single-entry update)
    silently wiped the whole registry. It must only write, never delete."""
    from routes.helpers import save_registry, load_registry
    data_dir = str(tmp_path)

    save_registry(data_dir, 'items.json', {'apple': {'name': 'Apple'}, 'torch': {'name': 'Torch'}})
    # Partial save — only apple. torch must SURVIVE.
    save_registry(data_dir, 'items.json', {'apple': {'name': 'Apple v2'}})

    reg = load_registry(data_dir, 'items.json')
    assert set(reg.keys()) == {'apple', 'torch'}
    assert reg['apple']['name'] == 'Apple v2'


def test_delete_registry_entry_removes_only_that_file(tmp_path):
    from routes.helpers import save_registry, load_registry, delete_registry_entry
    data_dir = str(tmp_path)

    save_registry(data_dir, 'items.json', {'apple': {'name': 'Apple'}, 'torch': {'name': 'Torch'}})
    delete_registry_entry(data_dir, 'items.json', 'apple')

    reg = load_registry(data_dir, 'items.json')
    assert set(reg.keys()) == {'torch'}


def _import_card(client, app, card_id, card):
    """Seed a library card and import it. Returns the imported Player."""
    r = client.post('/api/library/characters', json={'id': card_id, 'data': card})
    assert r.status_code == 200, r.get_data(as_text=True)
    r = client.post(f'/api/library/import/character/{card_id}', json={'active': False})
    assert r.status_code == 200, r.get_data(as_text=True)
    return app.world.player_manager.players.get(card['name'])


def test_import_character_restores_size_species_and_persona(tmp_path):
    """task-874: size (task-605), species (task-549) and the Persona block (the
    node property `properties.appearance`) were set by neither the card nor this
    import, so a library round-trip silently reset the character. Assert each is
    read, not just present in the seeded file."""
    client, app, data_dir = _fresh_app(tmp_path)
    card = dict(CANONICAL_CARD)
    card['name'] = 'Sized Char'
    card['size'] = 'huge'
    card['species'] = 'troll'
    card['appearance'] = {'identity': {'pronouns': 'they/them'},
                          'appearance': {'height_cm': 240}}

    p = _import_card(client, app, 'SizedChar', card)
    assert p is not None
    assert p.size == 'huge'
    assert p.species == 'troll'

    node = app.world.graph.get_node('player_Sized_Char')
    assert node is not None, "the import placed no character node"
    assert node.properties['appearance'] == card['appearance']


def test_import_character_unknown_size_becomes_none(tmp_path):
    """An unrecognised size must not be stored: None is what lets the engine
    fall back to a hand-authored `size_*` trait (engine/size.py)."""
    client, app, data_dir = _fresh_app(tmp_path)
    card = dict(CANONICAL_CARD)
    card['name'] = 'Bogus Size'
    card['size'] = 'enormous'

    p = _import_card(client, app, 'BogusSize', card)
    assert p is not None
    assert p.size is None
