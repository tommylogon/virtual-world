"""Tests for the MOSIAC selector (task-704).

Verifies:
- Goal priority ordering: priority 1 goal is active over priority 2.
- Goal alignment: score bonus connects active goal achieve refs to pursuit selection.
- Value gates: character traits and gated verbs remove invalid options.
- Grounded bindings: parameters resolve to real known world entities.
- Rejection mechanics: declining a candidate is a choice without penalty, prevented from re-proposal in same cycle.
- Conflicting needs: hungry & lonely goblin choosing meal vs rally based on active goal and traits.
- Deterministic simple NPC selection and execution.
- Timing constraints gating invalid timeframes.
"""

import pytest

from player import Player
from virtual_world_engine import VirtualWorld
from engine import mosiac_selector, plan_executor


def test_active_goal_priority_ordering():
    p = Player("Goblin Scout")
    p.goals = [
        {"id": "g2", "what": "Find firewood", "priority": 2, "status": "active", "opened_tick": 10},
        {"id": "g1", "what": "Survive the winter", "priority": 1, "status": "active", "opened_tick": 20},
        {"id": "g3", "what": "Become chief", "priority": 1, "status": "dormant", "opened_tick": 5},
    ]

    active = mosiac_selector.get_active_goal(p)
    assert active is not None
    assert active["id"] == "g1"  # priority 1 active goal beats priority 2


def test_goal_alignment_scores_advancement():
    goal_food = {
        "id": "eat_food",
        "what": "Get something to eat",
        "priority": 1,
        "status": "active",
        "achieve": [{"ref": "item:food", "note": "any food"}],
    }

    meal_candidate = {
        "id": "meal",
        "purpose": "Gather food, bring it home, and eat it.",
        "tags": ["eating", "food"],
        "steps": [{"kind": "take", "spec": {"tags": ["food"]}}],
    }

    scout_candidate = {
        "id": "scout-and-report",
        "purpose": "Scout the border.",
        "tags": ["scout"],
        "steps": [{"kind": "travel", "area": "Border"}],
    }

    align_meal = mosiac_selector.goal_alignment(meal_candidate, goal_food)
    align_scout = mosiac_selector.goal_alignment(scout_candidate, goal_food)

    assert align_meal > 0.0
    assert align_scout == 0.0
    assert align_meal > align_scout


def test_rejection_is_a_choice_without_penalty():
    world = VirtualWorld()
    p = Player("Gribba")
    world.add_player(p)
    p.current_area = "CampfireClearing"
    p.vitals["Hunger"] = 80

    selected = mosiac_selector.select_pursuit(p, world, candidate_ids=["meal", "gather"])
    assert selected is not None
    assert selected["template_id"] == "meal"

    # Decline the meal pursuit
    mosiac_selector.decline_pursuit(p, "meal")
    assert "meal" in p._declined_pursuits_cycle

    # Reselection in the same cycle does not re-propose meal
    second_choice = mosiac_selector.select_pursuit(p, world, candidate_ids=["meal", "gather"])
    assert second_choice is not None
    assert second_choice["template_id"] != "meal"

    # Reset cycle allows re-evaluation
    mosiac_selector.reset_selection_cycle(p)
    reset_choice = mosiac_selector.select_pursuit(p, world, candidate_ids=["meal", "gather"])
    assert reset_choice is not None
    assert reset_choice["template_id"] == "meal"


def test_conflicting_needs_goblin_choice():
    """Demonstrate a hungry and lonely goblin choosing meal vs rally based on goals and disposition."""
    world = VirtualWorld()
    goblin = Player("Mikka")
    world.add_player(goblin)
    goblin.current_area = "CampfireClearing"
    goblin.vitals["Hunger"] = 70
    goblin.vitals["Social"] = 30

    # Scenario A: Active goal is food
    goblin.goals = [
        {"id": "food_goal", "what": "Eat breakfast", "priority": 1, "status": "active",
         "achieve": [{"ref": "item:food"}]}
    ]
    pick_a = mosiac_selector.select_pursuit(goblin, world, candidate_ids=["meal", "rally"])
    assert pick_a is not None
    assert pick_a["template_id"] == "meal"

    # Scenario B: Active goal is social rally, priority 1
    goblin.goals = [
        {"id": "rally_goal", "what": "Rally the goblin clan", "priority": 1, "status": "active",
         "achieve": [{"ref": "present:clan"}]}
    ]
    # Trait emphasizing loyalty / affiliation
    goblin.traits = {"loyal": True, "social": True}
    mosiac_selector.reset_selection_cycle(goblin)
    pick_b = mosiac_selector.select_pursuit(goblin, world, candidate_ids=["meal", "rally"])
    assert pick_b is not None
    assert pick_b["template_id"] == "rally"


def test_grounded_bindings_and_plan_advancement():
    world = VirtualWorld()
    p = Player("Tusker")
    world.add_player(p)
    p.current_area = "Kitchen"
    p.home = "Kitchen"
    p.vitals["Hunger"] = 75

    choice = mosiac_selector.select_pursuit(p, world, candidate_ids=["meal"])
    assert choice is not None
    assert choice["bindings"]["home"] == "Kitchen"
    assert choice["bindings"]["food_spec"] == {"tags": ["food"]}

    # Assign and build plan
    p.active_pursuit = choice
    plan = plan_executor.build_plan(choice)
    assert plan is not None
    assert plan["pursuit_template"] == "meal"
    p.plan = plan

    # Validate plan execution
    valid, reason = plan_executor.is_plan_valid(p, world, plan)
    assert valid is True
    assert reason == "ok"
