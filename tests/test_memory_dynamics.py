"""Memory dynamics (task-685): mechanism + wiring tests.

Mechanism tests cover the arithmetic in engine/memory_dynamics.py directly.
Wiring tests prove the HTTP paths actually read/write the dynamics fields on
the live player object — a passing unit test alone does not prove the mechanic
is wired (see AGENTS.md).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import memory_dynamics as md
from player import Player


# ── mechanism: defaults & category ───────────────────────────────────────

def test_ensure_dynamics_defaults_old_saves():
    m = {"id": "a", "text": "old memory", "type": "observation", "source": "auto"}
    md.ensure_dynamics(m)
    assert m["category"] == "episodic"
    assert m["activation"] == 1.0
    assert m["confidence"] == 0.7
    assert m["reinforcements"] == 0
    assert m["reflection_depth"] == 0
    assert m["source_memory_ids"] == []
    assert m["contradicts"] == []


def test_ensure_dynamics_is_idempotent_and_keeps_explicit_values():
    m = {"id": "a", "text": "x", "confidence": 0.42, "category": "belief"}
    md.ensure_dynamics(m)
    md.ensure_dynamics(m)
    assert m["confidence"] == 0.42
    assert m["category"] == "belief"


def test_manual_source_defaults_to_full_confidence():
    m = {"id": "a", "text": "seed", "source": "manual"}
    md.ensure_dynamics(m)
    assert m["confidence"] == 1.0


def test_category_from_type_and_tags():
    assert md.ensure_dynamics({"type": "reflection"})["category"] == "belief"
    assert md.ensure_dynamics({"type": "weird_unknown_type"})["category"] == "episodic"
    assert md.ensure_dynamics({"type": "thought", "tags": ["rel:Anna"]})["category"] == "social"
    # a reflection about a person stays a belief — more specific wins
    assert md.ensure_dynamics({"type": "reflection", "tags": ["rel:Anna"]})["category"] == "belief"
    # pre-dynamics reflections were already first-order conclusions
    assert md.ensure_dynamics({"type": "reflection"})["reflection_depth"] == 1


def test_effective_importance_modulated_by_activation_and_confidence():
    base = {"importance": 10}
    assert md.effective_importance(base) == 10.0  # field-less = unchanged
    faded = md.effective_importance({"importance": 10, "activation": 0.0, "confidence": 1.0})
    doubted = md.effective_importance({"importance": 10, "activation": 1.0, "confidence": 0.0})
    assert faded == 10 * 0.6 * 1.0
    assert doubted == 10 * 1.0 * 0.75


# ── mechanism: reinforcement ─────────────────────────────────────────────

def test_reinforce_is_bounded_and_stamps_tick():
    m = {"id": "a", "text": "x"}
    for _ in range(20):
        md.reinforce(m, tick=55)
    assert m["reinforcements"] == 20
    assert m["activation"] == 1.0  # capped, never > 1
    assert m["confidence"] == 1.0  # capped, never > 1
    assert m["last_recalled_tick"] == 55


# ── mechanism: decay ─────────────────────────────────────────────────────

class _Store:
    def __init__(self, memories):
        self.memories = list(memories)
        self.memory_index = {}


def test_decay_spares_important_emotional_memory_and_removes_plain():
    emotional = {"id": "e", "text": "Father died", "importance": 9, "source": "auto",
                 "memory_emotions": [{"label": "grief", "intensity": 9}]}
    plain = {"id": "p", "text": "Ate bread", "importance": 3, "source": "auto"}
    store = _Store([emotional, plain])
    removed = md.apply_decay(store, rate=1.0, tick=10)
    assert removed == 1
    assert plain not in store.memories
    assert emotional in store.memories          # important memories never delete
    assert emotional["activation"] > 0.5        # and fade far slower (×0.24 step)


def test_decay_preconceived_never_background_half():
    pre = {"id": "a", "text": "told", "importance": 3, "source": "preconceived"}
    back = {"id": "b", "text": "bg", "importance": 3, "source": "background"}
    norm = {"id": "c", "text": "auto", "importance": 3, "source": "auto"}
    store = _Store([pre, back, norm])
    md.apply_decay(store, rate=0.4, tick=1)
    assert pre["activation"] == 1.0
    assert back["activation"] > norm["activation"]


def test_decay_zero_rate_is_inert():
    m = {"id": "a", "text": "x", "source": "auto"}
    store = _Store([m])
    assert md.apply_decay(store, rate=0, tick=1) == 0
    assert m.get("activation", 1.0) == 1.0  # absent field means untouched


# ── mechanism: contradiction ─────────────────────────────────────────────

def test_contradiction_links_assert_deny_pair_symmetrically():
    old = {"id": "old", "text": "Anna said she never entered the cellar",
           "entity_ids": ["anna"], "confidence": 0.9}
    new = {"id": "new", "text": "I saw Anna enter the cellar",
           "entity_ids": ["anna"]}
    linked = md.detect_contradiction(new, [old])
    assert [o["id"] for o in linked] == ["old"]
    assert new["contradicts"] == ["old"]
    assert old["contradicts"] == ["new"]
    assert old["confidence"] < 0.9  # the older memory loses a little certainty


def test_contradiction_requires_shared_entity_and_asymmetry():
    no_entity = {"id": "x", "text": "Anna said she never entered the cellar",
                 "entity_ids": ["anna"]}
    new = {"id": "n", "text": "I saw the cat enter the cellar",
           "entity_ids": ["cat"]}
    assert md.detect_contradiction(new, [no_entity]) == []
    # same entity, both assert — not a contradiction
    both_assert = {"id": "y", "text": "Anna entered the cellar with a torch",
                   "entity_ids": ["anna"]}
    new2 = {"id": "n2", "text": "Anna entered the cellar late at night",
            "entity_ids": ["anna"]}
    assert md.detect_contradiction(new2, [both_assert]) == []


def test_contradiction_ignores_attitude_statements():
    """A first-person feeling is not a factual denial (found live: 'I do not
    trust Anna since the cellar key' linked against 'Anna entered the
    cellar'). Sentiment conflicts belong to derive.py, not this linker."""
    fact = {"id": "fact", "text": "Anna entered the cellar late at night",
            "entity_ids": ["anna"]}
    attitude = {"id": "att", "text": "I do not trust Anna since the cellar key",
                "entity_ids": ["anna"]}
    assert md.detect_contradiction({"id": "n3", "text": "Anna entered the cellar twice",
                                    "entity_ids": ["anna"]}, [attitude]) == []
    assert md.detect_contradiction(attitude, [fact]) == []
    # ...but a real denial still links against the same fact
    denial = {"id": "den", "text": "Anna said she never entered the cellar",
              "entity_ids": ["anna"]}
    assert md.detect_contradiction(denial, [fact]) != []


# ── mechanism: consolidation ─────────────────────────────────────────────

def test_consolidation_folds_stale_unimportant_group():
    store = _Store([])
    for i in range(4):
        store.memories.append({"id": f"m{i}", "text": f"moment {i}",
                               "type": "action", "entity_ids": ["shop"],
                               "importance": 2, "source": "auto", "tick": 10 + i})
    keep = {"id": "keep", "text": "the forge burned down",
            "type": "observation", "entity_ids": ["shop"],
            "importance": 8, "source": "auto", "tick": 20}
    store.memories.append(keep)
    result = md.consolidate(store, tick=500)
    assert result["groups"] == 1 and result["folded"] == 4
    assert len(store.memories) == 2  # trace + the important memory
    trace = [m for m in store.memories if m["source"] == "consolidation"][0]
    assert trace["category"] == "semantic"
    assert sorted(trace["source_memory_ids"]) == ["m0", "m1", "m2", "m3"]
    assert keep in store.memories


def test_consolidation_ignores_recent_or_important_or_observation():
    store = _Store([
        {"id": "recent", "text": "just now", "type": "action",
         "entity_ids": ["shop"], "importance": 2, "source": "auto", "tick": 495},
        {"id": "obs", "text": "live belief", "type": "observation", "kind": "item",
         "entity_ids": ["shop"], "importance": 2, "source": "observation", "tick": 10},
        {"id": "one", "text": "single moment", "type": "action",
         "entity_ids": ["inn"], "importance": 2, "source": "auto", "tick": 10},
    ])
    result = md.consolidate(store, tick=500)
    assert result["groups"] == 0 and result["folded"] == 0
    assert len(store.memories) == 3


# ── wiring: Player write path ────────────────────────────────────────────

def test_player_add_memory_derives_category_and_links_contradiction():
    p = Player("Test")
    first = p.add_memory("Anna entered the cellar", 10, importance=6,
                         memory_type="observation", entity_ids=["anna"])
    second = p.add_memory("Anna said she never entered the cellar", 20,
                          importance=7, memory_type="speech", entity_ids=["anna"])
    assert first["category"] == "episodic"
    assert second["contradicts"] == [first["id"]]
    assert first["contradicts"] == [second["id"]]
    social = p.add_memory("I do not trust Anna", 30, memory_type="thought",
                          tags=["rel:Anna"])
    assert social["category"] == "social"


def test_player_recall_reinforces_instead_of_ratcheting_importance():
    p = Player("Test")
    m = p.add_memory("The cellar key was warm", 10, importance=5,
                     memory_type="thought")
    before_importance = m["importance"]
    p.get_relevant_memories("cellar key", tick=15)
    p.get_relevant_memories("cellar key", tick=16)
    assert m["importance"] == before_importance  # the old +1 ratchet is gone
    assert m["reinforcements"] == 2
    assert m["last_recalled_tick"] == 16


def test_trim_prefers_low_value_memories_and_keeps_repeated_experience():
    p = Player("Test")
    noise = p.add_memory("A passing remark about weather", 1, importance=1,
                         memory_type="thought")
    repeated = p.add_memory("The cellar door will not stay open", 2, importance=3,
                            memory_type="thought", entity_ids=["cellar"])
    for _ in range(5):
        p.get_relevant_memories("cellar door")
    p._trim_memories(len(p.memories) - 1)
    assert repeated in p.memories
    assert noise not in p.memories


# ── wiring: HTTP paths ───────────────────────────────────────────────────

def _client():
    from app import create_app
    app = create_app({'TESTING': True})
    return app.test_client()


def _active_player(client):
    return client.get('/api/state').get_json()['active_player']


def test_retrieve_endpoint_filters_suppressed_and_reinforces():
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'The red door on the landing would not open.',
        'importance': 6, 'type': 'observation', 'tick': 5,
    })
    # suppress it by keyword — a suppressed memory must not surface
    client.post(f'/api/players/{name}/memories/suppress', json={
        'keywords': 'red door', 'duration': 0})
    resp = client.post(f'/api/players/{name}/memories/retrieve', json={
        'query': 'red door landing', 'max_results': 5, 'reinforce': True})
    assert resp.status_code == 200
    assert resp.get_json()['memories'] == []

    # unblock → surfaces, and the stored entry is reinforced by the recall
    client.post(f'/api/players/{name}/memories/unblock', json={'keywords': 'red door'})
    resp = client.post(f'/api/players/{name}/memories/retrieve', json={
        'query': 'red door landing', 'max_results': 5, 'reinforce': True})
    memories = resp.get_json()['memories']
    assert len(memories) == 1
    stored = client.get(f'/api/players/{name}/memories').get_json()['memories'][0]
    assert stored['reinforcements'] >= 1


