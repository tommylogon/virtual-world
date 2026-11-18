"""Character goals: character-private data that survives a scenario round-trip.

A goal is an intention, so it lives in the character's own record (``Player.goals``)
and never as a world node. These tests pin the contract `engine/goals.normalize`
promises and the save/load path task-807 requires (task-807).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from engine import goals
from virtual_world_engine import VirtualWorld


def _world():
    world = VirtualWorld()
    if "Goal Room" not in world.areas:
        world.movement.add_area(Area("Goal Room", "a room.", []))
    return world


def test_normalize_drops_a_goal_with_neither_id_nor_what():
    """A goal with nothing in it cannot be referred to or shown, so it is
    dropped rather than given an invented intention."""
    dropped = goals.normalize([
        {"status": "active"},            # no id, no what
        "not a dict",
        {"id": "real", "what": "Do a thing"},
    ])
    assert [g["id"] for g in dropped] == ["real"]


def test_normalize_derives_an_id_and_coerces_an_unknown_status():
    """An authored goal may omit its id and may carry a status the engine does
    not know; both must degrade to a usable record, not crash the load."""
    norm = goals.normalize([{"what": "Become chief", "status": "ascended"}])
    assert norm == [{"id": "become_chief", "what": "Become chief",
                     "status": goals.DEFAULT_STATUS}]


def test_normalize_keeps_motivation_and_intention():
    """GIMP's M and I are stored on the goal -- the one home for them."""
    norm = goals.normalize([{
        "id": "become_chief", "what": "Become chief", "status": "active",
        "motivation": "I want respect and power",
        "intention": "because then the others will not push me around",
    }])
    assert norm[0]["motivation"] == "I want respect and power"
    assert norm[0]["intention"] == "because then the others will not push me around"


def test_active_returns_only_the_goals_being_pursued():
    norm = goals.active([
        {"id": "a", "what": "A", "status": "active"},
        {"id": "b", "what": "B", "status": "proposed"},
        {"id": "c", "what": "C", "status": "reached"},
    ])
    assert [g["id"] for g in norm] == ["a"]


def test_a_dormant_goal_is_held_but_not_pursued():
    """``dormant`` is a real status, not a typo to be corrected: a character can
    hold an ambition they are not working right now. It must survive normalise
    and stay out of ``active`` -- the two things that make it different from
    ``proposed``."""
    assert "dormant" in goals.GOAL_STATUSES

    norm = goals.normalize([
        {"id": "a", "what": "A", "status": "active"},
        {"id": "b", "what": "B", "status": "dormant"},
    ])
    assert [g["status"] for g in norm] == ["active", "dormant"]
    assert [g["id"] for g in goals.active(norm)] == ["a"]

    # and it is settable, so a character can put a goal down and pick it up
    moved, error = goals.set_status(norm, "b", "active")
    assert error is None
    assert goals.find(moved, "b")["status"] == "active"


def test_a_goals_round_trip_through_a_scenario():
    """Author goals on a character, save the scenario, reload it: the goals --
    including the id derived on normalise -- come back unchanged."""
    world = _world()
    pname = world.active_player
    world.get_player(pname).goals = [
        {"id": "become_chief", "what": "Become chief of the camp",
         "status": "active", "motivation": "I want respect and power",
         "intention": "because then the others will not push me around"},
        {"what": "Find my brother", "status": "proposed"},
    ]

    reloaded = VirtualWorld()
    reloaded.load_from_dict(world.to_scenario_dict())
    got = reloaded.get_player(pname).goals

    assert [g["id"] for g in got] == ["become_chief", "find_my_brother"]
    assert got[0]["status"] == "active"
    assert got[0]["motivation"] == "I want respect and power"
    assert got[1]["status"] == "proposed"


