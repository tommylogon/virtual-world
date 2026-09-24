"""Background agendas: approach variety and the theft agenda (task-468)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node, Edge, EDGE_CARRYING
from player import Player
from engine import background_social as bs


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _actor(w, name, area, *, tags=(), traits=None, hunger=0):
    p = Player(name)
    w.add_player(p)
    p.current_area = area
    w.set_player_area(name, area)
    p.simulation_mode = "background"
    p.state = "idle"
    p.activity = None
    p.tags = list(tags)
    p.traits = dict(traits or {})
    p.vitals["Hunger"] = hunger
    return p


def _carry(w, owner, name, tags=()):
    node = Node(id=f"item_{name}", type="item", name=name,
                properties={"name": name, "tags": list(tags), "actions": [],
                            "weight": 1})
    w.graph.add_node(node)
    pid = w.player_manager.get_player_node_id(owner.name)
    w.graph.add_edge(Edge(source=node.id, target=pid, type=EDGE_CARRYING))
    return node


# ───────────────────────── approach variety ───────────────────────────────

class TestApproachVariety:
    def test_approach_is_never_hostile_or_a_noop(self):
        a = Player("A")
        b = Player("B")
        for tick in range(30):
            action = bs.choose_approach_action(a, b, tick)
            assert action in bs.APPROACH_ACTIONS
            assert action not in ("bully", "ignore")

    def test_approach_is_deterministic(self):
        a = Player("A")
        b = Player("B")
        assert bs.choose_approach_action(a, b, 7) == \
            bs.choose_approach_action(a, b, 7)

    def test_cold_band_never_confides_or_flirts(self):
        a = Player("A")
        b = Player("B")
        # No relationship: confide (friend) and flirt (close friend) are gated out.
        seen = {bs.choose_approach_action(a, b, t) for t in range(200)}
        assert "confide" not in seen and "flirt" not in seen

    def test_warm_band_can_confide(self):
        a = Player("A")
        b = Player("B")
        a.relationships = {"B": {"closeness": 60}}
        b.relationships = {"A": {"closeness": 60}}
        seen = {bs.choose_approach_action(a, b, t) for t in range(200)}
        assert "confide" in seen


# ─────────────────────── trait-driven agenda choice ───────────────────────

class TestAgendaChoice:
    def test_hostile_trait_pushes_bully_over_compliment(self):
        a = Player("A")
        a.traits = {"hostile": True}
        b = Player("B")
        weights = bs.action_weights(a, b)
        assert weights["bully"] > weights["compliment"]


# ──────────────────────────── theft agenda ────────────────────────────────

class TestTheftAgenda:
    def test_a_tagged_thief_steals_from_a_neighbour(self):
        w = _world()
        thief = _actor(w, "Thief", "Camp", tags=["thief"])
        victim = _actor(w, "Victim", "Camp")
        item = _carry(w, victim, "coin purse")
        calls = []

        def _steal(item_name, target_name):
            calls.append((item_name, target_name))
            return "stolen"

        w.steal_item = _steal
        outcomes = bs.run_theft_pass(w, tick=0)
        assert len(outcomes) == 1
        assert outcomes[0]["success"] is True
        assert calls == [("coin purse", "Victim")]
        assert w.graph.get_node(item.id) is not None

    def test_a_starving_character_reaches_only_for_food(self):
        w = _world()
        hungry = _actor(w, "Hungry", "Camp", hunger=90)
        victim = _actor(w, "Victim", "Camp")
        _carry(w, victim, "heavy rock", tags=["stone"])
        _carry(w, victim, "bread", tags=["food"])
        calls = []
        w.steal_item = lambda i, t: calls.append((i, t)) or "stolen"
        bs.run_theft_pass(w, tick=0)
        assert len(calls) == 1 and calls[0][1] == "Victim"
        assert calls[0][0].startswith("bread")

    def test_theft_is_cooled_down_and_capped(self):
        w = _world()
        _actor(w, "Thief", "Camp", tags=["thief"])
        victim = _actor(w, "Victim", "Camp")
        _carry(w, victim, "coin purse")
        w.steal_item = lambda i, t: "stolen"
        assert len(bs.run_theft_pass(w, tick=0)) == 1
        assert len(bs.run_theft_pass(w, tick=10)) == 0          # cooldown
        assert len(bs.run_theft_pass(w, tick=300)) == 1         # second attempt
        assert len(bs.run_theft_pass(w, tick=600)) == 0         # daily cap

    def test_a_non_thief_with_a_full_belly_does_nothing(self):
        w = _world()
        _actor(w, "Innocent", "Camp")
        victim = _actor(w, "Victim", "Camp")
        _carry(w, victim, "coin purse")
        calls = []
        w.steal_item = lambda i, t: calls.append((i, t))
        assert bs.run_theft_pass(w, tick=0) == []
        assert calls == []

    def test_the_thief_is_restored_as_active(self):
        w = _world()
        _actor(w, "Thief", "Camp", tags=["thief"])
        victim = _actor(w, "Victim", "Camp")
        _carry(w, victim, "coin purse")
        before = w.active_player
        w.steal_item = lambda i, t: "stolen"
        bs.run_theft_pass(w, tick=0)
        assert w.active_player == before
