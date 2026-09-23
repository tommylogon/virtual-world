"""Fear tags: per-character fears drive frightened/interrupts (task-469)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node, Edge, EDGE_IN
from player import Player
from engine import fear
from engine import timeskip
from engine.effect_handlers import tags as tag_handlers


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _hero(w):
    p = w.get_active_player_obj() or next(iter(w.players.values()))
    p.vitals.update({"HP": 100, "Thirst": 0, "Hunger": 0, "Bladder": 0,
                     "Energy": 100, "Hygiene": 100, "Sanity": 100,
                     "Social": 100, "Entertainment": 100})
    p.conditions.clear()
    p.state = "idle"
    return p


def _npc(w, name, area, traits=None):
    previous = w.active_player
    p = Player(name)
    w.add_player(p)                 # add_player makes the new character active
    p.current_area = area
    w.set_player_area(name, area)
    p.simulation_mode = "background"
    p.next_due_tick = 0
    if traits:
        p.traits.update(traits)
    if previous:
        try:
            w.player_manager.set_active_player(previous)
        except Exception:
            pass
    return p


# ───────────────────────── detection ──────────────────────────────────────

def test_no_fears_no_sources():
    w = _world()
    hero = _hero(w)
    hero.fear_tags = []
    assert fear.fear_sources(w, hero) == []


def test_detects_a_feared_character_by_trait():
    w = _world()
    hero = _hero(w)
    hero.fear_tags = ["goblin"]
    _npc(w, "Snarl", hero.current_area, {"goblin": True})
    sources = fear.fear_sources(w, hero)
    assert any(s["kind"] == "character" and s["name"] == "Snarl" for s in sources)


def test_ignores_a_character_you_do_not_fear():
    w = _world()
    hero = _hero(w)
    hero.fear_tags = ["goblin"]
    _npc(w, "Guard", hero.current_area, {"guard": True})
    assert not any(s["name"] == "Guard" for s in fear.fear_sources(w, hero))


def test_goblins_do_not_fear_goblins():
    """The whole point: a feared group is not hostile to its own kind."""
    w = _world()
    hero = _hero(w)
    goblin = _npc(w, "Snarl", hero.current_area, {"goblin": True})
    goblin.fear_tags = ["guard"]           # goblins fear guards, not goblins
    _npc(w, "Grub", hero.current_area, {"goblin": True})
    assert fear.fear_sources(w, goblin) == []


def test_detects_a_feared_area_tag():
    w = _world()
    hero = _hero(w)
    node = w.graph.get_node(w.area_node_id(hero.current_area))
    node.properties.setdefault("tags", []).append("haunted")
    hero.fear_tags = ["haunted"]
    assert any(s["kind"] == "area" for s in fear.fear_sources(w, hero))


def test_detects_a_feared_item():
    w = _world()
    hero = _hero(w)
    area_id = w.area_node_id(hero.current_area)
    spider = Node(id="item_spider", type="item", name="giant spider",
                  properties={"name": "giant spider", "tags": ["spider"],
                              "actions": [], "weight": 1.0})
    w.graph.add_node(spider)
    w.graph.add_edge(Edge(source=spider.id, target=area_id, type=EDGE_IN))
    hero.fear_tags = ["spider"]
    assert any(s["kind"] == "item" for s in fear.fear_sources(w, hero))


# ───────────────────────── reaction ───────────────────────────────────────

def test_apply_frightening_sets_the_condition_with_its_source():
    w = _world()
    hero = _hero(w)
    hero.fear_tags = ["goblin"]
    _npc(w, "Snarl", hero.current_area, {"goblin": True})
    source = fear.react(w, hero)
    assert source and source["name"] == "Snarl"
    instances = hero.conditions.get("frightened") or []
    assert instances and instances[-1].get("source") == "Snarl"


def test_timeskip_pauses_on_fear():
    w = _world()
    hero = _hero(w)
    hero.fear_tags = ["goblin"]
    snarl = _npc(w, "Snarl", hero.current_area, {"goblin": True})
    snarl.next_due_tick = 10 ** 9        # it stays put, so the fear is present
    res = timeskip.advance(w, 60, intent="idle")
    assert res.interrupted and res.interrupt["kind"] == "fear"
    assert "frightened" in hero.conditions


# ───────────────────────── effects ────────────────────────────────────────

class _Self:
    def _resolve_player_name(self, game_state, target):
        return game_state.active_player if target in ("self", "") else target


def test_add_fear_tag_effect():
    w = _world()
    hero = _hero(w)
    tag_handlers.handle_add_fear_tag(
        _Self(), {"tag": "Goblin", "target": "self"}, {}, game_state=w)
    assert "goblin" in hero.fear_tags
    # adding again is a no-op, not a duplicate
    tag_handlers.handle_add_fear_tag(
        _Self(), {"tag": "goblin", "target": "self"}, {}, game_state=w)
    assert hero.fear_tags == ["goblin"]


def test_remove_fear_tag_effect():
    w = _world()
    hero = _hero(w)
    hero.fear_tags = ["goblin", "spider"]
    tag_handlers.handle_remove_fear_tag(
        _Self(), {"tag": "goblin", "target": "self"}, {}, game_state=w)
    assert hero.fear_tags == ["spider"]


def test_add_interest_tag_effect():
    w = _world()
    hero = _hero(w)
    tag_handlers.handle_add_interest_tag(
        _Self(), {"tag": "ruins", "target": "self"}, {}, game_state=w)
    assert "ruins" in hero.interest_tags


# ───────────────────────── persistence ────────────────────────────────────

def test_fear_tags_serialize():
    w = _world()
    hero = _hero(w)
    hero.fear_tags = ["goblin"]
    assert hero.to_dict().get("fear_tags") == ["goblin"]


# ───────────────────────── deliberate verbs ───────────────────────────────

def test_fear_target_action_tags_the_named_character():
    w = _world()
    hero = _hero(w)
    _npc(w, "Snarl", hero.current_area, {"goblin": True})
    hero.fear_tags = []
    message = w.fear_target("Snarl")
    assert "goblin" in hero.fear_tags
    assert "fear" in message.lower()


def test_interest_target_action_tags_a_named_item():
    w = _world()
    hero = _hero(w)
    area_id = w.area_node_id(hero.current_area)
    node = Node(id="item_ruin_map", type="item", name="old map",
                properties={"name": "old map", "tags": ["ruins"],
                            "actions": [], "weight": 1.0})
    w.graph.add_node(node)
    w.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
    w.interest_target("old map")
    assert "ruins" in hero.interest_tags


def test_fear_verb_via_http():
    from app import create_app
    app = create_app({"TESTING": True})
    app.world.time_per_tick_minutes = 1
    hero = _hero(app.world)
    _npc(app.world, "Snarl", hero.current_area, {"goblin": True})
    hero.fear_tags = []
    client = app.test_client()
    resp = client.post("/api/action", json={"command": "fear Snarl"})
    assert resp.status_code == 200
    assert "goblin" in hero.fear_tags