def test_set_goal_creates_then_updates_in_place():
    """Restating the same want must update the goal, not stack a duplicate."""
    new, error = goals.set_goal([], "Become chief")
    assert error is None
    assert new == [{"id": "become_chief", "what": "Become chief", "status": "active"}]

    again, error = goals.set_goal(new, "Become chief", motivation="I want respect")
    assert error is None
    assert len(again) == 1
    assert again[0]["motivation"] == "I want respect"


def test_set_goal_rejects_an_empty_want():
    new, error = goals.set_goal([], "   ")
    assert error and new == []


def test_set_status_completes_and_drops_by_id_or_what():
    start = goals.normalize([{"id": "a", "what": "A", "status": "active"}])
    done, error = goals.set_status(start, "a", "reached")
    assert error is None and done[0]["status"] == "reached"
    gone, error = goals.set_status(start, "A", "dropped")
    assert error is None and gone[0]["status"] == "dropped"


def test_set_status_reports_an_unknown_goal():
    _, error = goals.set_status([], "nothing", "reached")
    assert error and "nothing" in error


def test_the_goal_action_is_wired_through_the_dispatcher():
    """The dispatched verb is the caller: `goal set/complete/drop` must write the
    character's own goals, preserving the case the player typed."""
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    name = app.world.active_player

    client.post("/api/action", json={"action": "goal set Become chief", "character": name})
    assert app.world.get_player(name).goals == [
        {"id": "become_chief", "what": "Become chief", "status": "active"}]

    client.post("/api/action", json={"action": "goal complete become_chief", "character": name})
    assert app.world.get_player(name).goals[0]["status"] == "reached"

    client.post("/api/action", json={"action": "goal drop become_chief", "character": name})
    assert app.world.get_player(name).goals[0]["status"] == "dropped"


def test_existing_goals_without_blocks_still_normalise():
    """Adding blocks/links must not disturb a goal that has neither."""
    assert goals.normalize([{"id": "a", "what": "A"}]) == [
        {"id": "a", "what": "A", "status": "proposed"}]


def test_blocks_accept_a_comma_string_and_links_round_trip():
    norm = goals.normalize([{"id": "a", "what": "A", "blocks": "b, c ; d", "links": ["x"]}])
    assert norm[0]["blocks"] == ["b", "c", "d"]
    assert norm[0]["links"] == ["x"]


def test_a_goal_blocked_by_another_is_unblocked_when_it_is_reached():
    """Chain: A blocked by B. Reaching B unblocks A, with no per-goal script."""
    chain = goals.normalize([
        {"id": "a", "what": "A", "status": "active", "blocks": ["b"]},
        {"id": "b", "what": "B", "status": "active"},
    ])
    a = next(g for g in chain if g["id"] == "a")
    assert goals.resolve_blocks(a, {"goal": goals.goal_resolver(chain)}) == ["b"]

    reached, _ = goals.set_status(chain, "b", "reached")
    a2 = next(g for g in reached if g["id"] == "a")
    assert goals.resolve_blocks(a2, {"goal": goals.goal_resolver(reached)}) == []


def test_a_blocker_with_no_resolver_holds_the_goal():
    """An unknown prefix keeps the goal blocked rather than silently freeing it."""
    goal = {"id": "a", "what": "A", "status": "active", "blocks": ["event:storm_passed"]}
    assert goals.resolve_blocks(goal, {"goal": lambda ref: True}) == ["event:storm_passed"]


def test_with_blockers_marks_only_the_blocked_goal():
    goals_list = goals.normalize([
        {"id": "a", "what": "A", "blocks": ["b"]},
        {"id": "b", "what": "B"},
    ])
    out = goals.with_blockers(goals_list, {"goal": goals.goal_resolver(goals_list)})
    assert out[0].get("blocked_by") == ["b"]
    assert "blocked_by" not in out[1]


def test_set_status_appends_to_the_goal_log_with_a_tick():
    log = []
    chain = goals.normalize([{"id": "a", "what": "A", "status": "active"}])
    goals.set_status(chain, "a", "reached", tick=42, log=log)
    assert log == [{"goal_id": "a", "what": "A", "status": "reached", "tick": 42}]


