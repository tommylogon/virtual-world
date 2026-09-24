"""Tests for the save/load system: metadata, slots, autosave slot, rename,
safe filenames, and the app version stamp."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app import create_app
from routes.helpers import _save_game, save_autosave, sanitize_filename, unique_filename
from routes.saveload import _safe_save_path


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


class TestDeleteAllSaves:
    """bug-42: Delete All keeps the autosave slot and is one request."""

    @staticmethod
    def _write(name, autosave=False):
        path = os.path.join(_saves_dir(), name)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'_save_metadata': {'name': name, 'autosave': autosave}}, f)
        return path

    def test_delete_all_keeps_the_autosave_slot(self, app, client):
        auto = self._write('autosave.json', autosave=True)
        one = self._write('run_one_20260101_120000.json')
        two = self._write('run_two_20260102_120000.json')

        body = client.post('/api/save-games/delete-all', json={}).get_json()

        assert os.path.exists(auto)
        assert not os.path.exists(one) and not os.path.exists(two)
        assert body['kept'] == ['autosave.json']
        assert sorted(body['deleted']) == [
            'run_one_20260101_120000.json', 'run_two_20260102_120000.json']

    def test_delete_all_can_include_the_autosave_when_asked(self, app, client):
        auto = self._write('autosave.json', autosave=True)
        body = client.post('/api/save-games/delete-all',
                           json={'include_autosave': True}).get_json()
        assert not os.path.exists(auto)
        assert 'autosave.json' in body['deleted']
        assert body['kept'] == []

    def test_delete_all_ignores_non_json_files(self, app, client):
        note = os.path.join(_saves_dir(), 'notes.txt')
        with open(note, 'w', encoding='utf-8') as f:
            f.write('keep me')
        body = client.post('/api/save-games/delete-all', json={}).get_json()
        assert os.path.exists(note)
        assert body['deleted'] == []

    def test_delete_all_with_no_saves_is_a_noop(self, app, client):
        resp = client.post('/api/save-games/delete-all', json={})
        assert resp.status_code == 200
        assert resp.get_json()['deleted'] == []


class TestLoadGameAdoption:
    """bug-41: a loaded savegame must not inherit the previously open scenario.

    Otherwise a later Commit writes the loaded runtime state into the stale
    scenario's file and destroys its authored content.
    """

    def test_load_game_clears_the_stale_scenario_source(self, app, client):
        world = _world(app)
        world._scenario_source = '/some/stale/scenario.json'
        filename = _save_game(world, "bug41 source")
        resp = client.post(f'/api/load-game/{filename}')
        assert resp.status_code == 200
        assert world._scenario_source is None

    def test_load_game_names_the_world_from_the_payload(self, app, client):
        world = _world(app)
        world._scenario_name = 'Bug41 Camp'
        filename = _save_game(world, "bug41 name")
        # A different, previously open scenario must not leak its name in.
        world._scenario_name = 'Stale Scenario'
        world._scenario_source = '/some/stale/scenario.json'
        client.post(f'/api/load-game/{filename}')
        assert world._scenario_name == 'Bug41 Camp'
        assert world._scenario_source is None

    def test_load_game_syncs_the_commit_sequence(self, app, client):
        world = _world(app)
        filename = _save_game(world, "bug41 seq")
        world._edit_seq = 7
        world._commit_seq = 0
        client.post(f'/api/load-game/{filename}')
        assert world._commit_seq == getattr(world, '_edit_seq', 0)

    def test_api_load_savegame_payload_clears_the_source(self, app, client):
        world = _world(app)
        world._scenario_source = '/some/stale/scenario.json'
        payload = world.to_dict()
        payload['_save_metadata'] = {'name': 'a savegame'}
        payload['_scenario_name'] = 'Loaded World'
        resp = client.post('/api/load', json=payload)
        assert resp.status_code == 200
        assert world._scenario_source is None
        assert world._scenario_name == 'Loaded World'

    def test_adopt_loaded_world_refreshes_the_autosave(self, app, monkeypatch):
        import routes.saveload as saveload
        calls = []
        monkeypatch.setattr(saveload, 'save_autosave', lambda w: calls.append(w))
        monkeypatch.setitem(app.config, 'TESTING', False)

        saveload._adopt_loaded_world(app, {'_scenario_name': 'X'})
        assert calls == [app.world]

        saveload._adopt_loaded_world(app, {'_scenario_name': 'X'}, autosave=False)
        assert calls == [app.world], "ephemeral loads must not write the autosave"


class TestSanitizeFilename:
    """bug-43: filename generation must keep Unicode letters, fold only what is
    genuinely unsafe, and never hand back an empty/Windows-reserved stem."""

    def test_keeps_unicode_letters(self):
        assert sanitize_filename('Ærø kysten') == 'Ærø kysten'
        assert sanitize_filename('Draghál') == 'Draghál'

    def test_composes_combining_marks_instead_of_peeling_them(self):
        # 'e' + COMBINING ACUTE ACCENT normalises to 'é', it does not become 'e_'
        assert sanitize_filename('e\u0301') == 'é'

    def test_folds_unsafe_and_control_characters(self):
        assert sanitize_filename('a<b>c:d/e\\f|g?h*i') == 'a_b_c_d_e_f_g_h_i'
        assert sanitize_filename('bell\x07name') == 'bell_name'

    def test_strips_windows_hostile_trailing_dots_and_spaces(self):
        # Dots are only kept for scenario names; there a trailing "..." would be
        # silently dropped by Windows, so it is trimmed instead.
        assert sanitize_filename('report... ', allow='.()') == 'report'
        assert sanitize_filename('report ') == 'report'

    def test_escapes_reserved_windows_stems(self):
        assert sanitize_filename('CON') == '_CON'
        assert sanitize_filename('com1') == '_com1'
        assert sanitize_filename('console') == 'console'  # not reserved

    def test_falls_back_only_when_nothing_survives(self):
        assert sanitize_filename('', fallback='save') == 'save'
        assert sanitize_filename('   ', fallback='save') == 'save'

    def test_scenario_names_may_keep_dots_and_parens(self):
        assert sanitize_filename('Act I. (draft)', allow='.()') == 'Act I. (draft)'


class TestSaveFilenameCollisions:
    """bug-43: a second save in the same second must not clobber the first."""

    def _freeze_clock(self, monkeypatch):
        import routes.helpers as helpers
        monkeypatch.setattr(helpers.time, 'strftime', lambda fmt: '20260101_120000')

    def test_same_second_saves_produce_two_files(self, app, monkeypatch):
        self._freeze_clock(monkeypatch)
        world = _world(app)

        world.time_ticks = 1
        first = _save_game(world, "same name")
        world.time_ticks = 2
        second = _save_game(world, "same name")

        assert first == 'same name_20260101_120000.json'
        assert second == 'same name_20260101_120000_2.json'
        for filename, tick in ((first, 1), (second, 2)):
            with open(os.path.join(_saves_dir(), filename), 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            assert data['_save_metadata']['tick'] == tick
            # Collisions rename the file only — the display name is untouched.
            assert data['_save_metadata']['name'] == 'same name'

    def test_third_collision_keeps_counting(self, app, monkeypatch):
        self._freeze_clock(monkeypatch)
        world = _world(app)
        names = [_save_game(world, "many") for _ in range(3)]
        assert names == [
            'many_20260101_120000.json',
            'many_20260101_120000_2.json',
            'many_20260101_120000_3.json',
        ]
        assert len(os.listdir(_saves_dir())) == 3

    def test_unicode_save_keeps_letters_and_loads(self, app):
        world = _world(app)
        filename = _save_game(world, "Draghál")
        assert filename.startswith('Draghál_')
        assert '___' not in filename
        with open(os.path.join(_saves_dir(), filename), 'r', encoding='utf-8-sig') as f:
            assert json.load(f)['_save_metadata']['name'] == 'Draghál'

    def test_unique_filename_skips_taken_suffixes(self, tmp_path):
        (tmp_path / 'a.json').write_text('{}', encoding='utf-8')
        (tmp_path / 'a_2.json').write_text('{}', encoding='utf-8')
        assert unique_filename(str(tmp_path), 'a.json') == 'a_3.json'
        assert unique_filename(str(tmp_path), 'fresh.json') == 'fresh.json'


class TestSafeSavePath:
    """Traversal/extension validation is unchanged by the unicode work."""

    def test_rejects_traversal_and_foreign_extensions(self, tmp_path):
        assert _safe_save_path(str(tmp_path), '../escape.json') is None
        assert _safe_save_path(str(tmp_path), 'sub/evil.json') is None
        assert _safe_save_path(str(tmp_path), 'no_ext') is None
        assert _safe_save_path(str(tmp_path), '') is None

    def test_allows_a_unicode_filename(self, tmp_path):
        expected = os.path.join(str(tmp_path), 'Draghál_20260101_120000.json')
        assert _safe_save_path(str(tmp_path), 'Draghál_20260101_120000.json') == expected

