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

    client.post("/api/action", json={"command": "goal set Become chief", "character": name})
    assert app.world.get_player(name).goals == [
        {"id": "become_chief", "what": "Become chief", "status": "active"}]

    client.post("/api/action", json={"command": "goal complete become_chief", "character": name})
    assert app.world.get_player(name).goals[0]["status"] == "reached"

    client.post("/api/action", json={"command": "goal drop become_chief", "character": name})
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

    client.post("/api/action", json={"command": "goal set Hold the gate", "character": name})
    client.post("/api/action", json={"command": "goal complete hold_the_gate", "character": name})

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
                        "intention": "obligation to Elder Mara"}]


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
    client.post("/api/action", json={"command": "obligation accept fetch_water", "character": name})
    player = app.world.get_player(name)
    assert player.obligations[0]["status"] == "accepted"
    assert any(g["id"] == "fetch_water" for g in player.goals)