def test_set_goal_logs_creation_then_the_update():
    log = []
    g, _ = goals.set_goal([], "Become chief", tick=5, log=log)
    g, _ = goals.set_goal(g, "Become chief", status="reached", tick=9, log=log)
    assert [(e["status"], e["tick"]) for e in log] == [("active", 5), ("reached", 9)]


def test_goal_history_drops_malformed_rows():
    log = goals.history([
        {"goal_id": "a", "what": "A", "status": "reached", "tick": 1},
        {"status": "nonsense"},
        "junk",
        {"goal_id": "b", "status": "dropped", "tick": 2},
    ])
    assert [e["goal_id"] for e in log] == ["a", "b"]


def test_a_goal_log_round_trips_through_a_scenario():
    world = _world()
    pname = world.active_player
    player = world.get_player(pname)
    player.goals = [
        {"id": "a", "what": "A", "status": "reached"},
        {"id": "b", "what": "B", "status": "active"},
    ]
    player.goal_log = [
        {"goal_id": "a", "what": "A", "status": "reached", "tick": 3},
        {"goal_id": "b", "what": "B", "status": "active", "tick": 7},
    ]
    reloaded = VirtualWorld()
    reloaded.load_from_dict(world.to_scenario_dict())
    assert reloaded.get_player(pname).goal_log == [
        {"goal_id": "a", "what": "A", "status": "reached", "tick": 3},
        {"goal_id": "b", "what": "B", "status": "active", "tick": 7},
    ]


def test_the_goal_verb_records_history_with_ticks():
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    name = app.world.active_player

    client.post("/api/action", json={"action": "goal set Hold the gate", "character": name})
    client.post("/api/action", json={"action": "goal complete hold_the_gate", "character": name})

    log = app.world.get_player(name).goal_log
    assert [e["status"] for e in log] == ["active", "reached"]
    assert all("tick" in e for e in log)


def test_offer_then_accept_spawns_a_goal():
    obs, offer, error = goals.offer_obligation([], "Deliver the sealed letter", from_name="Elder Mara")
    assert error is None and offer["status"] == "offered"

    obs, spawned, error = goals.respond_obligation(obs, "deliver_the_sealed_letter", "accept", goals=[])
    assert error is None
    assert obs[0]["status"] == "accepted"
    assert obs[0]["goal_id"] == "deliver_the_sealed_letter"
    assert spawned == [{"id": "deliver_the_sealed_letter",
                        "what": "Deliver the sealed letter",
                        "status": "active",
                        "intention": "obligation to Elder Mara",
                        "source": "obligation:deliver_the_sealed_letter"}]


def test_refusing_an_obligation_spawns_no_goal():
    obs, _, _ = goals.offer_obligation([], "Guard the gate")
    obs, spawned, error = goals.respond_obligation(obs, "guard_the_gate", "refuse", goals=[])
    assert error is None
    assert obs[0]["status"] == "refused"
    assert "goal_id" not in obs[0]
    assert spawned == []


def test_obligations_expire_past_their_due_tick():
    obs, _, _ = goals.offer_obligation([], "Attend the moot", due=100)
    assert goals.expire_obligations(obs, 50)[0]["status"] == "offered"
    assert goals.expire_obligations(obs, 100)[0]["status"] == "forgotten"


def test_obligations_round_trip_through_a_scenario():
    world = _world()
    pname = world.active_player
    world.get_player(pname).obligations = [
        {"id": "guard_the_gate", "charge": "Guard the gate", "status": "accepted", "from": "The chief"},
    ]
    reloaded = VirtualWorld()
    reloaded.load_from_dict(world.to_scenario_dict())
    assert reloaded.get_player(pname).obligations == [
        {"id": "guard_the_gate", "charge": "Guard the gate", "status": "accepted", "from": "The chief"}]


