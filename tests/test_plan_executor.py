"""Tests for short-term plan executor runtime (task-702).

Verifies:
- Typed short-term plans advance for any character (LLM agent, simple NPC, background).
- Precondition validation and invalidation on broken world state.
- Pursuit survives interruption; needs preempt plan without erasing pursuit.
- Activity steps call ActivitySystem, bind specific bed, and expose graph relations.
- Full fisherman day micro-scenario (travel, fish to quota, return home, sleep on bed).
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Edge, Node, EDGE_CARRYING, EDGE_IN
from player import Player
from area import Area
from virtual_world_engine import VirtualWorld
from engine import plan_executor


def _world():
    world = VirtualWorld()
    world.time_per_tick_minutes = 1
    return world


def _add_area(world, name):
    area = Area(name, f"Description for {name}.", [])
    world.movement.add_area(area)
    return world.area_node_id(name)


def _connect(world, a, b):
    world.movement.connect_areas(a, b, "north", "south", "open")


def _add_item(world, area_name, name, tags, item_id=None):
    area_id = world.area_node_id(area_name)
    node = Node(
        id=item_id or f"item_{name.lower().replace(' ', '_')}",
        type="item",
        name=name,
        properties={"name": name, "tags": list(tags), "weight": 1.0, "uses": -1}
    )
    world.graph.add_node(node)
    world.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
    return node


def _make_player(world, name, area_name):
    p = Player(name)
    world.add_player(p)
    world.set_player_area(name, area_name)
    p.current_area = area_name
    for stat, val in {
        "Hunger": 10, "Thirst": 10, "Energy": 90, "Bladder": 0,
        "Hygiene": 100, "Sanity": 100, "Entertainment": 100, "Social": 100,
    }.items():
        p.vitals[stat] = val
    return p


def _assign(p, label, template, **bindings):
    p.active_pursuit = {
        "assignment_id": f"pursuit_{label}",
        "template_id": template,
        "label": label,
        "reason": f"pursuing {label}",
        "bindings": dict(bindings),
        "step_index": 0,
        "repeat": False,
    }
    return p.active_pursuit


def test_plan_advances_directly_on_world():
    """Executor advances typed plans directly on VirtualWorld without external sim wrapper."""
    world = _world()
    _add_area(world, "Storage")
    _add_area(world, "Workshop")
    _connect(world, "Storage", "Workshop")

    player = _make_player(world, "Worker", "Storage")
    item = _add_item(world, "Storage", "Iron Bar", ["metal", "bar"], "item_iron_bar")
    _assign(player, "move_bar", "haul", source="Storage", item="bar", sink="Workshop")

    # First advance: starts pursuit and takes item
    res = plan_executor.advance_plan(world, player)
    assert player.plan is not None
    assert player.plan["label"] == "move_bar"

    # Advance until done
    for _ in range(20):
        plan_executor.advance_plan(world, player)
        if player.plan is None:
            break

    # Item should be in Workshop
    workshop_id = world.area_node_id("Workshop")
    in_workshop = any(e.source == item.id and e.target == workshop_id and e.type == EDGE_IN
                      for e in world.graph.edges)
    assert in_workshop is True
    assert player.plan is None
    assert "pursuit_move_bar" in player.completed_pursuits


def test_invalid_step_precondition_aborts_plan_and_logs_failure():
    """A broken precondition (missing destination, missing item) fails the plan cleanly."""
    world = _world()
    _add_area(world, "Storage")
    player = _make_player(world, "Broken", "Storage")

    # Target item does not exist at Storage
    _assign(player, "take_ghost", "haul", source="Storage", item="nonexistent", sink="Storage")
    plan_executor.advance_plan(world, player)

    whys = [e.get("why") for e in player.lived_log]
    assert "plan:take_ghost:failed" in whys
    assert player.plan is None


def test_survival_need_preempts_plan_without_losing_pursuit():
    """Critical hunger/thirst preempts plan execution while preserving active_pursuit."""
    world = _world()
    _add_area(world, "Camp")
    _add_area(world, "Field")
    _connect(world, "Camp", "Field")
    player = _make_player(world, "HungryWorker", "Camp")
    _add_item(world, "Camp", "Box", ["crate"], "item_box")
    _assign(player, "carry_box", "haul", source="Camp", item="crate", sink="Field")

    # Start the plan
    plan_executor.advance_plan(world, player)
    assert player.plan is not None

    # Inject critical hunger
    player.vitals["Hunger"] = 90
    used = plan_executor.advance_plan(world, player)
    assert used is None
    assert player.plan is not None
    assert player.active_pursuit is not None

    # Satisfy hunger and resume
    player.vitals["Hunger"] = 10
    plan_executor.advance_plan(world, player)
    for _ in range(20):
        plan_executor.advance_plan(world, player)
        if player.plan is None:
            break
    assert "pursuit_carry_box" in player.completed_pursuits


def test_sleep_activity_binds_bed_spatial_relation_in_graph():
    """Sleeping with a bound bed creates an 'on' edge in the graph, removed on waking."""
    world = _world()
    _add_area(world, "Bedroom")
    player = _make_player(world, "Sleeper", "Bedroom")
    bed = _add_item(world, "Bedroom", "Wooden Bed", ["furniture", "bed"], "item_wooden_bed")

    _assign(player, "rest_time", "sleep-at-venue", venue="Bedroom", bed_id=bed.id)

    # Advance plan: reaches Bedroom and starts sleeping
    plan_executor.advance_plan(world, player)
    assert player.activity is not None
    assert player.activity["type"] == "sleeping"
    assert player.activity["target_item"] == bed.id

    # Check graph edge: player node has 'on' edge to bed node
    player_id = world._player_node_id(player.name)
    on_edges = [e for e in world.graph.get_edges_for_source(player_id, "on") if e.target == bed.id]
    assert len(on_edges) == 1, "Graph must reflect player 'on' the bed during sleep"

    # Waking clears activity and unbinds graph relation
    world.activities.wake(player.name)
    assert player.activity is None
    plan_executor.finish_plan(world, player, player.plan, "done")
    on_edges_after = [e for e in world.graph.get_edges_for_source(player_id, "on") if e.target == bed.id]
    assert len(on_edges_after) == 0, "Graph relation must be removed when sleep ends"


def test_fisherman_day_micro_scenario():
    """Full micro-scenario demonstrating a complete fisherman day:

    1. Fish until quota: James leaves Fisherman's Hut, travels to Lake Shore,
       fishes until catch count reaches target, and returns home.
    2. Pursue sleep: James travels to Fisherman's Hut, sleeps on his bed,
       exposing the graph relation, and finishes when rested.
    """
    world = _world()
    hut = _add_area(world, "Fisherman's Hut")
    lake = _add_area(world, "Lake Shore")
    _connect(world, "Fisherman's Hut", "Lake Shore")

    # Add bed in the hut
    bed = _add_item(world, "Fisherman's Hut", "Bunk Bed", ["furniture", "bed"], "item_bunk_bed")
    james = _make_player(world, "James", "Fisherman's Hut")

    # ── Phase 1: Fish and bring home ──
    _assign(james, "morning_fishing", "fish-and-bring-home",
            home="Fisherman's Hut", fishing_place="Lake Shore")

    # Step 1: Travel to Lake Shore
    plan_executor.advance_plan(world, james)
    assert james.current_area == "Lake Shore"
    assert james.plan["index"] == 1

    # Step 2: Start fishing activity at Lake Shore
    plan_executor.advance_plan(world, james)
    assert james.activity is not None
    assert james.activity["type"] == "fishing"
    assert james.activity["catch_count_target"] == 10

    # Simulate fishing catches over time
    james.activity["catch_count"] = 10
    world.activities.end_activity(james.name, reason="quota_reached")
    james._last_completed_activity_type = "fishing"

    # Step 3: Return home
    plan_executor.advance_plan(world, james)
    assert james.current_area == "Fisherman's Hut"
    assert "pursuit_morning_fishing" in james.completed_pursuits
    assert james.plan is None

    # ── Phase 2: Sleep at venue ──
    james.vitals["Energy"] = 10
    _assign(james, "night_sleep", "sleep-at-venue",
            venue="Fisherman's Hut", bed_id=bed.id)

    plan_executor.advance_plan(world, james)
    assert james.activity is not None
    assert james.activity["type"] == "sleeping"
    assert james.activity["target_item"] == bed.id

    # Verify witness relation in graph
    james_node_id = world._player_node_id("James")
    bed_edges = [e for e in world.graph.get_edges_for_source(james_node_id, "on") if e.target == bed.id]
    assert len(bed_edges) == 1

    # Wake up rested
    james.vitals["Energy"] = 100
    world.activities.wake(james.name)
    plan_executor.finish_plan(world, james, james.plan, "done")
    assert "pursuit_night_sleep" in james.completed_pursuits
    assert len(list(world.graph.get_edges_for_source(james_node_id, "on"))) == 0
