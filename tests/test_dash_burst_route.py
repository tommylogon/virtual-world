"""The dash burst through the action route (task-784).

`apply_action_gate` is unit-tested in test_dash_burst.py; this pins the WIRING:
a submitted dash arms the burst, a non-finish is refused while it is armed, and
the finish spends the minor and clears it. `enforce_slots` is what the human
composer and the agent submit both send.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _setup():
    from app import create_app
    from area import Area
    from player import Player
    app = create_app({"TESTING": True})
    w = app.world
    w.movement.add_area(Area("Dash A", "start", ["exterior"]))
    w.movement.add_area(Area("Dash B", "next", ["exterior"]))
    w.movement.add_area(Area("Dash C", "far", ["exterior"]))
    w.movement.connect_areas("Dash A", "Dash B", "north", "south", state="open")
    w.movement.connect_areas("Dash B", "Dash C", "north", "south", state="open")
    p = Player("Dasher")
    w.add_player(p)
    w.players[p.name].current_area = "Dash A"
    w.set_player_area(p.name, "Dash A")
    w.player_manager.active_player = p.name
    return app, w, p


def _post(client, command):
    return client.post(
        "/api/action",
        json={"character": "Dasher", "command": command, "enforce_slots": True},
    ).get_json()


def test_a_dash_arms_the_burst_and_only_the_finish_may_follow():
    from engine import action_tiers as at
    app, w, p = _setup()
    p.turn_slots = dict(at.DEFAULT_BUDGET)
    client = app.test_client()

    first = _post(client, "dash north")
    assert first.get("success") is not False, first
    assert p.current_area == "Dash B", p.current_area
    assert p.burst_pending == 1, "the dash did not arm the burst"
    assert p.turn_slots["major"] == 0 and p.turn_slots["minor"] == 1, p.turn_slots

    blocked = _post(client, "look")
    assert blocked.get("success") is False or blocked.get("error"), blocked
    assert p.burst_pending == 1, "a refused action must not clear the burst"
    assert p.turn_slots["minor"] == 1

    finish = _post(client, "go north")
    assert finish.get("success") is not False, finish
    assert p.current_area == "Dash C", p.current_area
    assert p.turn_slots["minor"] == 0, p.turn_slots
    assert p.burst_pending == 0, "the finish did not clear the burst"


def test_a_dash_without_the_minor_is_refused():
    from engine import action_tiers as at
    app, w, p = _setup()
    p.turn_slots = dict(at.DEFAULT_BUDGET)
    p.turn_slots["minor"] = 0        # nothing to finish with
    client = app.test_client()

    resp = _post(client, "dash north")
    assert resp.get("success") is False or resp.get("error"), resp
    assert p.current_area == "Dash A", "a refused dash must not move the character"
    assert p.burst_pending == 0
    assert p.turn_slots["major"] == 1, "a refused dash must not spend the major"


def test_successful_go_spends_only_the_major_slot():
    from engine import action_tiers as at
    app, w, p = _setup()
    p.turn_slots = dict(at.DEFAULT_BUDGET)
    client = app.test_client()

    result = _post(client, "go north")

    assert result.get("success") is not False, result
    assert p.current_area == "Dash B", p.current_area
    expected = {"major": 0, "minor": 1, "free": 3, "activity": 1}
    assert p.turn_slots == expected, p.turn_slots
    state = client.get("/api/state").get_json()
    assert state["players"]["Dasher"]["turn_slots"] == expected