def test_the_obligation_verb_accepts_and_spawns_a_goal():
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    name = app.world.active_player
    app.world.get_player(name).obligations = [
        {"id": "fetch_water", "charge": "Fetch water", "status": "offered"}]
    client.post("/api/action", json={"action": "obligation accept fetch_water", "character": name})
    player = app.world.get_player(name)
    assert player.obligations[0]["status"] == "accepted"
    assert any(g["id"] == "fetch_water" for g in player.goals)


# ───────────────────────────── task-822 tests ──────────────────────────────────

def test_fifteen_fields_round_trip_through_scenario():
    """task-822: verify the full 15-field goal record survives scenario round-trip."""
    world = _world()
    pname = world.active_player
    player = world.get_player(pname)
    player.goals = [
        {
            "id": "become_chief",
            "what": "Become chief of the camp",
            "why": "I want respect and power",
            "motivation": "I want respect and power",
            "intention": "because then the others will not push me around",
            "hoped_for": "the chief's staff and the clan seat",
            "source": "obligation:elders",
            "opened_tick": 4,
            "priority": 1,
            "visibility": "secret",
            "blocks": [{"ref": "character:Croak-Mother", "note": "she will not approve an outsider"}],
            "achieve": [{"ref": "item:chiefs_staff", "note": "symbol of authority"}],
            "achieve_mode": "all",
            "links": ["unite_goblins"],
            "deadline": 120,
            "status": "active",
        }
    ]

    reloaded = VirtualWorld()
    reloaded.load_from_dict(world.to_scenario_dict())
    loaded = reloaded.get_player(pname).goals[0]

    assert loaded["id"] == "become_chief"
    assert loaded["what"] == "Become chief of the camp"
    assert loaded["why"] == "I want respect and power"
    assert loaded["motivation"] == "I want respect and power"
    assert loaded["intention"] == "because then the others will not push me around"
    assert loaded["hoped_for"] == "the chief's staff and the clan seat"
    assert loaded["source"] == "obligation:elders"
    assert loaded["opened_tick"] == 4
    assert loaded["priority"] == 1
    assert loaded["visibility"] == "secret"
    assert loaded["blocks"] == [{"ref": "character:Croak-Mother", "note": "she will not approve an outsider"}]
    assert loaded["achieve"] == [{"ref": "item:chiefs_staff", "note": "symbol of authority"}]
    assert loaded["achieve_mode"] == "all"
    assert loaded["links"] == ["unite_goblins"]
    assert loaded["deadline"] == 120
    assert loaded["status"] == "active"
    # progress is projected, never stored
    assert "progress" not in loaded
    assert "blocked_by" not in loaded


def test_ref_with_note_and_bare_string_round_trip():
    """task-822: refs can be bare strings or dicts carrying note."""
    norm = goals.normalize([{
        "id": "test_refs",
        "what": "Test refs",
        "blocks": [
            {"ref": "character:Croak-Mother", "note": "distrusts me"},
            "item:torch",
        ],
        "achieve": [
            {"ref": "item:chiefs_staff", "note": "symbol of authority"},
        ],
        "links": ["sister_goal"],
    }])
    g = norm[0]
    assert g["blocks"] == [
        {"ref": "character:Croak-Mother", "note": "distrusts me"},
        "item:torch",
    ]
    assert g["achieve"] == [{"ref": "item:chiefs_staff", "note": "symbol of authority"}]
    assert g["links"] == ["sister_goal"]


def test_source_priority_visibility_deadline_safe_defaults():
    """task-822: safe fallback for invalid or malformed field values."""
    norm = goals.normalize([{
        "what": "Vague Ambition",
        "source": "unsupported_nonsense",
        "visibility": "super_hidden",
        "priority": "not_an_int",
        "deadline": "invalid_tick",
    }])
    g = norm[0]
    assert g["source"] == "self"
    assert g["visibility"] == "known"
    assert g["priority"] == 0
    assert "deadline" not in g