def test_retrieve_structured_groups_and_recency_never_negative():
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Anna threatened me with the knife.',
        'importance': 8, 'type': 'observation', 'tick': 900,
        'entity_ids': ['anna'],
    })
    client.post(f'/api/players/{name}/memories/reflect', json={
        'insights': [{'belief': 'Anna may be dangerous when cornered.',
                      'about': ['Anna'], 'confidence': 0.7}],
        'tick': 910,
    })
    resp = client.post(f'/api/players/{name}/memories/retrieve', json={
        'query': 'Anna knife', 'max_results': 5, 'structured': True,
        'entities': ['anna'], 'tick': 5000, 'reinforce': False})
    data = resp.get_json()
    texts = [m['text'] for m in data['memories']]
    assert 'Anna threatened me with the knife.' in texts
    assert 'Anna may be dangerous when cornered.' in texts
    assert any(m['text'] == 'Anna may be dangerous when cornered.'
               for m in data['groups']['beliefs'])
    assert any(m['text'] == 'Anna threatened me with the knife.'
               for m in data['groups']['events'])


def test_reflect_structured_payload_stamps_provenance_and_rel_tags():
    from app import create_app
    app = create_app({'TESTING': True})
    client = app.test_client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    resp = client.post(f'/api/players/{name}/memories/reflect', json={
        'insights': [{'belief': 'Anna is probably lying about the cellar.',
                      'about': [], 'confidence': 0.71,
                      'behavior': "Verify Anna's claims independently.",
                      'relationship': {'who': 'Anna', 'dim': 'trust', 'delta': -2}}],
        'tick': 100,
    })
    assert resp.status_code == 200
    stored = client.get(f'/api/players/{name}/memories').get_json()['memories']
    beliefs = [m for m in stored if m.get('category') == 'belief']
    procedures = [m for m in stored if m.get('category') == 'procedural']
    socials = [m for m in stored if m.get('category') == 'social']
    assert len(beliefs) == 1 and beliefs[0]['reflection_depth'] == 1
    assert abs(beliefs[0]['confidence'] - 0.71) < 1e-6
    assert len(procedures) == 1
    assert len(socials) == 1
    tags = socials[0]['tags']
    assert any(t == 'rel:Anna' for t in tags)
    assert any(t.startswith('trust:') for t in tags)

    # the delta reaches the derived per-person profile (derive.py) — the same
    # app instance, since the memory lives in THIS world
    from engine.derive import derive_person_profile
    player = app.world.players[name]
    profile = derive_person_profile(player, 'Anna')
    assert profile['trust'] < 0


