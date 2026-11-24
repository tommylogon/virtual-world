"""End-to-end tests for Scenario Timeline, Branching, StreamStore Lineage, and Time-Locking.

Covers bug-609, task-1005, task-1006, and task-1007 against a real Flask + VirtualWorld
instance (not synthetic stub dicts).
"""
from __future__ import annotations

from app import create_app
from engine.agent.prompt_builder import (
    build_result_reaction_messages,
    build_think_decide_messages,
)
from engine.stream_store import StreamStore


def _make_test_app(tmp_path):
    app = create_app({"TESTING": True})
    app.stream_store = StreamStore(str(tmp_path / "stream_e2e.db"))
    return app


def test_real_virtualworld_branch_fork_switch_and_redo_restores_state(tmp_path):
    app = _make_test_app(tmp_path)
    client = app.test_client()
    world = app.world
    player_name = next(iter(world.players.keys()))
    start_area = world.players[player_name].current_area

    # Seed initial Tick-0 checkpoint via /api/timeline/branches
    br_resp = client.get("/api/timeline/branches")
    assert br_resp.status_code == 200
    assert br_resp.get_json()["active_branch_id"] == "main"

    # Mutate live world at Tick 3 (move area, add memory + hearing, record checkpoint)
    world.time_ticks = 3
    other_areas = [
        n.name for n in world.graph.nodes.values()
        if getattr(n, "type", None) == "area" and n.name != start_area
    ]
    moved_area = other_areas[0] if other_areas else start_area
    world.players[player_name].current_area = moved_area
    world.players[player_name].memories.append({
        "id": "mem_future_t3",
        "text": "Discovered secret passage at tick 3.",
        "tick": 3,
        "source": "thought",
    })
    world.players[player_name].recent_hearing.append({
        "speaker": "Ghost",
        "text": "Leave this house",
        "tick": 3,
    })
    cp_resp = client.post("/api/timeline/checkpoint", json={"tick": 3})
    assert cp_resp.status_code == 200

    # Ensure checkpoint snapshot has zero recursive 'timeline' bloat
    snap_t3 = world.timeline_manager.branches["main"].checkpoints[3]
    assert "timeline" not in snap_t3
    assert "areas" not in snap_t3

    # Redo decision back at Tick 0 -> must restore real VirtualWorld state to Tick 0!
    app._agent_memory_manager = object()
    app._agent_plan_manager = object()
    redo_resp = client.post(
        "/api/timeline/redo",
        json={"character": player_name, "at_tick": 0},
    )
    assert redo_resp.status_code == 201
    redo_data = redo_resp.get_json()
    assert redo_data["restored"] is True
    assert redo_data["tick"] == 0
    redo_branch_id = redo_data["active_branch_id"]
    assert redo_branch_id != "main"

    # Live world was genuinely rewound and server agent caches cleared
    assert app.world.time_ticks == 0
    assert app.world.players[player_name].current_area == start_area
    assert all(m.get("id") != "mem_future_t3" for m in app.world.players[player_name].memories)
    assert app._agent_memory_manager is None
    assert app._agent_plan_manager is None

    # Switch back to 'main' -> must restore Tick 3 state intact!
    sw_resp = client.post("/api/timeline/switch", json={"branch_id": "main", "restore": True})
    assert sw_resp.status_code == 200
    sw_data = sw_resp.get_json()
    assert sw_data["restored"] is True
    assert sw_data["tick"] == 3
    assert app.world.time_ticks == 3
    assert app.world.players[player_name].current_area == moved_area
    assert any(m.get("id") == "mem_future_t3" for m in app.world.players[player_name].memories)