def test_reached_and_combinator_all_and_any():
    """task-822: achieve combinator 'all' vs 'any'."""
    resolvers = {
        "item": lambda v: v == "staff",
        "tag": lambda v: v == "respected",
    }
    # all mode (default)
    g_all = {
        "id": "g1", "what": "All",
        "achieve": ["item:staff", "tag:respected"],
        "achieve_mode": "all",
    }
    assert goals.reached(g_all, resolvers) is True

    g_all_unmet = {
        "id": "g2", "what": "All Unmet",
        "achieve": ["item:staff", "tag:chief"],  # tag:chief is False
        "achieve_mode": "all",
    }
    assert goals.reached(g_all_unmet, resolvers) is False

    # any mode
    g_any = {
        "id": "g3", "what": "Any",
        "achieve": ["item:staff", "tag:unreachable"],
        "achieve_mode": "any",
    }
    assert goals.reached(g_any, resolvers) is True

    g_any_unmet = {
        "id": "g4", "what": "Any Unmet",
        "achieve": ["item:crown", "tag:unreachable"],
        "achieve_mode": "any",
    }
    assert goals.reached(g_any_unmet, resolvers) is False

    # Empty achieve is never auto-reached
    g_empty = {"id": "g5", "what": "Empty", "achieve": []}
    assert goals.reached(g_empty, resolvers) is False


def test_progress_projection():
    """task-822: progress projects met/unmet counts and done status."""
    resolvers = {"item": lambda v: v == "staff"}
    g = {
        "id": "g1", "what": "Progress Test",
        "achieve": ["item:staff", "item:sword"],
    }
    prog = goals.goal_progress(g, resolvers)
    assert prog["count"] == 1
    assert prog["total"] == 2
    assert prog["met"] == ["item:staff"]
    assert prog["unmet"] == ["item:sword"]
    assert prog["done"] is False


def test_sync_reached_active_flips_and_logs():
    """task-822: active goal flips to reached when achieve is satisfied."""
    player = type("MockPlayer", (), {
        "goals": [{"id": "g1", "what": "G1", "status": "active", "achieve": ["item:staff"]}],
        "goal_log": [],
    })()
    resolvers = {"item": lambda v: True}
    goals.sync_reached(player, resolvers, tick=42)

    assert player.goals[0]["status"] == "reached"
    assert player.goal_log == [{"goal_id": "g1", "what": "G1", "status": "reached", "tick": 42}]


def test_sync_reached_deadline_drops_unreached_goal():
    """task-822: deadline moves an un-reached goal to dropped at its tick."""
    player = type("MockPlayer", (), {
        "goals": [{
            "id": "timed", "what": "Timed", "status": "active",
            "achieve": ["item:unobtainable"], "deadline": 50,
        }],
        "goal_log": [],
    })()
    resolvers = {"item": lambda v: False}

    # Before deadline: stays active
    goals.sync_reached(player, resolvers, tick=49)
    assert player.goals[0]["status"] == "active"
    assert player.goal_log == []

    # At deadline: dropped
    goals.sync_reached(player, resolvers, tick=50)
    assert player.goals[0]["status"] == "dropped"
    assert player.goal_log == [{"goal_id": "timed", "what": "Timed", "status": "dropped", "tick": 50}]


def test_turn_auto_reached_live():
    """task-822 step 1: active goal with achieve ref flips to reached on turn advance."""
    world = _world()
    pname = world.active_player
    player = world.get_player(pname)
    pnode_id = world.player_manager._player_node_id(pname)

    from graph import Node, Edge, EDGE_CARRYING
    staff_node = Node(
        id="item_chiefs_staff",
        type="item",
        name="Chief Staff",
        properties={"name": "Chief Staff", "uses": 1},
    )
    world.graph.add_node(staff_node)
    world.graph.add_edge(Edge(source=staff_node.id, target=pnode_id, type=EDGE_CARRYING))

    player.goals = goals.normalize([{
        "id": "have_staff",
        "what": "Hold the chief's staff",
        "status": "active",
        "achieve": [f"item:{staff_node.id}"],
    }])
    player.goal_log = []

    # Run turn tick
    world.tick_turn()

    assert player.goals[0]["status"] == "reached"
    assert len(player.goal_log) >= 1
    entry = player.goal_log[-1]
    assert entry["goal_id"] == "have_staff"
    assert entry["status"] == "reached"


