"""Plan executor runtime for character pursuits (task-702).

@module plan_executor
@contributes unified short-term plan execution for LLM agents, simple NPCs, and background characters
@docs docs/virtualWorld/design/Character Pursuits.md

Executes grounded short-term plans that make progress on an actor's active pursuit.
- The pursuit is the longer undertaking and motive (Player.active_pursuit).
- The plan is the current grounded approach (Player.plan).
- An Activity is the observable process running over time (Player.activity).

Uses one set of world rules for LLM agents, simple NPCs, and background characters.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from graph import Edge, EDGE_CARRYING, EDGE_IN
from engine.lived_log import record
from engine.plan_steps import STEP_KINDS, is_binding

logger = logging.getLogger(__name__)

TRAVEL_MINUTES = 1
TAKE_MINUTES = 2

_SPATIAL_RELATIONS = ("in", "on", "under", "behind", "beside", "at")


def _resolve_context(world_or_sim) -> Tuple[Any, Any]:
    """Resolve (sim, gs) regardless of whether BackgroundSimulation or World is passed."""
    if hasattr(world_or_sim, "gs"):
        return world_or_sim, world_or_sim.gs
    gs = world_or_sim
    from engine.background_simulation import BackgroundSimulation
    sim = getattr(gs, "_background_sim", None)
    if sim is None:
        sim = BackgroundSimulation(gs)
        try:
            gs._background_sim = sim
        except Exception:
            pass
    return sim, gs


# ───────────────────────────── building ─────────────────────────────────────

def build_plan(pursuit: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build the current short-term plan for a character's pursuit assignment.

    *pursuit* is the character-side Player.active_pursuit dict: it carries the
    template id, the bindings, and the reason. No graph node is involved - the
    assignment is the character's own data.
    """
    if not isinstance(pursuit, dict):
        return None
    template_id = str(pursuit.get("template_id") or "").strip().lower()
    from engine import pursuit_templates
    instance = pursuit_templates.bind(template_id, pursuit.get("bindings"))
    if (instance and pursuit.get("template_version")
            and instance["template_version"] != pursuit["template_version"]):
        return None
    if instance is None:
        return None
    label = str(pursuit.get("label") or template_id or "pursuit")
    plan = {
        "assignment_id": pursuit.get("assignment_id"),
        "pursuit_template": template_id,
        "template_version": instance["template_version"],
        "label": label,
        "purpose": instance["purpose"],
        "reason": str(pursuit.get("reason") or instance["purpose"]),
        "bindings": instance["bindings"],
        "index": 0,
        "steps": instance["steps"],
    }
    # Pass structured fields through to the live plan
    for key in ("requirements", "supplies", "timing", "progress",
                "stop_conditions", "duration", "recipe"):
        if key in instance:
            plan[key] = instance[key]
    return plan


# ───────────────────────────── matching ─────────────────────────────────────

def _match_item(node, spec: Dict[str, Any]) -> bool:
    if not spec:
        return True
    props = node.properties or {}
    tags = {str(t).lower() for t in (props.get("tags") or [])}
    want = {str(t).lower() for t in (spec.get("tags") or [])}
    if want and not (want & tags):
        return False
    name = spec.get("name")
    if name:
        needle = str(name).lower()
        if needle not in str(node.name or "").lower() and needle not in str(node.id or "").lower():
            return False
    return bool(want or name)


def _is_fixture(node) -> bool:
    props = node.properties or {}
    tags = {str(t).lower() for t in (props.get("tags") or [])}
    return "fixture" in tags


def _carried_matching(sim, player, spec: Dict[str, Any]):
    for node in sim._carried_nodes(player):
        if _match_item(node, spec):
            return node
    return None


def _in_area_matching(sim, player, spec: Dict[str, Any]):
    area_id = sim.gs.area_node_id(player.current_area) if player.current_area else None
    if not area_id:
        return None
    for node in sim._spatial_items(area_id):
        if _is_fixture(node):
            continue
        if _match_item(node, spec):
            return node
    return None


# ───────────────────────────── validation ───────────────────────────────────

