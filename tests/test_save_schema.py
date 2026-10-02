"""task-453: save/scenario schema version gate and migration.

Covers the pure migration helper and both load routes, plus stamping on save.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app import create_app
from version import SCHEMA_VERSION
from engine.schema import (
    SchemaError, schema_version_of, migrate,
)
from routes.helpers import _save_game, save_autosave


@pytest.fixture
def app(tmp_path, monkeypatch):
    import routes.helpers as helpers
    import routes.saveload as saveload
    saves_dir = tmp_path / 'saves'
    saves_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(helpers, 'SAVES_DIR', str(saves_dir))
    monkeypatch.setattr(saveload, 'SAVES_DIR', str(saves_dir))
    # Keep save_autosave off the real data/autosave.json.
    monkeypatch.setattr(helpers, 'AUTOSAVE_PATH', str(tmp_path / 'autosave.json'))
    monkeypatch.setattr(helpers, 'AUTOSAVE_SLOT', str(saves_dir / 'autosave.json'))
    return create_app({'TESTING': True})


def _saves_dir():
    import routes.helpers as helpers
    return helpers.SAVES_DIR


class TestSchemaVersionOf:
    def test_reads_metadata_autosave_meta_and_top_level(self):
        assert schema_version_of({'_save_metadata': {'schema_version': 2}}) == 2
        assert schema_version_of({'_autosave_meta': {'schema_version': 1}}) == 1
        assert schema_version_of({'schema_version': 3}) == 3
        assert schema_version_of({}) is None


class TestMigrate:
    def test_same_version_is_untouched(self):
        data = {'_save_metadata': {'schema_version': SCHEMA_VERSION}, 'players': {}}
        out, from_version = migrate(data)
        assert out is data
        assert from_version == SCHEMA_VERSION

    def test_unstamped_payload_is_current_not_v1(self):
        """The field was introduced with the app; unstamped files use the
        current shape (save_autosave stamped 2 while _save_game did not), so a
        missing version must NOT be assumed v1 and must not invert Bladder."""
        data = {'players': {'P': {'vitals': {'Bladder': 100}}}}
        out, from_version = migrate(data)
        assert from_version == SCHEMA_VERSION
        assert out['players']['P']['vitals']['Bladder'] == 100  # untouched

    def test_explicit_v1_migrates_the_bladder(self):
        data = {'_save_metadata': {'schema_version': 1},
                'players': {'P': {'vitals': {'Bladder': 30}}}}
        out, from_version = migrate(data)
        assert from_version == 1
        assert out['players']['P']['vitals']['Bladder'] == 70
        assert out['_save_metadata']['schema_version'] == SCHEMA_VERSION

    def test_newer_version_is_refused(self):
        data = {'_save_metadata': {'schema_version': SCHEMA_VERSION + 1}, 'players': {}}
        with pytest.raises(SchemaError):
            migrate(data)


class TestStamping:
    def test_named_save_carries_schema_version(self, app):
        world = app.world
        world.player_manager.active_player = next(iter(world.player_manager.players))
        filename = _save_game(world, 'schema test')
        with open(os.path.join(_saves_dir(), filename), encoding='utf-8-sig') as f:
            meta = json.load(f)['_save_metadata']
        assert meta['schema_version'] == SCHEMA_VERSION
        # still distinct from the app build version
        assert 'version' in meta

    def test_autosave_carries_schema_version(self, app):
        import routes.helpers as helpers
        save_autosave(app.world)
        with open(helpers.AUTOSAVE_PATH, encoding='utf-8') as f:
            boot = json.load(f)
        with open(helpers.AUTOSAVE_SLOT, encoding='utf-8') as f:
            slot = json.load(f)
        assert boot['_autosave_meta']['schema_version'] == SCHEMA_VERSION
        assert slot['_save_metadata']['schema_version'] == SCHEMA_VERSION


class TestLoadGate:
    def test_load_refuses_newer_schema(self, app):
        client = app.test_client()
        data = app.world.to_dict()
        data['_save_metadata'] = {'name': 'future', 'schema_version': SCHEMA_VERSION + 1}
        with open(os.path.join(_saves_dir(), 'future.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f)
        resp = client.post('/api/load-game/future.json')
        assert resp.status_code == 400
        assert 'newer' in resp.get_json()['error'].lower()

    def test_load_game_migrates_v1_and_reports(self, app):
        client = app.test_client()
        data = app.world.to_dict()
        data['_save_metadata'] = {'name': 'old', 'schema_version': 1}
        filename = 'old.json'
        with open(os.path.join(_saves_dir(), filename), 'w', encoding='utf-8') as f:
            json.dump(data, f)
        resp = client.post(f'/api/load-game/{filename}')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['status'] == 'success'
        assert 'schema_notice' in body and 'v1' in body['schema_notice']

    def test_ephemeral_load_migrates_explicit_v1_and_reports(self, app):
        client = app.test_client()
        data = app.world.to_dict()
        data['schema_version'] = 1  # explicit old version -> real migration
        resp = client.post('/api/load', data=json.dumps(data),
                           content_type='application/json')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['status'] == 'success'
        assert 'schema_notice' in body and 'v1' in body['schema_notice']

    def test_unstamped_ephemeral_load_has_no_notice(self, app):
        """An unstamped file is current-format: it loads without a false
        'migrated' notice (and without inverting Bladder)."""
        client = app.test_client()
        data = app.world.to_dict()
        resp = client.post('/api/load', data=json.dumps(data),
                           content_type='application/json')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['status'] == 'success'
        assert 'schema_notice' not in body

    def test_ephemeral_load_refuses_newer(self, app):
        client = app.test_client()
        data = app.world.to_dict()
        data['schema_version'] = SCHEMA_VERSION + 1
        resp = client.post('/api/load', data=json.dumps(data),
                           content_type='application/json')
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_same_version_load_has_no_notice(self, app):
        client = app.test_client()
        data = app.world.to_dict()
        data['schema_version'] = SCHEMA_VERSION
        resp = client.post('/api/load', data=json.dumps(data),
                           content_type='application/json')
        assert resp.status_code == 200
        assert 'schema_notice' not in resp.get_json()