def test_deterministic_reached_verdict():
    """task-822: deterministic, no RNG in reached evaluations."""
    resolvers = {"item": lambda v: v == "a"}
    g = {"id": "g", "what": "Det", "achieve": ["item:a", "item:b"]}
    v1 = goals.reached(g, resolvers)
    v2 = goals.reached(g, resolvers)
    v3 = goals.reached(g, resolvers)
    assert v1 == v2 == v3 == False


# ───────────────────────────── task-896 tests ──────────────────────────────────

def test_same_charge_from_two_issuers_stays_distinct():
    """Two issuers asking for the same thing are two offers, not an overwrite."""
    obs, a, _ = goals.offer_obligation([], "Guard the gate", from_name="Mara", from_id="node_mara")
    obs, b, _ = goals.offer_obligation(obs, "Guard the gate", from_name="Brek", from_id="node_brek")
    assert len(obs) == 2
    assert a["id"] != b["id"]
    assert {o["from_id"] for o in obs} == {"node_mara", "node_brek"}
    assert a["id"] == "guard_the_gate"  # first keeps the legacy slug


def test_same_issuer_restating_an_open_offer_revises_in_place():
    obs, a, _ = goals.offer_obligation([], "Guard the gate", from_id="node_mara", due=10)
    obs, b, _ = goals.offer_obligation(obs, "Guard the gate", from_id="node_mara", due=20)
    assert len(obs) == 1 and obs[0]["due"] == 20 and a["id"] == b["id"]


def test_accepting_twice_makes_no_duplicate_goal_or_history():
    log = []
    obs, offer, _ = goals.offer_obligation([], "Fetch water", from_name="Mara")
    obs, gl, _ = goals.respond_obligation(obs, offer["id"], "accept", goals=[], tick=3, log=log)
    obs, gl, err = goals.respond_obligation(obs, offer["id"], "accept", goals=gl, tick=4, log=log)
    assert err is None
    assert len(gl) == 1
    assert len(log) == 1  # the second accept recorded nothing
    assert gl[0]["source"] == f"obligation:{offer['id']}"


def test_unanswered_expiry_differs_from_accepted_overdue():
    obs, a, _ = goals.offer_obligation([], "Attend the moot", due=10)
    obs, b, _ = goals.offer_obligation(obs, "Carry the letter", due=10)
    obs, _gl, _ = goals.respond_obligation(obs, b["id"], "accept", goals=[])
    out = {o["id"]: o["status"] for o in goals.expire_obligations(obs, 10)}
    assert out[a["id"]] == "forgotten"
    assert out[b["id"]] == "failed"


def test_reached_goal_completes_its_obligation_exactly_once():
    obs, offer, _ = goals.offer_obligation([], "Fetch water", from_name="Mara")
    obs, gl, _ = goals.respond_obligation(obs, offer["id"], "accept", goals=[])
    gl, _ = goals.set_status(gl, "fetch_water", "reached")
    obs, changed = goals.sync_obligations(obs, gl)
    assert changed == [offer["id"]] and obs[0]["status"] == "done"
    obs, changed = goals.sync_obligations(obs, gl)
    assert changed == []  # already done: no second transition


def test_dropped_goal_fails_its_obligation():
    obs, offer, _ = goals.offer_obligation([], "Fetch water")
    obs, gl, _ = goals.respond_obligation(obs, offer["id"], "accept", goals=[])
    gl, _ = goals.set_status(gl, "fetch_water", "dropped")
    obs, changed = goals.sync_obligations(obs, gl)
    assert obs[0]["status"] == "failed"