def test_reflect_depth_guard_blocks_reflections_of_reflections():
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    # seed a first-order reflection (what reflect itself would write)
    client.post(f'/api/players/{name}/memories/reflect', json={
        'insights': [{'belief': 'The cellar is the centre of everything here.',
                      'about': [], 'confidence': 0.8}], 'tick': 50})
    stored = client.get(f'/api/players/{name}/memories').get_json()['memories']
    assert stored[0]['reflection_depth'] == 1

    resp = client.post(f'/api/players/{name}/memories/reflect', json={
        'insights': [{'belief': 'Everything in this house is about cellars.',
                      'about': [], 'confidence': 0.8}],
        'source_memory_ids': [stored[0]['id']], 'tick': 60})
    assert resp.status_code == 409

    # force overrides — the author is the engine's hand, not the agent's
    resp = client.post(f'/api/players/{name}/memories/reflect', json={
        'insights': [{'belief': 'Everything in this house is about cellars.',
                      'about': [], 'confidence': 0.8}],
        'source_memory_ids': [stored[0]['id']], 'tick': 60, 'force': True})
    assert resp.status_code == 200


def test_reencounter_reinforces_instead_of_appending():
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Anna lied to me about the cellar.',
        'importance': 7, 'type': 'thought', 'tick': 10, 'entity_ids': ['anna'],
    })
    resp = client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Anna lied to me about the cellar.',
        'importance': 7, 'type': 'thought', 'tick': 400, 'entity_ids': ['anna'],
    })
    body = resp.get_json()
    assert body.get('reinforced') is True
    stored = client.get(f'/api/players/{name}/memories').get_json()['memories']
    assert len(stored) == 1
    assert stored[0]['reinforcements'] == 1
    assert stored[0]['last_recalled_tick'] == 400


