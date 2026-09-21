"""Deterministic background survival runner (task-399 / engine.background_simulation)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node, Edge, EDGE_IN
from player import Player

AREA = "Blizzard Forest Clearing"


def _world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _bg_player(world, name="BgGoblin", area=AREA, **vitals):
    p = Player(name)
    world.add_player(p)
    p.current_area = area
    world.set_player_area(name, area)
    p.simulation_mode = "background"
    p.next_due_tick = 0
    for k, v in vitals.items():
        p.vitals[k] = v
    return p


def _add_item(world, area, name, tags, actions=None, item_id=None):
    area_id = world.area_node_id(area)
    n = Node(id=item_id or f"item_{name.lower().replace(' ', '_')}", type="item",
             name=name, properties={
                 "name": name, "tags": list(tags),
                 "actions": list(actions or []), "weight": 1.0,
             })
    world.graph.add_node(n)
    world.graph.add_edge(Edge(source=n.id, target=area_id, type=EDGE_IN))
    return n


def test_background_eats_when_hungry():
    w = _world()
    p = _bg_player(w, Thirst=5, Hunger=80, Energy=90)
    food = _add_item(w, AREA, "dried meat", ["food"], ["eat"])
    w.tick_turn()
    assert p.vitals["Hunger"] <= 40          # ate (−45) despite decay
    assert w.graph.get_node(food.id) is None  # single-use item consumed
    assert any(e["what"].startswith("ate") and e["why"] == "needs:eat"
               for e in p.trace_log)


def test_background_drinks_when_thirsty():
    w = _world()
    p = _bg_player(w, Thirst=80, Hunger=5, Energy=90)
    _add_item(w, AREA, "water skin", ["drink"], ["drink"])
    w.tick_turn()
    assert p.vitals["Thirst"] <= 40
    assert any(e["why"] == "needs:drink" for e in p.trace_log)


def test_active_mode_is_ignored():
    w = _world()
    p = _bg_player(w, Thirst=5, Hunger=80, Energy=90)
    p.simulation_mode = "active"      # back to normal fidelity
    food = _add_item(w, AREA, "dried meat", ["food"], ["eat"])
    w.tick_turn()
    assert p.vitals["Hunger"] > 70    # did not eat
    assert w.graph.get_node(food.id) is not None


def test_due_scheduling_defers_action():
    """An explicit future `next_due_tick` (saves, tools) still defers."""
    w = _world()
    p = _bg_player(w, Thirst=5, Hunger=80, Energy=90)
    p.next_due_tick = 10_000         # not due for a long time
    _add_item(w, AREA, "dried meat", ["food"], ["eat"])
    w.tick_turn()
    assert p.vitals["Hunger"] > 70    # deferred
    p.next_due_tick = 0               # now due
    w.tick_turn()
    assert p.vitals["Hunger"] <= 40   # acted
    # No banking: a turn is one action, so nothing accumulates while deferred.
    # (A backlog would let a character who waited dump many actions at once.)
    assert getattr(p, "_action_credit", 1.0) <= 1.0


def test_a_background_character_acts_once_per_turn():
    """One action per turn, like every other character (task-409).

    This replaces the old contract — "the same number of decisions per game hour
    at any tick length" — which put the background tier on a different clock from
    the live one: at a 1-minute turn it acted ten times less often than the
    player, and the two only agreed around T=10 by coincidence.

    Driven through `process_due` with the character kept available, because over
    real turns the *activity* durations legitimately differ in turns (eight hours
    of sleep is 480 turns at 1 min/tick and 32 at 15), and that would make the
    counts differ for a reason that has nothing to do with the action budget.
    """
    from engine.background_simulation import BackgroundSimulation

    def actions_in(turns, minutes_per_tick):
        w = _world()
        w.time_per_tick_minutes = minutes_per_tick
        p = _bg_player(w, Thirst=50, Hunger=50, Energy=90)
        p.next_due_tick = 0
        bgs = BackgroundSimulation(w)
        calls = []
        real = bgs._act

        def counting(name, player, _real=real):
            if name == p.name:
                calls.append(w.time_ticks)
            return _real(name, player)

        bgs._act = counting
        for _ in range(turns):
            p.activity = None          # keep the budget the only variable
            bgs.process_due()
            w.time_ticks += 1
        return len(calls)

    for minutes_per_tick in (1, 5, 15):
        assert actions_in(10, minutes_per_tick) == 10, minutes_per_tick


def test_a_deferred_character_banks_nothing():
    """`next_due_tick` in the future means no action and no backlog."""
    from engine.background_simulation import BackgroundSimulation

    w = _world()
    p = _bg_player(w, Thirst=50, Hunger=50, Energy=90)
    p.next_due_tick = 10_000
    bgs = BackgroundSimulation(w)
    calls = []
    real = bgs._act

    def counting(name, player, _real=real):
        if name == p.name:
            calls.append(w.time_ticks)
        return _real(name, player)

    bgs._act = counting
    for _ in range(10):
        p.activity = None
        bgs.process_due()
        w.time_ticks += 1
    assert calls == []

    # Release it: it takes one action, not ten.
    p.next_due_tick = 0
    p.activity = None
    bgs.process_due()
    assert len(calls) == 1


def test_a_sleeping_character_takes_no_action_and_banks_nothing():
    """Mid-activity means no decision, and no backlog to dump on waking."""
    from engine.background_simulation import BackgroundSimulation

    w = _world()
    p = _bg_player(w, Thirst=50, Hunger=50, Energy=90)
    p.next_due_tick = 0
    p.activity = {"type": "sleeping", "started_at_tick": 0}

    bgs = BackgroundSimulation(w)
    w.tick_manager._background_sim = bgs
    calls = []
    real = bgs._act

    def counting(name, player, _real=real):
        if name == p.name:
            calls.append(w.time_ticks)
        return _real(name, player)

    bgs._act = counting
    for _ in range(5):
        w.tick_turn()
    assert calls == []
    assert getattr(p, "_action_credit", 1.0) <= 1.0


def test_background_sleeps_when_tired():
    w = _world()
    p = _bg_player(w, Thirst=5, Hunger=5, Energy=10)
    w.tick_turn()
    assert p.activity and p.activity.get("type") == "sleeping"
    assert any(e["what"] == "went to sleep" and e["why"] == "needs:energy"
               for e in p.trace_log)


def test_background_drinks_from_water_area():
    w = _world()
    node = w.graph.get_node(w.area_node_id(AREA))
    node.properties.setdefault("tags", []).append("water")
    p = _bg_player(w, Thirst=80, Hunger=5, Energy=90)
    w.tick_turn()
    assert p.vitals["Thirst"] <= 40
    assert any(e["why"] == "needs:drink" for e in p.trace_log)


def test_areas_with_detects_food_area():
    w = _world()
    _add_item(w, AREA, "dried meat", ["food"], ["eat"])
    from engine.background_simulation import BackgroundSimulation, FOOD_TAGS
    sim = BackgroundSimulation(w)
    assert AREA in sim._areas_with(FOOD_TAGS)
