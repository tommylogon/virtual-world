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
    # task-424: a source that authors on_drink owns its own restore, so the old
    # DRINK_RESTORE fallback constant no longer sets the drop. Assert it quenched,
    # not a fixed amount (the world's water_pitcher is authored at -15).
    assert p.vitals["Thirst"] < 80
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
    p.autonomy = False               # human-driven: the engine must not puppet it
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
    # No banking: the flow fills one timeframe and nothing accumulates while
    # deferred. (A backlog would let a character who waited dump many actions at
    # once — and the credit accumulator that used to allow for that is gone.)
    assert not hasattr(p, "_action_credit")


def test_a_satisfied_character_does_nothing_at_any_turn_length():
    """The flow stops when nothing is due — which is the common case.

    A fed, rested, entertained character spends its whole timeframe doing
    nothing at all. This is what makes a long turn quiet rather than frantic,
    and it is precisely what the superseded per-turn action *budget* got wrong:
    that granted one action per game minute whether or not anything needed
    doing, so a 30-minute turn was thirty passes through the need ladder.
    """
    from engine.background_simulation import BackgroundSimulation

    for minutes_per_tick in (1, 5, 15, 30):
        w = _world()
        w.time_per_tick_minutes = minutes_per_tick
        p = _bg_player(w, Thirst=10, Hunger=10, Energy=90)
        p.vitals["Bladder"] = 0
        p.vitals["Hygiene"] = 100
        p.vitals["Sanity"] = 100
        p.vitals["Entertainment"] = 100
        p.next_due_tick = 0
        bgs = BackgroundSimulation(w)
        calls = []
        real = bgs._act

        def counting(name, player, served=None, _real=real):
            if name == p.name:
                calls.append(1)
            return _real(name, player, served)

        bgs._act = counting
        w.tick_turn()

        assert calls == [], (
            f"T={minutes_per_tick}: acted {len(calls)} times with nothing due"
        )


def test_a_hungry_character_eats_once_per_turn_at_every_turn_length():
    """The load-bearing invariant: behaviour is a function of **game time**, not
    of how much game time a turn happens to cover.

    A meal is a task, so it is done once per timeframe. Under the old budget a
    15-minute turn was an opportunity to eat fifteen times, which is why the
    camp looked frenzied at long turns and calm at short ones.
    """
    from engine.background_simulation import BackgroundSimulation

    for minutes_per_tick in (1, 5, 15, 30):
        w = _world()
        w.time_per_tick_minutes = minutes_per_tick
        # Hunger well above the threshold, and a meal that will not fully clear
        # it — the exact case that used to repeat once per iteration.
        p = _bg_player(w, Thirst=10, Hunger=95, Energy=90)
        p.vitals["Bladder"] = 0
        p.vitals["Hygiene"] = 100
        p.vitals["Sanity"] = 100
        p.vitals["Entertainment"] = 100
        p.next_due_tick = 0
        _add_item(w, AREA, "dried meat", ["food"], ["eat"])
        _add_item(w, AREA, "hard bread", ["food"], ["eat"])

        bgs = BackgroundSimulation(w)
        assert not hasattr(bgs, "_action_credit")
        w.tick_turn()

        meals = [e for e in p.trace_log if e.get("why") == "needs:eat"]
        assert len(meals) == 1, (
            f"T={minutes_per_tick}: ate {len(meals)} times in one turn"
        )


def test_a_walk_repeats_within_a_turn_but_a_meal_does_not():
    """Travel is progress, so it is the one action that fills a timeframe.

    A character walking toward food takes one step per minute, so a 15-minute
    turn is fifteen steps — that is the whole point of `TASK_MINUTES["travel"]`
    being 1 while the other tasks are longer. `served` deliberately excludes
    travel for exactly this reason.
    """
    from engine.background_simulation import BackgroundSimulation, TASK_MINUTES

    assert TASK_MINUTES["travel"] == 1
    # Sleep is the other one-minute entry: it only gets the character lying down,
    # and the sleeping activity owns whatever follows. Every real task is longer,
    # which is what stops it repeating inside one timeframe.
    for task in ("eat", "drink", "relieve", "wash", "recreate", "recuperate", "work"):
        assert TASK_MINUTES[task] > 1, task