def test_stream_store_branch_lineage_and_non_destructive_batch_sync(tmp_path):
    app = _make_test_app(tmp_path)
    client = app.test_client()
    wid = "mansion"
    app.world._scenario_name = wid

    # Record main timeline events at ticks 0, 1, 2, 3
    for tick, text in [
        (0, "Entered foyer"),
        (1, "Walked into library"),
        (2, "Main branch: opened diary"),
        (3, "Main branch: took iron key"),
    ]:
        r = client.post(
            "/api/stream",
            json={
                "world_id": wid,
                "branch_id": "main",
                "kind": "action",
                "actor": "elena vance",
                "tick": tick,
                "payload": {"type": "action", "actor": "elena vance", "tick": tick, "text": text},
            },
        )
        assert r.status_code == 201

    # Fork branch_a at tick 1
    app.world.time_ticks = 1
    client.post("/api/timeline/checkpoint", json={"tick": 1})
    fork_resp = client.post(
        "/api/timeline/fork",
        json={"label": "Alt Path", "fork_tick": 1, "switch": True},
    )
    assert fork_resp.status_code == 201
    branch_a = fork_resp.get_json()["active_branch_id"]

    # Simulate browser StreamPersistence.persist() on branch_a sending inherited main rows
    # PLUS new branch_a rows with replace=True -> must NOT wipe main or duplicate ticks 0..1!
    batch_resp = client.post(
        "/api/stream/batch",
        json={
            "world_id": wid,
            "branch_id": branch_a,
            "replace": True,
            "from_tick": 1,
            "events": [
                {"kind": "action", "actor": "elena vance", "tick": 0, "branch_id": "main", "payload": {"text": "Entered foyer"}},
                {"kind": "action", "actor": "elena vance", "tick": 1, "branch_id": "main", "payload": {"text": "Walked into library"}},
                {"kind": "action", "actor": "elena vance", "tick": 2, "branch_id": branch_a, "payload": {"text": "Alt branch: slid bookcase open"}},
            ],
        },
    )
    assert batch_resp.status_code == 201
    assert batch_resp.get_json()["count"] == 1  # only branch_a's own row inserted

    # Querying branch_a walks ancestry: gets main ticks 0..1 + branch_a tick 2 (NO main ticks 2..3!)
    a_events = client.get(f"/api/stream?world_id={wid}&branch_id={branch_a}").get_json()["events"]
    a_texts = [e["payload"]["text"] for e in a_events]
    assert a_texts == [
        "Entered foyer",
        "Walked into library",
        "Alt branch: slid bookcase open",
    ]

    # Querying main still has ALL 4 main events untouched and ZERO branch_a contamination!
    m_events = client.get(f"/api/stream?world_id={wid}&branch_id=main").get_json()["events"]
    m_texts = [e["payload"]["text"] for e in m_events]
    assert m_texts == [
        "Entered foyer",
        "Walked into library",
        "Main branch: opened diary",
        "Main branch: took iron key",
    ]

    # Querying with tick_to=1 strictly prunes future events
    rewound_events = client.get(f"/api/stream?world_id={wid}&branch_id=main&tick_to=1").get_json()["events"]
    assert [e["payload"]["text"] for e in rewound_events] == [
        "Entered foyer",
        "Walked into library",
    ]


def test_time_locking_across_prompts_hearing_and_connected_commons(tmp_path):
    app = _make_test_app(tmp_path)
    client = app.test_client()
    world = app.world
    player_name = next(iter(world.players.keys()))
    player = world.players[player_name]

    world.set_game_date(day=10, month=5, year=2026)
    world.time_ticks = 2
    player.memories.append({"id": "past_mem", "text": "Found tarnished locket at tick 1.", "tick": 1, "source": "thought"})
    player.memories.append({"id": "future_mem", "text": "SPOILER from tick 25!", "tick": 25, "source": "thought"})
    player.recent_hearing.append({"speaker": "Miki", "text": "Past whisper at tick 2", "tick": 2})
    player.recent_hearing.append({"speaker": "Miki", "text": "FUTURE shout at tick 30", "tick": 30})

    think_msgs = build_think_decide_messages(world, player_name)
    user_prompt = think_msgs[1]["content"]
    assert "Found tarnished locket at tick 1." in user_prompt
    assert "Past whisper at tick 2" in user_prompt
    assert "SPOILER from tick 25!" not in user_prompt
    assert "FUTURE shout at tick 30" not in user_prompt

    react_msgs = build_result_reaction_messages(world, player_name, what_happened="You look around.")
    assert "SPOILER from tick 25!" not in react_msgs[1]["content"]
    assert "FUTURE shout at tick 30" not in react_msgs[1]["content"]

    # Connected-mode Commons time-locking by tick and world_datetime
    world.commons.post_message("User", "Hello at tick 2", tick=2, world_datetime=world.datetime_for_tick(2))
    world.commons.post_message("User", "Future leak at tick 50", tick=50, world_datetime=world.datetime_for_tick(50))

    cm_resp = client.get("/api/commons/messages?as=User")
    assert cm_resp.status_code == 200
    cm_texts = [m["text"] for m in cm_resp.get_json()["messages"]]
    assert "Hello at tick 2" in cm_texts
    assert "Future leak at tick 50" not in cm_texts
