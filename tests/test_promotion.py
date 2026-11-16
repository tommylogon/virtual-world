"""Promotion/demotion memory bridge (task-399).

Covers the handoff acceptance criteria: activation consolidates a background
span into exactly one bounded ``source: "background"`` memory, repeated
activation never duplicates it, foreground actions are never summarized as
background, and the consolidation marks survive save/load.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine import promotion, lived_log as lived_log_mod
from graph import Node, WorldGraph


SCOPE_MANIFEST = {
    "the_pines": {"id": "the_pines", "name": "The Pines", "kind": "building",
                  "children": ["pines_floor_3"]},
    "pines_floor_3": {"id": "pines_floor_3", "name": "Floor 3", "kind": "floor",
                      "parent_id": "the_pines", "children": ["apartment_3b"]},
    "apartment_3b": {"id": "apartment_3b", "name": "Apartment 3B",
                     "kind": "apartment", "parent_id": "pines_floor_3",
                     "area_ids": ["area_3b_living"]},
}


class _ScopeGS:
    """A game-state stub with just what activation and flushing read."""

    def __init__(self, tick=100):
        self.graph = WorldGraph()
        self.world_scopes = dict(SCOPE_MANIFEST)
        self.players = {}
        self.time_ticks = tick
        self.time_per_tick_minutes = 1
        self.graph.add_node(Node(id="area_lobby", type="area", name="Lobby",
                                 properties={"world_scope_id": "the_pines"}))
        self.graph.add_node(Node(id="area_hall3", type="area", name="Hallway 3",
                                 properties={"world_scope_id": "pines_floor_3"}))
        self.graph.add_node(Node(id="area_3b_living", type="area", name="3B Living",
                                 properties={"world_scope_id": "apartment_3b"}))

    def area_node_id(self, name):
        for nid, node in self.graph.nodes.items():
            if node.type == "area" and node.name == name:
                return nid
        return None


def _resident(gs, name, area, *, background=True, soak=False):
    p = Player(name)
    p.current_area = area
    if soak:
        p.soak_order = {"intent": "idle", "declared_minutes": 10,
                        "remaining_minutes": 10}
    if background:
        promotion.offload(gs, p)
    gs.players[name] = p
    return p


class _GS:
    """Minimal game-state stub: the two clock fields the bridge reads."""

    def __init__(self, tick=0, minutes=1):
        self.time_ticks = tick
        self.time_per_tick_minutes = minutes


def _player(area="Chief's Pit"):
    p = Player("Gribba")
    p.current_area = area
    return p


def _bg(p, gs, kind="act", what="worked", why="schedule:work"):
    lived_log_mod.record(p, gs.time_ticks, kind, what, why=why, area=p.current_area)


def _bg_memories(p):
    return [m for m in p.memories if m.get("source") == "background"]


# ───────────────────────────── offload ────────────────────────────────────

def test_offload_demotes_and_stamps_the_boundary():
    p, gs = _player(), _GS(tick=100)
    assert promotion.offload(gs, p) is True
    assert p.simulation_mode == "background"
    assert p.last_offload_tick == 100


def test_offloading_an_already_background_character_is_a_noop():
    p, gs = _player(), _GS(tick=100)
    promotion.offload(gs, p)
    assert promotion.offload(gs, p) is False


# ───────────────────────────── promotion ──────────────────────────────────

def test_promoting_an_attended_character_does_nothing():
    p, gs = _player(), _GS(tick=100)
    assert promotion.promote(gs, p) is None
    assert _bg_memories(p) == []


def test_promotion_writes_one_background_memory_without_truncation():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)

    gs.time_ticks = 40
    _bg(p, gs, what="worked", why="schedule:work")
    gs.time_ticks = 45
    _bg(p, gs, kind="move", what="travelled", why="needs:hunger")
    gs.time_ticks = 70

    text = promotion.promote(gs, p)
    assert p.simulation_mode == "active"
    memories = _bg_memories(p)
    assert len(memories) == 1
    assert memories[0]["text"] == text        # stored verbatim, no truncation
    assert "routine" in text and "work" in text


def test_repeated_promotion_does_not_duplicate_the_memory():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 30
    _bg(p, gs)
    promotion.promote(gs, p)

    assert promotion.promote(gs, p) is None
    assert len(_bg_memories(p)) == 1


def test_a_second_span_adds_exactly_one_more_memory():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 20
    _bg(p, gs, what="worked", why="schedule:work")
    promotion.promote(gs, p)

    assert promotion.offload(gs, p) is True
    gs.time_ticks = 40
    _bg(p, gs, what="slept", why="needs:energy")
    promotion.promote(gs, p)

    assert len(_bg_memories(p)) == 2


def test_foreground_actions_are_never_summarized_as_background():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 20
    _bg(p, gs, what="worked", why="schedule:work")
    promotion.promote(gs, p)

    # A foreground action between the two spans.
    gs.time_ticks = 40
    lived_log_mod.record(p, gs.time_ticks, "plan", "FOREGROUND_MARKER",
                     why="goal:plan", area=p.current_area)

    promotion.offload(gs, p)
    gs.time_ticks = 60
    _bg(p, gs, what="slept", why="needs:energy")
    gs.time_ticks = 70
    text = promotion.promote(gs, p)

    assert "FOREGROUND_MARKER" not in text
    assert "FOREGROUND_MARKER" not in " ".join(
        m["text"] for m in _bg_memories(p))
    assert len(_bg_memories(p)) == 2


def test_an_empty_span_writes_no_memory_but_still_promotes():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 25
    assert promotion.promote(gs, p) is None
    assert p.simulation_mode == "active"
    assert _bg_memories(p) == []


# ───────────────────────────── invariants ─────────────────────────────────

def test_the_summary_is_deterministic_for_a_fixed_span():
    entries = [
        {"t": 11, "kind": "act", "what": "ate", "why": "needs:hunger",
         "salient": False, "area": "Camp"},
        {"t": 12, "kind": "move", "what": "moved", "why": "needs:drink",
         "salient": False, "area": "Camp"},
    ]
    gs = _GS()
    assert (promotion.summarize(gs, entries, since_tick=10, end_tick=20)
            == promotion.summarize(gs, entries, since_tick=10, end_tick=20))


def test_consolidation_marks_survive_serialization():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 20
    _bg(p, gs)
    promotion.promote(gs, p)

    data = p.to_dict()
    assert data["last_offload_tick"] == 10
    assert data["background_consolidated_through"] == 20


def test_a_reloaded_player_does_not_double_consolidate():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 20
    _bg(p, gs)
    promotion.promote(gs, p)
    assert len(_bg_memories(p)) == 1

    # Reload the marks *and the lived log* onto a fresh player and promote again:
    # the span is already consolidated, so no second memory is written.
    payload = p.to_dict()
    reloaded = _player()
    reloaded.last_offload_tick = payload["last_offload_tick"]
    reloaded.background_consolidated_through = payload["background_consolidated_through"]
    lived_log_mod.load(reloaded, payload["lived_log"])
    reloaded.simulation_mode = "background"
    gs.time_ticks = 25
    assert promotion.promote(gs, reloaded) is None


# ──────────────────── atomic transitions + scope boundary ─────────────────

def test_activate_scope_queues_only_background_residents_inside():
    # Level-scoped: child scopes are NOT recursively activated (task-710)
    gs = _ScopeGS()
    dave = _resident(gs, "Dave", "Lobby")         # the_pines own area
    bob = _resident(gs, "Bob", "Hallway 3")       # child pines_floor_3
    alice = _resident(gs, "Alice", "3B Living")   # grandchild apartment_3b
    carol = _resident(gs, "Carol", "Somewhere Else")  # outside every scope

    queued = promotion.activate_scope(gs, "the_pines")

    # Dave is in the_pines; Bob and Alice are in child scopes and must NOT be promoted
    assert queued == ["Dave"]
    assert promotion.pending(gs)["Dave"]["mode"] == "active"
    # Nothing has changed tier yet - the request is queued, not applied.
    assert dave.simulation_mode == "background"
    assert alice.simulation_mode == "background"
    assert bob.simulation_mode == "background"
    assert carol.simulation_mode == "background"

    # Activating apartment_3b specifically activates Alice
    queued_3b = promotion.activate_scope(gs, "apartment_3b")
    assert queued_3b == ["Alice"]

    # Whole world mode activates everyone
    queued_all = promotion.activate_scope(gs, "whole_world")
    assert set(queued_all) == {"Alice", "Bob", "Carol", "Dave"}


def test_flush_applies_the_batch_at_one_boundary():
    gs = _ScopeGS()
    dave = _resident(gs, "Dave", "Lobby")
    bob = _resident(gs, "Bob", "Hallway 3")
    carol = _resident(gs, "Carol", "Somewhere Else")
    promotion.activate_scope(gs, "the_pines")

    changed = promotion.flush(gs)

    assert set(changed) == {"Dave"}
    assert dave.simulation_mode == "active"
    assert bob.simulation_mode == "background"
    assert carol.simulation_mode == "background"
    assert promotion.pending(gs) == {}


def test_a_second_request_for_the_same_character_replaces_the_first():
    gs = _ScopeGS()
    alice = _resident(gs, "Alice", "3B Living")
    promotion.request(gs, alice, "active")
    promotion.request(gs, alice, "background")
    assert promotion.pending(gs)["Alice"]["mode"] == "background"
    promotion.flush(gs)
    assert alice.simulation_mode == "background"


def test_flush_applies_a_queued_offload_and_stamps_the_boundary():
    gs = _ScopeGS(tick=100)
    alice = _resident(gs, "Alice", "3B Living", background=False)
    promotion.request(gs, alice, "background", reason="left-scope")
    promotion.flush(gs)
    assert alice.simulation_mode == "background"
    assert alice.last_offload_tick == 100


def test_flush_drops_a_request_for_a_missing_character():
    gs = _ScopeGS()
    ghost = Player("Ghost")
    promotion.request(gs, ghost, "active")
    assert promotion.flush(gs) == []
    assert promotion.pending(gs) == {}


def test_a_soak_ordered_character_is_not_activated_by_a_scope():
    gs = _ScopeGS()
    _resident(gs, "Dave", "Lobby")
    _resident(gs, "Bob", "Lobby", soak=True)
    queued = promotion.activate_scope(gs, "the_pines")
    assert queued == ["Dave"]


def test_activation_writes_the_span_memory_at_flush():
    gs = _ScopeGS(tick=100)
    alice = _resident(gs, "Alice", "3B Living")
    gs.time_ticks = 120
    _bg(alice, gs, what="worked", why="schedule:work")

    promotion.activate_scope(gs, "apartment_3b")
    promotion.flush(gs)

    assert alice.simulation_mode == "active"
    memories = _bg_memories(alice)
    assert len(memories) == 1
    assert "work" in memories[0]["text"]


def test_observe_route_queues_residents_and_404s_unknown_scope():
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    resident = next(iter(world.players.values()))
    area_id = world.area_node_id(resident.current_area)
    world.world_scopes = {
        "pines": {"id": "pines", "name": "Pines", "area_ids": [area_id]},
    }
    promotion.offload(world, resident)
    client = app.test_client()

    missing = client.post("/api/world/scopes/nope/observe")
    assert missing.status_code == 404

    ok = client.post("/api/world/scopes/pines/observe")
    assert ok.status_code == 200
    body = ok.get_json()
    assert resident.name in body["queued"]
    assert resident.name in body["pending"]



# ─────────────────── tick re-evaluation (task-711) ────────────────────────

def test_evaluate_scope_tick_promotes_on_entry_and_demotes_on_exit():
    gs = _ScopeGS(tick=100)
    alice = _resident(gs, "Alice", "3B Living", background=False)
    bob = _resident(gs, "Bob", "Lobby", background=True)
    gs._active_scope = "apartment_3b"

    # Alice walks out of apartment_3b into Lobby; Bob walks into apartment_3b
    alice.current_area = "Lobby"
    bob.current_area = "3B Living"

    queued = promotion.evaluate_scope_tick(gs)
    assert set(queued) == {"Alice", "Bob"}
    assert promotion.pending(gs)["Alice"]["mode"] == "background"
    assert promotion.pending(gs)["Bob"]["mode"] == "active"

    # Flush lands transitions atomically
    changed = promotion.flush(gs)
    assert set(changed) == {"Alice", "Bob"}
    assert alice.simulation_mode == "background"
    assert alice.last_offload_tick == 100
    assert bob.simulation_mode == "active"


def test_evaluate_scope_tick_negative_exit_demotes_with_span_stamped():
    gs = _ScopeGS(tick=100)
    alice = _resident(gs, "Alice", "3B Living", background=False)
    gs._active_scope = "apartment_3b"

    # Alice leaves the selected scope
    alice.current_area = "Lobby"
    queued = promotion.evaluate_scope_tick(gs)
    assert queued == ["Alice"]

    promotion.flush(gs)
    assert alice.simulation_mode == "background"
    assert alice.last_offload_tick == 100

    # Background work happens while outside
    gs.time_ticks = 150
    _bg(alice, gs, what="prowled", why="schedule:patrol")

    # Alice returns to apartment_3b
    alice.current_area = "3B Living"
    queued = promotion.evaluate_scope_tick(gs)
    assert queued == ["Alice"]
    promotion.flush(gs)

    assert alice.simulation_mode == "active"
    memories = _bg_memories(alice)
    assert len(memories) == 1
    assert "patrol" in memories[0]["text"]


def test_evaluate_scope_tick_soak_order_is_never_touched():
    gs = _ScopeGS(tick=100)
    charlie = _resident(gs, "Charlie", "3B Living", background=True, soak=True)
    gs._active_scope = "apartment_3b"

    queued = promotion.evaluate_scope_tick(gs)
    assert "Charlie" not in queued
    assert "Charlie" not in promotion.pending(gs)
    assert charlie.simulation_mode == "background"

    # Even if outside or inside, soak_order protects it
    charlie.current_area = "Lobby"
    queued = promotion.evaluate_scope_tick(gs)
    assert "Charlie" not in queued


def test_evaluate_scope_tick_whole_world_short_circuits():
    gs = _ScopeGS(tick=100)
    alice = _resident(gs, "Alice", "Lobby", background=False)
    bob = _resident(gs, "Bob", "3B Living", background=True)
    gs._active_scope = "whole_world"

    queued = promotion.evaluate_scope_tick(gs)
    assert queued == []
    assert promotion.pending(gs) == {}


def test_evaluate_scope_tick_measured_from_inside_tick_turn():
    from app import create_app
    app = create_app({"TESTING": True})
    vw = app.world
    resident = next(iter(vw.players.values()))
    area_id = vw.area_node_id(resident.current_area)
    vw.world_scopes = {
        "isolated": {"id": "isolated", "name": "Isolated", "area_ids": [area_id]},
    }
    vw._active_scope = "isolated"
    resident.simulation_mode = "active"

    # Find another area that is outside the scope
    outside_area = None
    for aid, node in vw.graph.nodes.items():
        if node.type == "area" and aid != area_id:
            outside_area = node.name
            break
    assert outside_area is not None

    # Move resident outside the scope
    resident.current_area = outside_area

    # Measure simulation_mode from INSIDE tick_turn
    observed_modes = []
    real_tick_turn = vw.tick_manager.tick_turn

    def spy_tick_turn(*args, **kwargs):
        res = real_tick_turn(*args, **kwargs)
        observed_modes.append(resident.simulation_mode)
        return res

    vw.tick_manager.tick_turn = spy_tick_turn
    vw.tick_turn()

    assert len(observed_modes) == 1
    assert observed_modes[0] == "background"
    assert resident.simulation_mode == "background"