def test_a_deferred_character_banks_nothing():
    """`next_due_tick` in the future means no action and no backlog."""
    from engine.background_simulation import BackgroundSimulation, minutes_in_turn

    w = _world()
    p = _bg_player(w, Thirst=50, Hunger=50, Energy=90)
    p.next_due_tick = 10_000
    bgs = BackgroundSimulation(w)
    calls = []
    real = bgs._act

    def counting(name, player, served=None, _real=real):
        if name == p.name:
            calls.append(w.time_ticks)
        return _real(name, player, served)

    bgs._act = counting
    for _ in range(10):
        p.activity = None
        bgs.process_due()
        w.time_ticks += 1
    assert calls == []

    # Release it: it fills the timeframe it now has, not a backlog of ten turns.
    p.next_due_tick = 0
    p.activity = None
    bgs.process_due()
    # Each action consumes at least a minute, so no flow can contain more than
    # the timeframe's worth of them. Ten turns of deferral cannot become one
    # turn of ten actions.
    assert len(calls) <= minutes_in_turn(w)
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

    def counting(name, player, served=None, _real=real):
        if name == p.name:
            calls.append(w.time_ticks)
        return _real(name, player, served)

    bgs._act = counting
    for _ in range(5):
        w.tick_turn()
    assert calls == []
    assert not hasattr(p, "_action_credit")


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


def test_a_task_longer_than_the_timeframe_spans_turns():
    """A ten-minute meal cannot happen inside a one-minute turn.

    Without this the cost is overdrawn — the meal resolves instantly, so a
    fine-grained clock lets a character perform fifteen whole tasks in fifteen
    minutes while a coarse one admits only the two or three that fit. At T=1 the
    meal starts an activity authored in **minutes**, so it costs ten minutes of
    game time however the clock is sliced.
    """
    w = _world()
    w.time_per_tick_minutes = 1
    p = _bg_player(w, Thirst=10, Hunger=90, Energy=90)
    p.vitals["Entertainment"] = 100
    p.next_due_tick = 0
    _add_item(w, AREA, "dried meat", ["food"], ["eat"])

    w.tick_turn()
    assert p.activity is not None, "a 10-minute meal fit inside a 1-minute turn"
    assert p.activity["type"] == "eating"
    assert p.activity["duration_minutes"] == 10

    # It occupies the turns it needs, then releases. A type missing from
    # ACTIVITY_INTERRUPTIBLE would never expire and strand the character busy.
    for _ in range(20):
        w.tick_turn()
        if p.activity is None:
            break
    assert p.activity is None, "the meal never ended — character stuck busy"


def test_a_task_that_fits_does_not_start_an_activity():
    """At a 15-minute turn the same meal is part of the turn, not a span."""
    w = _world()
    w.time_per_tick_minutes = 15
    p = _bg_player(w, Thirst=10, Hunger=90, Energy=90)
    p.vitals["Entertainment"] = 100
    p.next_due_tick = 0
    _add_item(w, AREA, "dried meat", ["food"], ["eat"])

    w.tick_turn()
    assert p.activity is None, "a task that fits should not span turns"
    assert p.vitals["Hunger"] <= 50


def test_every_task_activity_can_expire():
    """The trap the ACTIVITY_INTERRUPTIBLE comment warns about.

    `_tick` only calls `_maybe_end_by_duration` for members of that set, so a
    task activity missing from it runs its elapsed time past its duration
    forever and the character is stuck `busy` — which downstream reads as a
    mysterious refusal to eat, sleep or wash.
    """
    from engine.activities import ACTIVITY_INTERRUPTIBLE, ACTIVITY_SKIP_TURNS

    for kind in ("eating", "drinking", "relieving", "washing", "recreating",
                 "recuperating"):
        assert kind in ACTIVITY_INTERRUPTIBLE, f"{kind} would never expire"
        assert kind in ACTIVITY_SKIP_TURNS, f"{kind} would not occupy a turn"
