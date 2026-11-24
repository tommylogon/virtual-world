"""End-to-end tests for all 6 remaining Timeline Vision pieces (task-1008..task-1013).

Tests:
1. SQLite TimelineStore compressed checkpoint persistence & hydration across restarts (task-1008).
2. Authored Entity Existence Windows (exists_from / exists_until) across room prompts, ticks, and /api/state (task-1009).
3. Pre-start prequel expansion (/api/timeline/expand-past) & past-to-future branch connection (/api/timeline/connect) (task-1010).
4. Unified Connected-mode Commons branching on world.timeline_manager vs isolated Standalone mode (task-1011).
5. Fork & Soak (/api/timeline/fork-soak) recording periodic checkpoints & branch-scoped StreamStore milestones (task-1012).
"""
from __future__ import annotations

from app import create_app
from engine.agent.prompt_builder.room_context import build_room_context
from engine.stream_store import StreamStore
from engine.timeline import TimelineManager
from engine.timeline_store import TimelineStore


def _make_app(tmp_path):
    app = create_app({"TESTING": True})
    app.stream_store = StreamStore(str(tmp_path / "stream.db"))
    app.timeline_store = TimelineStore(str(tmp_path / "timeline.db"))
    app.world._scenario_name = "vision_test"
    return app


def test_sqlite_timeline_store_persists_and_hydrates_across_restarts(tmp_path):
    db_path = str(tmp_path / "tl_persist.db")
    store1 = TimelineStore(db_path)
    tm1 = TimelineManager(store=store1, world_id="millwood")
    tm1.record_checkpoint(0, {"time_ticks": 0, "marker": "may_start"}, branch_id="main")
    b = tm1.fork_branch(label="August Alt", fork_tick=0, snapshot={"time_ticks": 50, "marker": "aug_alt"}, switch=True)
    tm1.record_checkpoint(50, {"time_ticks": 50, "marker": "aug_alt_50"}, branch_id=b.branch_id)
    store1.close()

    # Simulate server restart with a fresh TimelineManager attaching to the same SQLite DB
    store2 = TimelineStore(db_path)
    tm2 = TimelineManager()
    tm2.attach_store(store2, "millwood", hydrate=True)
    assert tm2.active_branch_id == b.branch_id
    assert set(tm2.branches.keys()) == {"main", b.branch_id}
    restored = tm2._find_checkpoint_at_or_before(b.branch_id, 50)
    assert restored is not None and restored["marker"] == "aug_alt_50"
    main_cp = tm2._find_checkpoint_at_or_before("main", 0)
    assert main_cp is not None and main_cp["marker"] == "may_start"
    store2.close()


def test_entity_existence_windows_phase_characters_and_items_in_and_out(tmp_path):
    app = _make_app(tmp_path)
    client = app.test_client()
    world = app.world
    world.set_game_date(day=15, month=5, year=2026)  # May 15, 2026

    pnames = list(world.players.keys())
    p0 = world.players[pnames[0]]
    area = p0.current_area

    # Pick an item node in p0's area (or attach one) and give it exists_from = 2026-08-01
    from graph import Edge, Node
    aid = world.graph.area_of(world.player_manager.player_node_id(pnames[0]))
    future_item = Node(
        id="item_aug_relic",
        type="item",
        name="august_relic",
        properties={
            "description": "A relic that only arrives in August.",
            "exists_from": "2026-08-01",
        },
    )
    world.graph.add_node(future_item)
    world.graph.add_edge(Edge(source="item_aug_relic", target=aid, type="in"))

    # In May 2026: august_relic must NOT appear in room prompt and must have exists_now=False in /api/state
    ctx_may = build_room_context(world, p0)
    assert "august_relic" not in ctx_may
    st_may = client.get("/api/state").get_json()
    assert st_may["graph"]["nodes"]["item_aug_relic"]["exists_now"] is False

    # Jump to Sept 1, 2026: august_relic MUST appear in room prompt and have exists_now=True
    world.set_game_date(day=1, month=9, year=2026)
    ctx_sep = build_room_context(world, p0)
    assert "august_relic" in ctx_sep
    st_sep = client.get("/api/state").get_json()
    assert st_sep["graph"]["nodes"]["item_aug_relic"]["exists_now"] is True

    # Verify TickManager skips characters outside their existence window
    p0.exists_from = "2026-10-01"
    energy_before = p0.vitals.get("Energy", 100)
    world.tick_manager.tick_turn(skip_npcs=True)
    assert p0.vitals.get("Energy", 100) == energy_before