def test_reinforce_endpoint_stamps_specific_ids():
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'A smell of iron in the stairwell.',
        'importance': 5, 'type': 'observation', 'tick': 3})
    stored = client.get(f'/api/players/{name}/memories').get_json()['memories'][0]
    resp = client.post(f'/api/players/{name}/memories/reinforce', json={
        'ids': [stored['id']], 'tick': 77})
    assert resp.get_json()['reinforced'] == 1
    stored = client.get(f'/api/players/{name}/memories').get_json()['memories'][0]
    assert stored['reinforcements'] == 1
    assert stored['last_recalled_tick'] == 77


def test_editor_round_trips_category_confidence_contradicts():
    """task-691 acceptance: the editor's new controls survive the update
    endpoint, and a contradicts link set from one side becomes mutual."""
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    a = client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Anna entered the cellar at night.',
        'importance': 6, 'type': 'observation', 'tick': 10, 'entity_ids': ['anna']})
    b = client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Anna said she never entered the cellar.',
        'importance': 7, 'type': 'speech', 'tick': 20, 'entity_ids': ['anna']})
    aid = a.get_json()['entry']['id']
    bid = b.get_json()['entry']['id']
    # structural detection already linked the pair at write time
    b_before = next(m for m in client.get(f'/api/players/{name}/memories').get_json()['memories'] if m['id'] == bid)
    assert b_before['contradicts'] == [aid]

    # the editor sets the category/confidence explicitly and REPLACES a's
    # contradicts with an empty list — removal must sync b's side too
    resp = client.post(f'/api/players/{name}/memories/entry/{aid}', json={
        'category': 'belief', 'confidence': 0.65, 'contradicts': []})
    assert resp.status_code == 200
    stored = client.get(f'/api/players/{name}/memories').get_json()['memories']
    entry = next(m for m in stored if m['id'] == aid)
    other = next(m for m in stored if m['id'] == bid)
    assert entry['category'] == 'belief'
    assert abs(entry['confidence'] - 0.65) < 1e-6
    assert entry['contradicts'] == []
    assert other['contradicts'] == []  # removal was symmetric

    # re-linking from one side makes it mutual again
    resp = client.post(f'/api/players/{name}/memories/entry/{aid}', json={
        'contradicts': [bid]})
    stored = client.get(f'/api/players/{name}/memories').get_json()['memories']
    entry = next(m for m in stored if m['id'] == aid)
    other = next(m for m in stored if m['id'] == bid)
    assert entry['contradicts'] == [bid]
    assert other['contradicts'] == [aid]