def is_plan_valid(player, world_or_sim, plan: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if the plan's preconditions and current step remain grounded in the world.

    Returns (True, 'ok') or (False, reason). If false, the plan approach is invalidated.
    """
    if not plan or not isinstance(plan, dict):
        return False, "no plan"
    steps = plan.get("steps") or []
    idx = int(plan.get("index", 0) or 0)
    if idx >= len(steps):
        return True, "completed"

    sim, gs = _resolve_context(world_or_sim)

    # Check stop conditions
    for sc in plan.get("stop_conditions") or []:
        sctype = sc.get("type")
        if sctype == "vital_below":
            vital = str(sc.get("stat") or sc.get("vital") or "")
            thresh = float(sc.get("value") or sc.get("threshold") or 0)
            cur = float(getattr(player, "vitals", {}).get(vital, 100) or 100)
            if cur <= thresh:
                return False, f"stop condition triggered: {vital} <= {thresh}"
        elif sctype == "vital_above":
            vital = str(sc.get("stat") or sc.get("vital") or "")
            thresh = float(sc.get("value") or sc.get("threshold") or 0)
            cur = float(getattr(player, "vitals", {}).get(vital, 0) or 0)
            if cur >= thresh:
                return False, f"stop condition triggered: {vital} >= {thresh}"

    step = steps[idx]
    kind = step.get("kind")
    if kind not in STEP_KINDS:
        return False, f"unknown step kind: {kind}"

    if kind == "travel":
        target_area = step.get("area")
        if target_area:
            target_id = gs.area_node_id(target_area)
            if not target_id:
                return False, f"destination area '{target_area}' does not exist"
        else:
            tags = step.get("tags") or []
            if not sim._areas_with(tags):
                return False, f"no area matches destination tags {tags}"

    elif kind == "take":
        spec = step.get("spec") or {}
        # If not already carrying, check if reachable in current area or reachable on arrival
        if _carried_matching(sim, player, spec) is None:
            # If we are already at the target area, item must exist
            if _in_area_matching(sim, player, spec) is None:
                # Can only take if item exists in area
                return False, "target item not found in area"

    elif kind == "drop":
        spec = step.get("spec") or {}
        if _carried_matching(sim, player, spec) is None:
            return False, "item to drop is not carried"

    elif kind == "activity":
        want = str(step.get("activity") or "").strip().lower()
        from engine.activities_loader import get as get_activity_def
        if not get_activity_def(want):
            return False, f"activity definition '{want}' not found"

    return True, "ok"


# ───────────────────────────── satisfaction ─────────────────────────────────

def _check_activity_completion(activity: Optional[dict], condition: dict, player) -> bool:
    if not activity or not condition:
        return False
    ctype = condition.get("type")
    if ctype == "duration_elapsed":
        if activity.get("duration_minutes") is not None:
            return float(activity.get("elapsed_minutes", 0.0) or 0.0) >= float(activity["duration_minutes"])
        if activity.get("duration_ticks") is not None:
            return int(activity.get("elapsed_ticks", 0) or 0) >= int(activity["duration_ticks"])
        return False
    if ctype == "vital_full":
        vital = str(condition.get("vital") or "").strip()
        if not vital:
            return False
        return float(getattr(player, "vitals", {}).get(vital, 0) or 0) >= 100.0
    if ctype == "field_threshold":
        field = str(condition.get("field") or "").strip()
        if not field:
            return False
        value = condition.get("value")
        if value is None:
            param = condition.get("param")
            if param:
                value = activity.get(param)
        if value is None:
            return False
        try:
            return float(activity.get(field, 0) or 0) >= float(value)
        except (TypeError, ValueError):
            return False
    return False


def is_step_satisfied(world_or_sim, player, step: Dict[str, Any]) -> bool:
    """Check whether *step* is already satisfied for *player*."""
    sim, gs = _resolve_context(world_or_sim)
    kind = step.get("kind")

    if kind == "travel":
        if step.get("area"):
            return player.current_area == step["area"]
        return player.current_area in sim._areas_with(step.get("tags") or [])

    if kind == "take":
        return _carried_matching(sim, player, step.get("spec") or {}) is not None

    if kind == "drop":
        spec = step.get("spec") or {}
        carried = _carried_matching(sim, player, spec)
        return carried is None and _in_area_matching(sim, player, spec) is not None

    if kind == "activity":
        activity = getattr(player, "activity", None)
        want = str(step.get("activity") or "").strip().lower()
        if not want:
            return activity is None
        current_type = (activity or {}).get("type", "").lower()
        if current_type != want:
            last_type = getattr(player, "_last_completed_activity_type", None)
            if last_type and str(last_type).lower() == want:
                player._last_completed_activity_type = None
                return True
            return False
        catch_target = step.get("catch_count_target")
        if catch_target is not None:
            if int(activity.get("catch_count", 0) or 0) >= int(catch_target):
                return True
        if step.get("duration_minutes") is not None:
            if float(activity.get("elapsed_minutes", 0.0) or 0.0) >= float(step["duration_minutes"]):
                return True
        elif step.get("duration_ticks") is not None:
            if int(activity.get("elapsed_ticks", 0) or 0) >= int(step["duration_ticks"]):
                return True
        try:
            from engine.activities_loader import get as get_activity_def
            definition = get_activity_def(want) or {}
            for condition in definition.get("completion") or []:
                if _check_activity_completion(activity, condition, player):
                    return True
        except Exception:
            pass
        return False

    if kind == "wait":
        activity = getattr(player, "activity", None)
        if not activity:
            return True
        if step.get("duration_minutes") is not None:
            return float(activity.get("elapsed_minutes", 0.0) or 0.0) >= float(step["duration_minutes"])
        if step.get("duration_ticks") is not None:
            return int(activity.get("elapsed_ticks", 0) or 0) >= int(step["duration_ticks"])
        return True

    return True


# ───────────────────────────── execution ────────────────────────────────────

def _bind_activity_spatial_relation(gs, player, target_item: Optional[str], relation: str = "on"):
    """Bind a specific bed/fixture relation in the graph so witnesses see the character on it."""
    if not target_item or not gs or not hasattr(gs, "graph"):
        return
    player_id = gs._player_node_id(player.name) if hasattr(gs, "_player_node_id") else None
    if not player_id:
        return
    # Find target item node in area
    target_node = gs.graph.get_node(target_item)
    if not target_node:
        # Search by name in current area
        area_id = gs.area_node_id(player.current_area) if hasattr(gs, "area_node_id") else None
        if area_id:
            from engine.world_scopes import spatial_item_nodes
            for itm in spatial_item_nodes(gs.graph, area_id):
                if itm.name == target_item or itm.id == target_item:
                    target_node = itm
                    break
    if target_node:
        try:
            gs.graph.add_edge(Edge(source=player_id, target=target_node.id, type=relation))
        except Exception:
            pass


def _unbind_activity_spatial_relation(gs, player, relation: str = "on"):
    """Remove transient spatial relation edge on activity end."""
    if not gs or not hasattr(gs, "graph"):
        return
    player_id = gs._player_node_id(player.name) if hasattr(gs, "_player_node_id") else None
    if not player_id:
        return
    for edge in list(gs.graph.get_edges_for_source(player_id, relation)):
        gs.graph.remove_edge(edge.source, edge.target, edge.type)


def execute_step(world_or_sim, player, plan: Dict[str, Any], step: Dict[str, Any]) -> Any:
    """Run one step of the plan.

    Returns:
    - minutes_used (int/float) if progress made
    - None if step started an ongoing process or waiting
    - 'failed' if precondition broken or action impossible
    """
    sim, gs = _resolve_context(world_or_sim)
    why = f"plan:{plan['label']}"
    kind = step.get("kind")

    if kind == "travel":
        if step.get("area"):
            moved = sim._travel_to_area(player, step["area"], why)
        else:
            moved = sim._travel_toward(player, step.get("tags") or [], why)
        if moved:
            return TRAVEL_MINUTES
        if is_step_satisfied(sim, player, step):
            return None
        return "failed"

    if kind == "take":
        node = _in_area_matching(sim, player, step.get("spec") or {})
        if node is None:
            record(player, gs.time_ticks, "plan",
                   f"nothing to take for {plan['label']} at {player.current_area}",
                   why=f"{why}:failed", area=player.current_area, tags=["plan"])
            return "failed"
        sim._carry(player, node)
        record(player, gs.time_ticks, "plan",
               f"took {node.name} for {plan['label']}",
               why=why, area=player.current_area, tags=["plan"])
        return TAKE_MINUTES

    if kind == "drop":
        node = _carried_matching(sim, player, step.get("spec") or {})
        if node is None:
            return "failed"
        area_id = gs.area_node_id(player.current_area) if player.current_area else None
        if not area_id:
            return "failed"
        graph = gs.graph
        for e in list(graph.edges):
            if e.source == node.id:
                graph.remove_edge(e.source, e.target, e.type)
        graph.add_edge(Edge(source=node.id, target=area_id, type="in"))
        record(player, gs.time_ticks, "plan",
               f"delivered {node.name} to {player.current_area}",
               why=why, area=player.current_area, tags=["plan"])
        return TAKE_MINUTES

    if kind == "activity":
        want = str(step.get("activity") or "").strip().lower()
        if not want:
            return "failed"
        current = (getattr(player, "activity", None) or {}).get("type", "").lower()
        if current == want:
            return None
        target_item = step.get("target_item")
        dur_ticks = step.get("duration_ticks")
        try:
            dur_ticks = int(dur_ticks) if dur_ticks is not None else None
        except (TypeError, ValueError):
            dur_ticks = None
        dur_minutes = step.get("duration_minutes")
        try:
            dur_minutes = float(dur_minutes) if dur_minutes is not None else None
        except (TypeError, ValueError):
            dur_minutes = None
        catch_target = step.get("catch_count_target")
        recipe_id = step.get("recipe")

        if want == "cooking" and recipe_id and hasattr(gs, "crafting"):
            try:
                prev_active = getattr(gs, "active_player", player.name)
                gs.active_player = player.name
                msg = gs.crafting.start_cooking(gs, recipe_id)
                gs.active_player = prev_active
                record(player, gs.time_ticks, "plan",
                       f"started {want} for {plan['label']}: {msg}",
                       why=why, area=player.current_area, tags=["plan"])
                return None
            except Exception as exc:
                record(player, gs.time_ticks, "plan",
                       f"could not start {want} for {plan['label']}: {exc}",
                       why=f"{why}:failed", area=player.current_area, tags=["plan"])
                return "failed"

        try:
            msg = gs.activities.start_activity(
                player.name, want, target_item=target_item,
                duration_ticks=dur_ticks,
                duration_minutes=dur_minutes,
                catch_count_target=catch_target,
                recipe_id=recipe_id,
            )
            if want == "sleeping" and target_item:
                _bind_activity_spatial_relation(gs, player, target_item, "on")
            record(player, gs.time_ticks, "plan",
                   f"started {want} for {plan['label']}: {msg}",
                   why=why, area=player.current_area, tags=["plan"])
            return None
        except Exception as exc:
            record(player, gs.time_ticks, "plan",
                   f"could not start {want} for {plan['label']}: {exc}",
                   why=f"{why}:failed", area=player.current_area, tags=["plan"])
            return "failed"

    if kind == "wait":
        dur_minutes = step.get("duration_minutes") or 10
        try:
            gs.activities.start_activity(
                player.name, "waiting",
                duration_minutes=float(dur_minutes)
            )
            return None
        except Exception:
            return None

    return "failed"


# ───────────────────────────── lifecycle ────────────────────────────────────

def finish_plan(world_or_sim, player, plan: Dict[str, Any], outcome: str) -> None:
    """Record completion or failure of *plan*, updating active_pursuit and completed_pursuits."""
    sim, gs = _resolve_context(world_or_sim)
    label = plan.get("label", "plan")
    record(player, gs.time_ticks, "plan",
           f"plan {label} {outcome}",
           why=f"plan:{label}:{outcome}",
           area=player.current_area, tags=["plan"])

    done = getattr(player, "completed_pursuits", None)
    if done is None:
        done = []
        player.completed_pursuits = done
    assignment_id = plan.get("assignment_id")
    if assignment_id and assignment_id not in done:
        done.append(assignment_id)

    record(player, gs.time_ticks, "pursuit",
           f"pursuit {label} {outcome}",
           why=f"pursuit:{label}:{outcome}",
           area=player.current_area, tags=["pursuit"])

    active = getattr(player, "active_pursuit", None)
    if isinstance(active, dict) and active.get("assignment_id") == assignment_id:
        if active.get("repeat") and outcome == "done":
            active["step_index"] = 0
            plan["index"] = 0
            player.plan = plan
            return
        player.active_pursuit = None

    player.plan = None
    _unbind_activity_spatial_relation(gs, player, "on")


def _sync_pursuit_step(player, plan: Dict[str, Any]) -> None:
    """Keep the saved pursuit's progress aligned with its current plan."""
    pursuit = getattr(player, "active_pursuit", None)
    if isinstance(pursuit, dict) and pursuit.get("assignment_id") == plan.get("assignment_id"):
        pursuit["step_index"] = int(plan.get("index", 0) or 0)


def maybe_assign_pursuit(world_or_sim, player) -> bool:
    """Resume the character's assigned pursuit if idle and no plan is running."""
    if player.state in ("dead", "unconscious") or player.activity:
        return False
    pursuit = getattr(player, "active_pursuit", None)
    if not isinstance(pursuit, dict):
        return False
    if getattr(player, "plan", None):
        return False

    plan = build_plan(pursuit)
    if not plan or plan.get("pursuit_template") != pursuit.get("template_id"):
        return False
    plan["index"] = max(0, int(pursuit.get("step_index", 0) or 0))
    player.plan = plan

    sim, gs = _resolve_context(world_or_sim)
    if plan["index"] == 0:
        record(player, gs.time_ticks, "pursuit",
               f"started pursuit {plan['label']} because {plan['reason']}",
               why=f"pursuit:{plan['label']}:start",
               area=player.current_area, tags=["pursuit"])
    return True


def check_need_preemption(player, plan: Optional[Dict[str, Any]] = None) -> bool:
    """Check if critical survival needs demand immediate preemption of a plan."""
    vitals = getattr(player, "vitals", {}) or {}
    template = str((plan or {}).get("pursuit_template") or "").lower()
    # Critical thresholds matching survival ladder, exempting pursuits serving that exact need
    if vitals.get("Hunger", 0) >= 85 and template not in ("meal", "eat", "food"):
        return True
    if vitals.get("Thirst", 0) >= 85 and template not in ("drink", "water"):
        return True
    if vitals.get("Bladder", 0) >= 90:
        return True
    if vitals.get("Energy", 100) <= 15 and template not in ("sleep-at-venue", "sleep", "rest"):
        return True
    return False


def advance_plan(world_or_sim, player) -> Optional[int]:
    """Advance the stored plan for *player* by (at most) one action.

    Unified runtime runner for LLM agents, simple NPCs, and background characters.
    Returns minutes used or None.
    """
    sim, gs = _resolve_context(world_or_sim)
    plan = getattr(player, "plan", None)
    if not plan and not maybe_assign_pursuit(world_or_sim, player):
        return None

    plan = player.plan
    if not plan:
        return None

    # Check survival need preemption
    if check_need_preemption(player, plan):
        return None

    # Validate plan approach against world state
    valid, reason = is_plan_valid(player, world_or_sim, plan)
    if not valid:
        record(player, gs.time_ticks, "plan",
               f"plan approach {plan.get('label')} invalidated: {reason}",
               why=f"plan:{plan.get('label')}:failed",
               area=player.current_area, tags=["plan"])
        finish_plan(world_or_sim, player, plan, "failed")
        return None

    steps = plan.get("steps") or []
    while True:
        idx = int(plan.get("index", 0) or 0)
        if idx >= len(steps):
            finish_plan(world_or_sim, player, plan, "done")
            return None
        step = steps[idx]
        if is_step_satisfied(sim, player, step):
            plan["index"] = idx + 1
            _sync_pursuit_step(player, plan)
            continue
        outcome = execute_step(sim, player, plan, step)
        if outcome == "failed":
            finish_plan(world_or_sim, player, plan, "failed")
            return None
        if outcome and is_step_satisfied(sim, player, step):
            plan["index"] = idx + 1
            _sync_pursuit_step(player, plan)
            if plan["index"] >= len(steps):
                finish_plan(world_or_sim, player, plan, "done")
        return outcome