def test_issuer_identity_survives_a_scenario_round_trip():
    world = _world()
    pname = world.active_player
    world.get_player(pname).obligations = [
        {"id": "guard_the_gate", "charge": "Guard the gate", "status": "offered",
         "from": "Mara", "from_id": "node_mara"}]
    reloaded = VirtualWorld()
    reloaded.load_from_dict(world.to_scenario_dict())
    got = reloaded.get_player(pname).obligations[0]
    assert got["from_id"] == "node_mara" and got["from"] == "Mara"


def _two_agents():
    from player import Player
    world = _world()
    a = world.get_player(world.active_player)
    b = Player("Brek")
    b.current_area = a.current_area
    world.add_player(b)
    world.set_active_player(a.name)
    return world, a, b


def test_issue_offer_writes_to_the_recipient_with_the_issuer_node_id():
    world, a, b = _two_agents()
    record, err = goals.issue_offer(world, a.name, "Brek", "Guard the gate", due=50)
    assert err is None
    assert [o["charge"] for o in b.obligations] == ["Guard the gate"]
    assert b.obligations[0]["from_id"] == world.player_manager.get_player_node_id(a.name)
    assert not a.obligations  # the issuer's own record is untouched


def test_issue_offer_refuses_self_stranger_and_absent_recipient():
    world, a, b = _two_agents()
    assert goals.issue_offer(world, a.name, a.name, "x")[1]
    assert goals.issue_offer(world, a.name, "Nobody", "x")[1]
    b.current_area = "Elsewhere"
    assert "not here" in goals.issue_offer(world, a.name, "Brek", "x")[1]
    assert not b.obligations


def test_offer_verb_is_wired_through_the_dispatcher():
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    world = app.world
    from player import Player
    name = world.active_player
    brek = Player("Brek")
    brek.current_area = world.get_player(name).current_area
    world.add_player(brek)
    world.set_active_player(name)

    client.post("/api/action", json={"action": "offer Brek: Guard the gate due 99", "character": name})

    assert [o["charge"] for o in brek.obligations] == ["Guard the gate"]
    assert brek.obligations[0]["due"] == 99
    assert brek.obligations[0]["status"] == "offered"

