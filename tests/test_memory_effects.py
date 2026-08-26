"""Tests for memory trigger effects and Player memory helpers (task-198)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import WorldGraph
from engine.effects import Effects
from engine.logging_events import GameLogger
from player import Player


# ─────────────────── Fixtures ───────────────────


@pytest.fixture
def graph():
    return WorldGraph()


@pytest.fixture
def logging_events():
    return GameLogger()


@pytest.fixture
def effects(graph, logging_events):
    return Effects(graph, logging_events)


@pytest.fixture
def hero():
    p = Player("Hero")
    p.vitals["HP"] = 50
    return p


def _make_game_state(player, extra_players=None):
    game_state = type("FakeGameState", (), {})()
    game_state.player = player
    game_state.players = extra_players or {player.name: player}
    game_state.get_players_in_area = lambda area_name=None, exclude_self=True: []
    return game_state


# ─────────────────── Player memory helpers ───────────────────


class TestPlayerMemoryHelpers:
    def test_add_memory_default_fields(self, hero):
        hero.add_memory("Found a key.", 10, importance=6, memory_type="action")
        assert len(hero.memories) == 1
        m = hero.memories[0]
        assert m["text"] == "Found a key."
        assert m["tick"] == 10
        assert m["importance"] == 6
        assert m["type"] == "action"
        assert m["id"]
        assert m["tags"] == []
        assert m["source"] == "auto"
        assert m["salience_override"] == 0
        assert m["suppressions"] == []

    def test_add_memory_with_tags_and_source(self, hero):
        hero.add_memory("Saw a ghost.", 5, tags=["haunted", "night"], source="manual")
        m = hero.memories[0]
        assert m["tags"] == ["haunted", "night"]
        assert m["source"] == "manual"

    def test_suppress_by_tags(self, hero):
        hero.add_memory("A", 1, tags=["x"], importance=5)
        hero.add_memory("B", 2, tags=["y"], importance=5)
        hero.add_memory("C", 3, tags=["x", "y"], importance=5)
        suppressed = hero.suppress_memory(tags=["x"], duration=3)
        assert set(suppressed) == {hero.memories[0]["id"], hero.memories[2]["id"]}
        assert len(hero.memories[1]["suppressions"]) == 0

    def test_suppress_by_keyword(self, hero):
        hero.add_memory("The candle flickers.", 1)
        hero.add_memory("A cold wind blows.", 2)
        suppressed = hero.suppress_memory(keywords="candle", duration=1)
        assert len(suppressed) == 1
        assert hero.memories[0]["suppressions"][0]["until_tick"] == 1

    def test_suppress_duration_zero_is_permanent(self, hero):
        hero.add_memory("Secret.", 1)
        hero.suppress_memory(keywords="Secret", duration=0)
        assert hero.memories[0]["suppressions"][0]["until_tick"] is None

    def test_unblock_removes_suppression(self, hero):
        hero.add_memory("Hidden.", 1)
        hero.suppress_memory(keywords="Hidden", duration=5, scope="self")
        assert len(hero.memories[0]["suppressions"]) == 1
        hero.unblock_memory(keywords="Hidden", scope="self")
        assert hero.memories[0]["suppressions"] == []

    def test_unblock_noop_when_no_suppression(self, hero):
        hero.add_memory("Free.", 1)
        result = hero.unblock_memory(keywords="Free")
        assert result == []

    def test_clear_expired_suppressions(self, hero):
        hero.add_memory("Old.", 1)
        hero.add_memory("New.", 2)
        hero.memories[0]["suppressions"] = [{"until_tick": 5, "source": "self"}]
        hero.memories[1]["suppressions"] = [{"until_tick": 99, "source": "self"}]
        hero.clear_expired_suppressions(current_tick=10)
        assert hero.memories[0]["suppressions"] == []
        assert len(hero.memories[1]["suppressions"]) == 1

    def test_reset_turn_state_clears_salience_and_expired(self, hero):
        hero.add_memory("Recall me.", 1)
        hero.memories[0]["salience_override"] = 7
        hero.memories[0]["suppressions"] = [{"until_tick": 2, "source": "self"}]
        hero.reset_turn_state(current_tick=5)
        assert hero.memories[0]["salience_override"] == 0
        assert hero.memories[0]["suppressions"] == []

    def test_get_relevant_memories_excludes_suppressed(self, hero):
        hero.add_memory("Visible fact.", 1, tags=["fact"])
        hero.add_memory("Hidden truth.", 2, tags=["secret"])
        hero.suppress_memory(tags=["secret"], duration=1)
        results = hero.get_relevant_memories("truth", max_results=5)
        assert all(m["text"] == "Visible fact." for m in results)

    def test_get_relevant_memories_respects_salience_override(self, hero):
        hero.add_memory("Fade.", 1, importance=3)
        hero.add_memory("Boom.", 2, importance=3)
        hero.memories[1]["salience_override"] = 10
        results = hero.get_relevant_memories("fade", max_results=5)
        assert results[0]["text"] == "Boom."

    def test_get_relevant_memories_reinforces_on_recall(self, hero):
        hero.add_memory("Stable.", 1, importance=5)
        hero.get_relevant_memories("stable", max_results=5)
        assert hero.memories[0]["importance"] == 6

    def test_get_relevant_memories_reinforce_caps_at_10(self, hero):
        hero.add_memory("Maxed.", 1, importance=10)
        for _ in range(5):
            hero.get_relevant_memories("maxed", max_results=5)
        assert hero.memories[0]["importance"] == 10


# ─────────────────── surface_memory effect ───────────────────


class TestSurfaceMemoryEffect:
    def test_surface_by_tag_sets_salience(self, effects, hero):
        hero.add_memory("A hidden key.", 1, tags=["key"])
        gs = _make_game_state(hero)
        out = effects.handle_surface_memory(
            {"tags": ["key"], "salience_boost": 5},
            {}, game_state=gs,
        )
        assert hero.memories[0]["salience_override"] == 5

    def test_surface_by_keyword(self, effects, hero):
        hero.add_memory("The door is locked.", 1)
        gs = _make_game_state(hero)
        out = effects.handle_surface_memory(
            {"keywords": "locked", "salience_boost": 3},
            {}, game_state=gs,
        )
        assert hero.memories[0]["salience_override"] == 3

    def test_surface_emits_message_with_memory_text(self, effects, hero):
        hero.add_memory("A flash of light.", 1, tags=["vision"])
        gs = _make_game_state(hero)
        out = effects.handle_surface_memory(
            {"tags": ["vision"], "message": "You remember: {memory}"},
            {}, game_state=gs,
        )
        assert any("flash of light" in line for line in out)

    def test_surface_no_match_returns_noop(self, effects, hero):
        hero.add_memory("Nothing here.", 1)
        gs = _make_game_state(hero)
        out = effects.handle_surface_memory({"tags": ["nope"]}, {}, game_state=gs)
        assert out == []

    def test_surface_specific_target_player(self, effects, hero):
        other = Player("Other")
        other.add_memory("Other secret.", 1, tags=["secret"])
        gs = _make_game_state(hero, {"Hero": hero, "Other": other})
        out = effects.handle_surface_memory(
            {"target": "Other", "tags": ["secret"]},
            {}, game_state=gs,
        )
        assert other.memories[0]["salience_override"] == 3
        assert hero.memories == []


# ─────────────────── suppress_memory effect ───────────────────


class TestSuppressMemoryEffect:
    def test_suppress_adds_suppression(self, effects, hero):
        hero.add_memory("Forgettable.", 1, tags=["minor"])
        gs = _make_game_state(hero)
        out = effects.handle_suppress_memory(
            {"tags": ["minor"], "duration": 2, "scope": "self"},
            {}, game_state=gs,
        )
        assert hero.memories[0]["suppressions"][0]["until_tick"] == 2

    def test_suppress_no_match_no_output(self, effects, hero):
        hero.add_memory("Important.", 1)
        gs = _make_game_state(hero)
        out = effects.handle_suppress_memory(
            {"tags": ["nothing"], "message": "Should not appear"},
            {}, game_state=gs,
        )
        assert out == []


# ─────────────────── unblock_memory effect ───────────────────


class TestUnblockMemoryEffect:
    def test_unblock_removes_suppression(self, effects, hero):
        hero.add_memory("Blocked.", 1)
        hero.suppress_memory(keywords="Blocked", duration=5)
        gs = _make_game_state(hero)
        out = effects.handle_unblock_memory(
            {"keywords": "Blocked", "scope": "self"},
            {}, game_state=gs,
        )
        assert hero.memories[0]["suppressions"] == []

    def test_unblock_noop_when_nothing_to_unblock(self, effects, hero):
        hero.add_memory("Free.", 1)
        gs = _make_game_state(hero)
        out = effects.handle_unblock_memory(
            {"keywords": "Free", "message": "Noop"},
            {}, game_state=gs,
        )
        assert out == []


# ─────────────────── API round-trips ───────────────────


class TestMemoryApiRoundTrips:
    def test_suppress_api(self):
        from app import create_app
        app = create_app({'TESTING': True})
        client = app.test_client()
        name = self._active_player(client)
        client.post(f'/api/players/{name}/memories/clear')
        client.post(f'/api/players/{name}/memories/entry', json={
            'text': 'API test memory.', 'tags': ['api'], 'tick': 1,
        })
        resp = client.post(f'/api/players/{name}/memories/suppress', json={
            'tags': ['api'], 'duration': 2,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['suppressed']) == 1

    def test_unblock_api(self):
        from app import create_app
        app = create_app({'TESTING': True})
        client = app.test_client()
        name = self._active_player(client)
        client.post(f'/api/players/{name}/memories/clear')
        client.post(f'/api/players/{name}/memories/entry', json={
            'text': 'Block me.', 'tags': ['blockme'], 'tick': 1,
        })
        client.post(f'/api/players/{name}/memories/suppress', json={
            'tags': ['blockme'], 'duration': 5,
        })
        resp = client.post(f'/api/players/{name}/memories/unblock', json={
            'tags': ['blockme'],
        })
        assert resp.status_code == 200
        mems = client.get(f'/api/players/{name}/memories').get_json()['memories']
        target = [m for m in mems if m['text'] == 'Block me.'][0]
        assert target['suppressions'] == []

    def test_clear_expired_api(self):
        from app import create_app
        app = create_app({'TESTING': True})
        client = app.test_client()
        name = self._active_player(client)
        client.post(f'/api/players/{name}/memories/clear')
        client.post(f'/api/players/{name}/memories/entry', json={
            'text': 'Expire me.', 'tick': 1,
        })
        mems = client.get(f'/api/players/{name}/memories').get_json()['memories']
        target = [m for m in mems if m['text'] == 'Expire me.'][0]
        mem_id = target['id']
        # Inject a stale suppression directly
        target['suppressions'] = [{'until_tick': 5, 'source': 'self'}]
        client.post(f'/api/players/{name}/memories', json={'memories': mems})
        resp = client.post(f'/api/players/{name}/memories/clear-expired', json={'current_tick': 10})
        assert resp.status_code == 200
        mems = client.get(f'/api/players/{name}/memories').get_json()['memories']
        target = [m for m in mems if m['id'] == mem_id][0]
        assert target['suppressions'] == []

    def _active_player(self, client):
        return client.get('/api/state').get_json()['active_player']
