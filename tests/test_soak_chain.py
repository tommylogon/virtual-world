"""End-to-end soak orders on the real turn loop (task-481 validation).

tests/test_soak_orders.py drives ``soak.apply_orders`` directly. These tests
drive ``world.tick_turn()`` — the same path the live game takes — so the chain
(background pass → soak policy → time spent → promotion → resume memory → turn
event) is exercised together rather than system by system.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node, Edge, EDGE_IN
from player import Player
from engine import soak, timeskip


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
    p.fear_tags = []
    p.interest_tags = []
    p.soak_order = None
    p.simulation_mode = "active"
    try:
        w.player_manager.set_active_player(p.name)
    except Exception:
        pass
    return p


def _spawn(w, name, area, traits=None, human=False):
    previous = w.active_player
    p = Player(name)
    w.add_player(p)
    p.current_area = area
    w.set_player_area(name, area)
    p.simulation_mode = "background"
    p.vitals.update({"Hunger": 0, "Thirst": 0, "Energy": 90})
    if traits:
        p.traits.update(traits)
    if human:
        p.autonomy = False
    if previous:
        try:
            w.player_manager.set_active_player(previous)
        except Exception:
            pass
    return p


def _item(w, area, name, tags):
    node = Node(id=f"item_{name.replace(' ', '_')}", type="item", name=name,
                properties={"name": name, "tags": list(tags), "actions": [],
                            "weight": 1.0})
    w.graph.add_node(node)
    w.graph.add_edge(Edge(source=node.id, target=w.area_node_id(area),
                          type=EDGE_IN))
    return node


def _soak_events(w, name):
    return [e for e in w.game_logger.turn_events
            if e.get("action") == "soak_end" and e.get("actor") == name]


# ───────────────────────── the real turn loop ─────────────────────────────

def test_an_order_steps_and_finishes_on_the_real_turn_loop():
    w = _world()
    hero = _hero(w)
    other = _spawn(w, "Borin", hero.current_area, human=True)
    other.simulation_mode = "active"
    before = len(hero.memories)

    soak.declare(hero, intent="idle", minutes=3)
    assert hero.simulation_mode == "background"

    for _ in range(3):
        w.tick_turn()

    # The order ended itself, the character is attended again, and the span is
    # remembered exactly once.
    assert hero.soak_order is None
    assert hero.simulation_mode == "active"
    assert len(hero.memories) == before + 1
    assert hero.memories[-1].get("source") == "timeskip"
    events = _soak_events(w, hero.name)
    assert events and "finished" in events[-1]["description"]

    # The other attended human was never drawn into the order.
    assert other.soak_order is None
    assert other.simulation_mode == "active"


def test_the_order_is_promoted_when_something_is_feared_mid_span():
    w = _world()
    hero = _hero(w)
    hero.fear_tags = ["goblin"]
    soak.declare(hero, intent="idle", minutes=60)

    w.tick_turn()                       # baseline turn: nothing there yet
    assert hero.soak_order is not None

    _spawn(w, "Snarl", hero.current_area, traits={"goblin": True})
    w.tick_turn()

    assert hero.soak_order is None and hero.simulation_mode == "active"
    assert "frightened" in hero.conditions
    events = _soak_events(w, hero.name)
    assert events and "interrupted" in events[-1]["description"]


def test_a_search_order_hands_back_when_it_finds_its_target():
    """The policy's find is not dropped: it ends the order like a skip does."""
    w = _world()
    hero = _hero(w)
    hero.skills["Survival"] = 3
    _item(w, hero.current_area, "iron ore", ["ore"])

    soak.declare(hero, intent="search", minutes=30, target_type="ore")
    w.tick_turn()

    assert hero.soak_order is None and hero.simulation_mode == "active"
    assert hero.memories[-1].get("source") == "timeskip"
    events = _soak_events(w, hero.name)
    assert events and "interrupted" in events[-1]["description"]


def test_an_order_keeps_its_span_across_other_characters_turns():
    w = _world()
    hero = _hero(w)
    _spawn(w, "Borin", hero.current_area, human=True)
    soak.declare(hero, intent="idle", minutes=5)

    w.tick_turn()
    assert soak.remaining(hero) == 4
    w.tick_turn()
    assert soak.remaining(hero) == 3
    assert hero.simulation_mode == "background"
    assert hero.soak_order["declared_minutes"] == 5


def test_a_death_in_soak_finishes_the_order():
    w = _world()
    hero = _hero(w)
    soak.declare(hero, intent="idle", minutes=60)
    w.tick_turn()
    hero.state = "dead"
    w.tick_turn()
    assert hero.soak_order is None
    assert hero.simulation_mode == "active"
    events = _soak_events(w, hero.name)
    assert events and "You died." in events[-1]["description"]