def test_prequel_expand_past_and_connect_branches(tmp_path):
    app = _make_app(tmp_path)
    client = app.test_client()
    world = app.world
    world.time_per_tick_minutes = 60  # 24 ticks per day for fast math
    world.set_game_date(day=1, month=10, year=2026)  # Oct 1, 2026 at tick 0
    dt_before = world.datetime_for_tick()

    pname = next(iter(world.players.keys()))
    world.players[pname].memories.append({"id": "oct_mem", "text": "Arrived in October.", "tick": 0, "source": "thought"})
    client.post("/api/stream", json={"world_id": "vision_test", "branch_id": "main", "kind": "action", "actor": pname, "tick": 0, "payload": {"text": "Oct start"}})

    # Expand 30 days earlier (opens Sept 1 .. Oct 1 before old Tick 0)
    exp_resp = client.post("/api/timeline/expand-past", json={"delta_days": 30})
    assert exp_resp.status_code == 200
    exp_data = exp_resp.get_json()
    assert exp_data["ok"] is True
    assert exp_data["delta_days"] == 30
    assert exp_data["delta_ticks"] == 30 * 24
    # Existing world datetime stays pinned to exact same calendar date!
    assert world.datetime_for_tick() == dt_before
    # StreamStore event tick was shifted cleanly
    stream_evts = client.get("/api/stream?world_id=vision_test&branch_id=main").get_json()["events"]
    assert stream_evts[0]["tick"] == 30 * 24

    # Record Oct checkpoint on main, then fork a prequel branch and add a prequel memory
    client.post("/api/timeline/checkpoint", json={"tick": world.time_ticks})
    fork_resp = client.post("/api/timeline/fork", json={"label": "May Prequel", "fork_tick": world.time_ticks, "switch": True})
    prequel_id = fork_resp.get_json()["active_branch_id"]
    world.players[pname].memories.append({"id": "prequel_mem", "text": "Met mysterious stranger in May.", "tick": 5, "source": "thought"})
    client.post("/api/timeline/checkpoint", json={"tick": world.time_ticks})

    # Connect prequel -> main into a brand new branch (leaving both source & target intact)
    conn_resp = client.post("/api/timeline/connect", json={"source_branch_id": prequel_id, "target_branch_id": "main", "label": "Connected Canon"})
    assert conn_resp.status_code == 201
    conn_data = conn_resp.get_json()
    assert conn_data["ok"] is True
    assert conn_data["merged_memories"] >= 1
    assert any(m.get("id") == "prequel_mem" for m in app.world.players[pname].memories)
    assert any(m.get("id") == "oct_mem" for m in app.world.players[pname].memories)


def test_unified_connected_commons_branching_and_fork_soak(tmp_path):
    app = _make_app(tmp_path)
    client = app.test_client()
    world = app.world
    world.time_per_tick_minutes = 60

    # Connected mode Commons (default use_viwo_state=True) shares world.timeline_manager
    world.commons.post_message("User", "Main branch message", tick=0)
    f_resp = client.post("/api/commons/branches", json={"name": "Commons Alt"})
    assert f_resp.status_code == 201
    alt_bid = f_resp.get_json()["active_branch_id"]
    assert alt_bid == world.timeline_manager.active_branch_id
    assert alt_bid != "main"

    # Post on Commons Alt, then switch back to main via /api/commons/branches/switch
    world.commons.post_message("User", "Alt branch only message", tick=1)
    sw_resp = client.post("/api/commons/branches/switch", json={"branch_id": "main"})
    assert sw_resp.status_code == 200
    assert world.timeline_manager.active_branch_id == "main"
    main_texts = [m["text"] for m in world.commons.messages]
    assert "Main branch message" in main_texts
    assert "Alt branch only message" not in main_texts

    # Fork & Soak 12 hours directly into an isolated timeline branch
    tick_before = world.time_ticks
    soak_resp = client.post(
        "/api/timeline/fork-soak",
        json={"hours": 12, "checkpoint_every_minutes": 360, "label": "12h Soak"},
    )
    assert soak_resp.status_code == 201
    sdata = soak_resp.get_json()
    assert sdata["ok"] is True
    assert sdata["active_branch_id"] != "main"
    assert sdata["checkpoints_recorded"] >= 2
    assert sdata["tick"] > tick_before
    # StreamStore recorded soak milestones under the new branch_id
    soak_evts = client.get(f"/api/stream?world_id=vision_test&branch_id={sdata['active_branch_id']}").get_json()["events"]
    assert any("[Soak checkpoint" in (e.get("payload") or {}).get("text", "") for e in soak_evts)
