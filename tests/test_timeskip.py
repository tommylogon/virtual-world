"""Timeskip actions (task-464) + interrupt evaluator (task-466)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node, Edge, EDGE_IN
from engine import interrupts as iv
from engine import timeskip


def _world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _hero(w):
    p = w.get_active_player_obj()
    if p is None:
        p = next(iter(w.players.values()))
    return p


def _add_item(w, area, name, tags, item_id=None):
    area_id = w.area_node_id(area)
    node = Node(id=item_id or f"item_{name.lower().replace(' ', '_')}", type="item",
                name=name, properties={"name": name, "tags": list(tags),
                                       "actions": [], "weight": 1.0})
    w.graph.add_node(node)
    w.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
    return node


def _safe(p):
    """Neutralise the danger bands so a short skip does not interrupt by accident."""
    p.vitals.update({"HP": 100, "Thirst": 0, "Hunger": 0, "Bladder": 0,
                     "Energy": 100, "Hygiene": 100, "Sanity": 100,
                     "Social": 100, "Entertainment": 100})
    p.conditions.clear()
    p.state = "idle"
    return p


# ───────────────────────── interrupt evaluator ────────────────────────────

def _snap(**kw):
    base = {"vitals": {}, "conditions": set(), "hp": 100, "state": "idle",
            "area": "A", "visible": set(), "log_len": 0, "te_len": 0}
    base.update(kw)
    return base


def test_interrupt_death():
    reasons = iv.evaluate(_snap(), _snap(state="dead"))
    assert reasons and reasons[0].kind == "death"


def test_interrupt_threat_from_event_marker():
    events = [{"description": "[Steal] Goblin tries to steal your knife"}]
    reasons = iv.evaluate(_snap(), _snap(), events=events)
    assert any(r.kind == "threat" for r in reasons)


def test_interrupt_hostile_condition():
    reasons = iv.evaluate(_snap(), _snap(conditions={"grappled"}))
    assert any(r.why == "condition:grappled" for r in reasons)


def test_interrupt_drive_danger_crossing_only():
    crossed = iv.evaluate(_snap(vitals={"Thirst": 88}), _snap(vitals={"Thirst": 92}))
    assert any(r.why == "vital:thirst" for r in crossed)
    # already in danger: no repeat interrupt
    already = iv.evaluate(_snap(vitals={"Thirst": 95}), _snap(vitals={"Thirst": 97}))
    assert not any(r.why == "vital:thirst" for r in already)


def test_interrupt_resource_danger_crossing():
    reasons = iv.evaluate(_snap(vitals={"Energy": 12}), _snap(vitals={"Energy": 9}))
    assert any(r.why == "vital:energy" for r in reasons)


def test_interrupt_involuntary_bladder():
    reasons = iv.evaluate(_snap(vitals={"Bladder": 93}), _snap(vitals={"Bladder": 96}))
    assert any(r.kind == "involuntary" for r in reasons)


def test_interrupt_discovery_by_tag():
    before = _snap()
    after = _snap(visible={("item", "i1", "old coin", ("relic",))})
    reasons = iv.evaluate(before, after, watch_tags=["relic"])
    assert any(r.why == "discovery:interest" for r in reasons)


def test_interrupt_arrival_on_travel():
    reasons = iv.evaluate(_snap(area="A"), _snap(area="B"),
                          intent="travel", target="B")
    assert any(r.kind == "arrival" for r in reasons)


# ───────────────────────── timeskip runner ────────────────────────────────

def test_idle_advances_the_clock_by_the_span():
    w = _world()
    hero = _safe(_hero(w))
    start = w.time_ticks
    res = timeskip.advance(w, 5, intent="idle")
    assert res.ok and res.elapsed_minutes == 5 and res.ticks == 5
    assert w.time_ticks == start + 5


def test_idle_does_not_interrupt_when_nothing_happens():
    w = _world()
    hero = _safe(_hero(w))
    hero.vitals["Thirst"] = 0
    hero.vitals["Hunger"] = 0
    hero.vitals["Bladder"] = 0
    res = timeskip.advance(w, 3, intent="idle")
    assert res.ok and not res.interrupted


def test_idle_lets_vitals_decay():
    w = _world()
    hero = _safe(_hero(w))
    hero.vitals["Energy"] = 50          # resource: decays ~0.1/min
    res = timeskip.advance(w, 60, intent="idle")
    assert res.vitals_after["Energy"] < 50


def test_forced_minute_resolution_and_restore():
    w = _world()
    _safe(_hero(w))
    w.time_per_tick_minutes = 15
    res = timeskip.advance(w, 3, intent="idle")
    assert res.elapsed_minutes == 3
    assert res.ticks == 3
    assert w.time_per_tick_minutes == 15, "frame dial must be restored"


def test_vital_danger_interrupts_and_returns_control():
    w = _world()
    hero = _hero(w)
    hero.vitals["Thirst"] = 89          # one tick of decay crosses 90
    res = timeskip.advance(w, 600, intent="idle")
    assert res.ok and res.interrupted
    assert res.interrupt["why"] == "vital:thirst"
    assert res.elapsed_minutes < 600


def test_involuntary_interrupts_a_wait():
    w = _world()
    hero = _hero(w)
    hero.vitals["Bladder"] = 94
    res = timeskip.advance(w, 600, intent="idle")
    assert res.interrupted
    assert res.interrupt["kind"] == "involuntary"


def test_search_finds_an_item_and_stops():
    w = _world()
    hero = _safe(_hero(w))
    area = hero.current_area
    if not area:
        exits = w.build_exits_for_area("Blizzard Forest Clearing", include_hidden=True)
        area = "Blizzard Forest Clearing"
        assert exits, "fixture world has no exits"
    _add_item(w, area, "old relic", ["relic"])
    res = timeskip.advance(w, 60, intent="search", watch_tags=["relic"])
    assert res.interrupted
    assert res.interrupt["why"] == "search:found"


def test_travel_moves_along_a_way():
    w = _world()
    hero = _safe(_hero(w))
    area = hero.current_area
    exits = w.build_exits_for_area(area, include_hidden=True) if area else {}
    if not exits:
        # put the hero somewhere that has an exit
        for node in w.graph.nodes.values():
            if node.type == "area":
                ex = w.build_exits_for_area(node.name, include_hidden=True)
                if ex:
                    hero.current_area = node.name
                    area = node.name
                    exits = ex
                    break
    assert exits, "no connected areas in the fixture world"
    target = next(iter(exits.values()))["target"]
    res = timeskip.advance(w, 30, intent="travel", target=target)
    assert res.elapsed_minutes >= 1
    assert hero.current_area != area


def test_leisure_eats_when_hungry():
    w = _world()
    hero = _safe(_hero(w))
    hero.vitals["Hunger"] = 80
    _add_item(w, hero.current_area, "dried meat", ["food"])
    timeskip.advance(w, 30, intent="leisure")
    assert hero.vitals["Hunger"] <= 40, "leisure did not eat"


def test_explore_moves_through_an_exit():
    w = _world()
    hero = _safe(_hero(w))
    area = hero.current_area
    exits = w.build_exits_for_area(area, include_hidden=True) if area else {}
    if not exits:
        return  # fixture has no connected areas
    res = timeskip.advance(w, 10, intent="explore")
    assert res.elapsed_minutes >= 1
    assert hero.current_area != area


def test_unknown_intent_is_rejected():
    w = _world()
    res = timeskip.advance(w, 10, intent="dance")
    assert not res.ok and "intent" in res.reason.lower()


def test_only_one_skip_at_a_time():
    w = _world()
    timeskip._ACTIVE = True
    try:
        res = timeskip.advance(w, 5, intent="idle")
        assert not res.ok and "already running" in res.reason
    finally:
        timeskip._ACTIVE = False


def test_duration_is_clamped(monkeypatch):
    w = _world()
    _safe(_hero(w))
    monkeypatch.setattr(timeskip, "MAX_MINUTES", 2)
    res = timeskip.advance(w, 10 ** 9, intent="idle")
    assert res.ok
    assert res.elapsed_minutes <= 2


# ───────────────────────── summary / memory ───────────────────────────────

def test_skip_writes_exactly_one_memory():
    w = _world()
    hero = _safe(_hero(w))
    before = len(getattr(hero, "memories", []) or [])
    res = timeskip.advance(w, 4, intent="idle")
    assert res.ok
    memories = list(getattr(hero, "memories", []) or [])
    assert len(memories) == before + 1
    entry = memories[-1]
    assert entry.get("source") == "timeskip"
    assert "waited" in entry.get("text", "").lower()


def test_no_memory_when_nothing_happened():
    w = _world()
    hero = _safe(_hero(w))
    before = len(getattr(hero, "memories", []) or [])
    timeskip.advance(w, 0, intent="idle")   # rejected: below minimum
    assert len(getattr(hero, "memories", []) or []) == before


# ───────────────────────── route planning ─────────────────────────────────

def test_route_helpers_report_hop_duration():
    w = _world()
    hero = _safe(_hero(w))
    area = hero.current_area
    exits = w.build_exits_for_area(area, include_hidden=True) if area else {}
    if not exits:
        return  # fixture has no connected areas; nothing to measure
    target = next(iter(exits.values()))["target"]
    assert timeskip.route_hops(w, area, target) == 1
    assert timeskip.travel_minutes(w, area, target) == timeskip.per_hop_minutes()
    assert timeskip.route_hops(w, area, area) == 0


# ───────────────────────── HTTP route ─────────────────────────────────────

def _client():
    from app import create_app
    app = create_app({"TESTING": True})
    hero = _safe(_hero(app.world))
    try:
        app.world.player_manager.set_active_player(hero.name)
    except Exception:
        pass
    return app.test_client()


def test_timeskip_route_runs_and_reports():
    client = _client()
    resp = client.post("/api/world/timeskip", json={"intent": "idle", "minutes": 2})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] and data["elapsed_minutes"] == 2
    assert data["clock_after"]


def test_timeskip_route_rejects_unknown_intent():
    client = _client()
    resp = client.post("/api/world/timeskip", json={"intent": "dance", "minutes": 2})
    assert resp.status_code == 400


def test_timeskip_route_rejects_oversize():
    client = _client()
    resp = client.post("/api/world/timeskip", json={"intent": "idle", "minutes": 99999})
    assert resp.status_code == 400