def test_people_endpoint_derives_profiles_from_rel_memories():
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Anna lied to me about the cellar.',
        'importance': 7, 'type': 'thought', 'tick': 10,
        'tags': ['rel:Anna', 'trust:-3'], 'entity_ids': ['anna']})
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Anna helped me carry the lantern.',
        'importance': 5, 'type': 'observation', 'tick': 30,
        'tags': ['rel:Anna', 'trust:+1'], 'entity_ids': ['anna']})

    resp = client.get(f'/api/players/{name}/memories/people')
    assert resp.status_code == 200
    people = resp.get_json()['people']
    assert len(people) == 1
    anna = people[0]
    assert anna['name'] == 'Anna'
    assert anna['memory_count'] == 2
    profile = anna['profile']
    # two trust deltas (−3 ×7, +1 ×5) → net negative, derived by derive.py
    assert profile['trust'] < 0
    assert profile['role'] in ('rival', 'stranger', 'acquaintance', 'hostile')
    assert isinstance(profile['summary'], str) and profile['summary']

    # a character with no rel: memories gets an empty list, not an error
    client.post(f'/api/players/{name}/memories/clear')
    resp = client.get(f'/api/players/{name}/memories/people')
    assert resp.status_code == 200
    assert resp.get_json()['people'] == []


def test_old_save_memory_round_trips_without_new_fields():
    from app import create_app
    app = create_app({'TESTING': True})
    client = app.test_client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    # a bare legacy entry, exactly as a pre-dynamics save would carry it,
    # planted directly on the player (the PUT replace route 405s — pre-existing
    # route shadowing, unrelated here)
    app.world.players[name].memories = [{
        'id': 'old1', 'text': 'I inherited this house.',
        'tick': -50, 'importance': 7, 'type': 'backstory',
        'source': 'manual'}]
    resp = client.post(f'/api/players/{name}/memories/retrieve', json={
        'query': 'inherited house', 'max_results': 3, 'reinforce': False})
    assert resp.status_code == 200
    assert len(resp.get_json()['memories']) == 1
    # and editing it does not lose the legacy shape
    resp = client.post(f'/api/players/{name}/memories/entry/old1', json={
        'text': 'I inherited this house from my father.'})
    assert resp.status_code == 200
    stored = client.get(f'/api/players/{name}/memories').get_json()['memories'][0]
    assert stored['category'] == 'episodic'
    assert stored['confidence'] == 1.0  # manual source → fully trusted
