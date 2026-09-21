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


def test_a_focused_character_owes_nothing_at_a_one_minute_turn():
    """At a 1-minute turn the decision *is* the whole turn.

    The turn holds one action and the focused character's own LLM turn spent it,
    so the deterministic tier has nothing left to spend. This is why the
    asymmetry below is invisible at the camp's default turn length and only
    appears when the turn gets longer.
    """
    w = _world()
    w.time_per_tick_minutes = 1
    w.active_player = None
    p = _bg_player(w, Thirst=5, Hunger=80, Energy=90)
    p.simulation_mode = "active"      # focused: it has its own turn
    food = _add_item(w, AREA, "dried meat", ["food"], ["eat"])
    w.tick_turn()
    assert p.vitals["Hunger"] > 70    # did not eat on top of its own decision
    assert w.graph.get_node(food.id) is not None


def test_a_focused_character_spends_the_rest_of_a_long_turn():
    """Its decision is its first action, not its whole turn.

    At a 15-minute turn the decision costs one minute; the deterministic tier
    spends the other fourteen, exactly as it does for a background character.
    Without this a focused goblin did one thing and stood still for fourteen
    minutes while its background twin did fifteen things (task-409).
    """
    w = _world()
    w.time_per_tick_minutes = 15
    w.active_player = None
    p = _bg_player(w, Thirst=5, Hunger=80, Energy=90)
    p.simulation_mode = "active"
    _add_item(w, AREA, "dried meat", ["food"], ["eat"])
    w.tick_turn()
    assert p.vitals["Hunger"] <= 40, "focused character did not spend its turn"


def test_the_humans_own_character_is_never_puppeted():
    """The player's remaining minutes belong to the player.

    The player character is focused like any other, but the engine must not
    spend its turn for it — otherwise the world plays the game while the player
    is deciding.
    """
    w = _world()
    w.time_per_tick_minutes = 15
    p = _bg_player(w, Thirst=5, Hunger=80, Energy=90)
    p.simulation_mode = "active"
    w.active_player = p              # this is the player's character
    _add_item(w, AREA, "dried meat", ["food"], ["eat"])
    w.tick_turn()
    assert p.vitals["Hunger"] > 70, "player character acted on its own"


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


def test_actions_per_turn_is_an_interim_approximation():
    """DEBT — this pins the superseded model, not the target one (task-436).

    [[Simulation Model]] supersedes a per-turn *budget* of actions: a turn is a
    timeframe, and a character fills it with an action flow whose length is
    **emergent** from the durations of the actions in it. The budget below
    assumes one-minute actions with no durations, which is why a 30-minute turn
    becomes thirty actions — and therefore ~1,440 actions per character per game
    day. That is the number that makes a camp look frenzied at long turns.

    The assertion is kept so the arithmetic is visible and so that implementing
    the flow model makes this test **fail loudly** and force the rewrite. Do not
    treat `30/30/30` as a requirement; treat it as the current interim limit.
    See `dev_tasks/todo/gameplay/task-436-task-durations-and-remove-action-cost-time.md`.

    It replaced an older contract — "the same number of decisions per game hour
    at any tick length" — which put the background tier on a different clock from
    the live one: at a 1-minute turn it acted ten times less often than the
    player, and the two only agreed around T=10 by coincidence.
    """
    from engine.background_simulation import BackgroundSimulation

    def actions_in(game_minutes, minutes_per_tick):
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
        turns = max(1, int(round(game_minutes / minutes_per_tick)))
        for _ in range(turns):
            p.activity = None          # keep the budget the only variable
            bgs.process_due()
            w.time_ticks += 1
        return len(calls)

    # Interim: one action per game minute, so 30 minutes is 30 actions at 1, 5 or
    # 15 min/turn. A span that divides evenly by every turn length, because a
    # character cannot take a fraction of a turn (20 minutes is 1.33 turns at 15).
    for minutes_per_tick in (1, 5, 15):
        assert actions_in(30, minutes_per_tick) == 30, minutes_per_tick

    # The consequence, stated so the debt is legible rather than implied: at the
    # camp's 1-minute turn this is 1,440 actions per character per game day.
    assert actions_in(30, 1) * 48 == 1_440


def test_a_deferred_character_banks_nothing():
    """`next_due_tick` in the future means no action and no backlog."""
    from engine.background_simulation import BackgroundSimulation, actions_per_turn

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

    # Release it: it spends the turn it now has, not a backlog of ten turns.
    p.next_due_tick = 0
    p.activity = None
    bgs.process_due()
    assert len(calls) == actions_per_turn(w)
    assert len(calls) < 10


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