def test_obligation_exchange_scenario_fixture():
    from app import create_app
    import json
    app = create_app({'TESTING': True})
    client = app.test_client()

    with open('data/scenarios/obligation_exchange.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    res = client.post('/api/load', json=data)
    assert res.status_code == 200

    world = app.world
    mara = world.get_player('Elder Mara')
    brek = world.get_player('Brek')
    assert mara is not None
    assert brek is not None

    # Mara offers Brek an obligation
    res = client.post('/api/action', json={'action': 'offer Brek: Deliver the sealed letter due 20', 'character': 'Elder Mara'})
    assert res.status_code == 200
    assert len(brek.obligations) == 1
    obl = brek.obligations[0]
    assert obl['id'] == 'deliver_the_sealed_letter'
    assert obl['status'] == 'offered'
    assert obl['from_id'] == getattr(mara, 'node_id', 'player_Elder_Mara')
    assert obl['from'] == 'Elder Mara'
    assert obl['due'] == 20

    # Brek accepts the obligation
    res2 = client.post('/api/action', json={'action': 'obligation accept deliver_the_sealed_letter', 'character': 'Brek'})
    assert res2.status_code == 200
    assert brek.obligations[0]['status'] == 'accepted'
    assert any(g.get('source') == 'obligation:deliver_the_sealed_letter' for g in brek.goals)


def test_goal_reached_fires_trigger_and_grants_consequence():
    """task-823: reached goal dispatches goal_reached event; an ordinary trigger
    answers it by granting an item via existing mechanics (containment/carrying edge)."""
    world = _world()
    pname = world.active_player
    player = world.get_player(pname)
    pnode_id = world.player_manager._player_node_id(pname)
    pnode = world.graph.get_node(pnode_id)

    # 1. Goal carries prose hope, NO grants or reward table
    goal_data = {
        "id": "become_chief",
        "what": "Become chief of the tribe",
        "status": "active",
        "hoped_for": "Lead the tribe and carry the chief staff",
        "achieve": ["flag:elected_chief"],
    }
    assert "grants" not in goal_data
    assert "reward" not in goal_data
    player.goals = goals.normalize([goal_data])
    player.goal_log = []

    # 2. Add ordinary trigger on goal_reached answering become_chief
    trigger_data = {
        "id": "trig_chief_staff",
        "trigger_type": "goal_reached",
        "conditions": {
            "type": "goal_id",
            "value": "become_chief",
        },
        "effects": [
            {
                "effect_type": "give_item",
                "item_id": "item_chiefs_staff",
                "name": "Chief Staff",
                "target": "target",
            }
        ],
    }
    pnode.properties["triggers"] = [trigger_data]

    # Pre-condition: player does not have chief staff
    from graph import EDGE_CARRYING
    carried_before = [
        e.source for e in world.graph.get_edges_for_target(pnode_id, EDGE_CARRYING)
    ]
    assert not any("staff" in s.lower() for s in carried_before)

    # 3. Satisfy the goal condition and tick the world
    player.flags = {"elected_chief": True}
    world.tick_turn()

    # Goal is reached
    assert player.goals[0]["status"] == "reached"

    # Consequence is a real node granted to player via carrying edge
    carried_after = [
        world.graph.get_node(e.source)
        for e in world.graph.get_edges_for_target(pnode_id, EDGE_CARRYING)
    ]
    staff_nodes = [n for n in carried_after if n and "staff" in (n.name or "").lower()]
    assert len(staff_nodes) == 1
    staff_node = staff_nodes[0]
    assert staff_node.type == "item"

    # A second character can take the item by normal mechanics
    from player import Player
    rival = Player("Rival")
    rival.current_area = "Goal Room"
    world.player_manager.players["Rival"] = rival
    rival_node_id = world.player_manager._player_node_id("Rival")
    from graph import Node
    world.graph.add_node(Node(id=rival_node_id, name="Rival", type="character"))

    # Rival takes the staff: remove carrying edge to player, add carrying edge to rival
    world.graph.remove_edge(staff_node.id, pnode_id, EDGE_CARRYING)
    from graph import Edge
    world.graph.add_edge(Edge(source=staff_node.id, target=rival_node_id, type=EDGE_CARRYING))

    rival_carried = [
        e.source for e in world.graph.get_edges_for_target(rival_node_id, EDGE_CARRYING)
    ]
    assert staff_node.id in rival_carried


def test_goal_reached_without_trigger_completes_without_consequence():
    """task-823: removing the trigger removes the consequence while the goal still completes."""
    world = _world()
    pname = world.active_player
    player = world.get_player(pname)
    pnode_id = world.player_manager._player_node_id(pname)
    pnode = world.graph.get_node(pnode_id)

    # Goal without any trigger installed
    pnode.properties["triggers"] = []
    player.goals = goals.normalize([{
        "id": "become_chief",
        "what": "Become chief",
        "status": "active",
        "hoped_for": "Lead the tribe",
        "achieve": ["flag:elected_chief"],
    }])
    player.goal_log = []
    player.flags = {"elected_chief": True}

    world.tick_turn()

    # Goal completes
    assert player.goals[0]["status"] == "reached"

    # But no item was granted
    from graph import EDGE_CARRYING
    carried = [
        world.graph.get_node(e.source)
        for e in world.graph.get_edges_for_target(pnode_id, EDGE_CARRYING)
    ]
    staff_nodes = [n for n in carried if n and "staff" in (n.name or "").lower()]
    assert len(staff_nodes) == 0
