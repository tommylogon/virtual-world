"""Tests for the save/load system: metadata, slots, autosave slot, rename,
safe filenames, and the app version stamp."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app import create_app
from routes.helpers import _save_game, save_autosave


@pytest.fixture
def app(tmp_path, monkeypatch):
    """An app instance whose saves dir is a temp dir (never touches real saves)."""
    import routes.helpers as helpers
    import routes.saveload as saveload
    saves_dir = tmp_path / 'saves'
    saves_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(helpers, 'SAVES_DIR', str(saves_dir))
    monkeypatch.setattr(saveload, 'SAVES_DIR', str(saves_dir))
    application = create_app({'TESTING': True})
    return application


def _saves_dir():
    import routes.helpers as helpers
    return helpers.SAVES_DIR


def _world(app):
    return app.world


@pytest.fixture
def client(app):
    return app.test_client()


class TestSaveGame:
    def test_save_creates_timestamped_file_with_metadata(self, app):
        world = _world(app)
        active = next(iter(world.player_manager.players))
        world.player_manager.active_player = active
        world.time_ticks = 42
        world.turn_number = 7

        filename = _save_game(world, "my run")
        assert filename and filename.endswith('.json')
        path = os.path.join(_saves_dir(), filename)
        assert os.path.exists(path)
        with open(path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        meta = data['_save_metadata']
        assert meta['name'] == 'my run'
        assert meta['tick'] == 42
        assert meta['turn'] == 7
        assert meta['player'] == active
        assert meta['version']  # app version stamped
        assert meta['autosave'] is False
        assert 'players' in data and 'areas' in data  # stats available

    def test_save_to_slot_overwrites_in_place(self, app):
        world = _world(app)
        world.time_ticks = 1
        first = _save_game(world, "slot one")
        assert first.endswith('.json')

        world.time_ticks = 99
        second = _save_game(world, None, slot=first)
        assert second == first  # same file, overwritten
        with open(os.path.join(_saves_dir(), first), 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        assert data['_save_metadata']['tick'] == 99
        # No new-name supplied → existing label preserved
        assert data['_save_metadata']['name'] == 'slot one'

    def test_save_to_slot_rejects_bad_names(self, app):
        world = _world(app)
        assert _save_game(world, None, slot="../escape.json") is None
        assert _save_game(world, None, slot="x.yaml") is None
        # Nothing escaped the saves dir
        for fname in os.listdir(os.path.dirname(_saves_dir())):
            assert 'escape' not in fname


class TestAutosaveSlot:
    def test_autosave_writes_boot_file_and_modal_slot(self, tmp_path, monkeypatch):
        import routes.helpers as helpers
        boot = tmp_path / 'boot_autosave.json'
        saves = tmp_path / 'saves_autosave'
        saves.mkdir(exist_ok=True)
        slot = saves / 'autosave.json'
        monkeypatch.setattr(helpers, 'AUTOSAVE_PATH', str(boot))
        monkeypatch.setattr(helpers, 'SAVES_DIR', str(saves))
        monkeypatch.setattr(helpers, 'AUTOSAVE_SLOT', str(slot))

        world = create_app({'TESTING': True}).world
        world.time_ticks = 5
        world.turn_number = 2

        save_autosave(world)

        assert boot.exists()  # boot restore file unchanged behavior
        with open(boot, 'r', encoding='utf-8-sig') as f:
            boot_data = json.load(f)
        assert '_autosave_meta' in boot_data
        assert '_save_metadata' not in boot_data  # boot file keeps only its meta

        assert slot.exists()  # modal slot written
        with open(slot, 'r', encoding='utf-8-sig') as f:
            slot_data = json.load(f)
        meta = slot_data['_save_metadata']
        assert meta['autosave'] is True
        assert meta['name'] == 'Autosave'
        assert meta['tick'] == 5
        assert meta['turn'] == 2
        assert meta['version']
        assert '_autosave_meta' not in slot_data


class TestSaveRoutes:
    def test_list_returns_stats_and_autosave_first(self, app, client, tmp_path):
        world = _world(app)
        world.time_ticks = 3
        _save_game(world, "manual one")

        # Autosave slot in the same saves dir
        slot_path = os.path.join(_saves_dir(), 'autosave.json')
        with open(slot_path, 'w', encoding='utf-8') as f:
            json.dump({
                'players': [{'name': 'X'}], 'areas': {},
                '_save_metadata': {
                    'name': 'Autosave', 'tick': 10, 'turn': 4,
                    'player': 'X', 'version': '1.0.0', 'autosave': True,
                    'timestamp': '20990101_000000',
                },
            }, f)

        resp = client.get('/api/save-games')
        assert resp.status_code == 200
        saves = resp.get_json()
        assert saves and saves[0]['autosave'] is True  # pinned top
        assert saves[0]['name'] == 'Autosave'
        assert saves[0]['players'] == 1
        assert any(s['filename'].startswith('manual one') and s['version'] for s in saves)

    def test_rename_updates_label_and_file(self, app, client):
        world = _world(app)
        filename = _save_game(world, "old name")
        resp = client.post(f'/api/save-game/{filename}/rename', json={'name': 'new cool name'})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['status'] == 'success'
        assert body['filename'].startswith('new cool name_')
        with open(os.path.join(_saves_dir(), body['filename']), 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        assert data['_save_metadata']['name'] == 'new cool name'
        assert not os.path.exists(os.path.join(_saves_dir(), filename))  # old gone

    def test_rename_rejects_empty_name(self, app, client):
        world = _world(app)
        filename = _save_game(world, "keep me")
        resp = client.post(f'/api/save-game/{filename}/rename', json={'name': '   '})
        assert resp.status_code == 400

    def test_load_and_delete_use_safe_paths(self, app, client):
        resp = client.post('/api/load-game/..%2F..%2Fsecret')
        assert resp.status_code == 404
        resp = client.delete('/api/save-game/..%2F..%2Fsecret')
        assert resp.status_code == 404

    def test_load_roundtrip(self, app, client):
        world = _world(app)
        world.time_ticks = 13
        filename = _save_game(world, "roundtrip")
        resp = client.post(f'/api/load-game/{filename}')
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'success'
        assert world.time_ticks == 13

    def test_save_via_api_new_and_slot(self, app, client):
        resp = client.post('/api/save-game', json={'name': 'api save'})
        assert resp.status_code == 201
        filename = resp.get_json()['filename']
        # Overwrite same slot via API
        world = _world(app)
        world.time_ticks = 21
        resp2 = client.post('/api/save-game', json={'slot': filename})
        assert resp2.status_code == 201
        assert resp2.get_json()['filename'] == filename
