"""Per-character soak orders (task-481).

A human declares an order on their turn; the normal turn loop runs the character
on a policy until the span is spent or something promotes them back.
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
    p.soak_order = None
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


# ───────────────────────── engine ─────────────────────────────────────────

def test_an_order_steps_and_expires_with_one_memory():
    w = _world()
    hero = _hero(w)
    before = len(hero.memories)
    soak.declare(hero, intent="idle", minutes=3)
    assert soak.remaining(hero) == 3
    for _ in range(3):
        soak.apply_orders(w)
    assert hero.soak_order is None and soak.remaining(hero) is None
    assert len(hero.memories) == before + 1
    assert hero.memories[-1].get("source") == "timeskip"


def test_cancel_drops_the_order():
    w = _world()
    hero = _hero(w)
    soak.declare(hero, intent="idle", minutes=10)
    assert soak.cancel(hero) is True and hero.soak_order is None
    assert soak.cancel(hero) is False


def test_a_feared_thing_promotes_the_character():
    w = _world()
    hero = _hero(w)
    hero.fear_tags = ["goblin"]
    _spawn(w, "Snarl", hero.current_area, traits={"goblin": True})
    soak.declare(hero, intent="idle", minutes=60)
    soak.apply_orders(w)
    assert hero.soak_order is None
    assert "frightened" in hero.conditions


def test_a_critical_vital_promotes_the_character():
    w = _world()
    hero = _hero(w)
    hero.vitals["Thirst"] = 95
    soak.declare(hero, intent="idle", minutes=60)
    soak.apply_orders(w)
    assert hero.soak_order is None


def test_a_hostile_condition_promotes_the_character():
    w = _world()
    hero = _hero(w)
    hero.conditions["grappled"] = [{}]
    soak.declare(hero, intent="idle", minutes=60)
    soak.apply_orders(w)
    assert hero.soak_order is None


def test_a_watched_discovery_promotes_the_character():
    w = _world()
    hero = _hero(w)
    soak.declare(hero, intent="explore", minutes=60, watch_tags=["relic"])
    soak.apply_orders(w)                       # first turn seeds the baseline
    assert hero.soak_order is not None
    _item(w, hero.current_area, "old relic", ["relic"])
    soak.apply_orders(w)
    assert hero.soak_order is None


def test_unknown_intent_is_rejected():
    w = _world()
    hero = _hero(w)
    try:
        soak.declare(hero, intent="dance", minutes=5)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# ───────────────────────── background mode ────────────────────────────────

def test_an_order_makes_the_character_genuinely_background():
    w = _world()
    hero = _hero(w)
    hero.simulation_mode = "active"
    soak.declare(hero, intent="idle", minutes=5)
    assert hero.simulation_mode == "background"
    soak.cancel(hero)
    assert hero.simulation_mode == "active"


def test_finishing_restores_attended_mode():
    w = _world()
    hero = _hero(w)
    soak.declare(hero, intent="idle", minutes=1)
    soak.apply_orders(w)
    assert hero.soak_order is None
    assert hero.simulation_mode == "active"


def test_process_due_leaves_an_ordered_character_to_its_order():
    """A hungry ordered character on `idle` is not auto-fed by the soak pass.

    autonomy True so the ordinary human-skip rule does not apply — the order
    skip is what keeps the generic need policy away.
    """
    from engine.background_simulation import BackgroundSimulation
    w = _world()
    hero = _hero(w)
    hero.autonomy = True
    hero.vitals["Hunger"] = 80
    soak.declare(hero, intent="idle", minutes=10)
    BackgroundSimulation(w).process_due()
    assert hero.vitals["Hunger"] == 80, "the generic need policy ran anyway"


# ───────────────────────── routes ─────────────────────────────────────────

def _client():
    from app import create_app
    app = create_app({"TESTING": True})
    app.world.time_per_tick_minutes = 1
    hero = _hero(app.world)
    return app, hero, app.test_client()


def test_soak_route_declares_and_cancels():
    _app, hero, client = _client()
    resp = client.post("/api/world/soak", json={"intent": "leisure", "minutes": 5})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["mode"] == "soak" and data["order"]["intent"] == "leisure"
    assert hero.soak_order is not None

    resp = client.delete("/api/world/soak")
    assert resp.status_code == 200 and resp.get_json()["ok"] is True
    assert hero.soak_order is None


def test_timeskip_declares_an_order_when_another_human_is_attended():
    app, hero, client = _client()
    _spawn(app.world, "Borin", hero.current_area, human=True)   # attended, not soaking
    resp = client.post("/api/world/timeskip", json={"intent": "idle", "minutes": 5})
    assert resp.status_code == 200
    assert resp.get_json()["mode"] == "soak"
    assert hero.soak_order is not None


def test_timeskip_still_fast_forwards_when_the_human_is_alone():
    app, hero, client = _client()
    resp = client.post("/api/world/timeskip", json={"intent": "idle", "minutes": 3})
    assert resp.status_code == 200
    assert resp.get_json()["mode"] == "character"
    assert hero.soak_order is None


def test_state_payload_reports_the_soak_order_for_the_roster():
    _app, hero, client = _client()
    client.post("/api/world/soak", json={"intent": "travel", "minutes": 30,
                                         "heading": "west"})
    state = client.get("/api/state").get_json()
    soak = state["players"][hero.name]["soak"]
    assert soak and soak["intent"] == "travel"
    assert soak["remaining_minutes"] == 30


def test_soak_can_be_cancelled_by_character_name():
    app, hero, client = _client()
    other = _spawn(app.world, "Borin", hero.current_area, human=True)
    client.post("/api/world/soak", json={"intent": "idle", "minutes": 5})

    # Cancelling a character with no order is a clean no-op, and does not touch
    # the active character's order.
    resp = client.delete("/api/world/soak?character=Borin")
    assert resp.status_code == 200 and resp.get_json()["ok"] is False
    assert hero.soak_order is not None

    resp = client.delete("/api/world/soak?character=" + hero.name)
    assert resp.get_json()["ok"] is True and hero.soak_order is None
    assert other.soak_order is None


def test_soak_cancel_rejects_an_unknown_character():
    _app, _hero2, client = _client()
    assert client.delete("/api/world/soak?character=Nobody").status_code == 404
