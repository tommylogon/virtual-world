"""Assigned character pursuits and their short-term execution (task-426).

A pursuit is **character data, not a world node** (task-818): an actor-bound
assignment - which reusable pursuit template this character is undertaking, with
what bindings and reason. The generic template lives in
``data/library/pursuit_templates`` and is separate from both the assignment and
world-crafting recipes.

The assignment is persisted on ``Player.active_pursuit``. Its current grounded
approach is kept on ``Player.plan`` and advanced **one step per action**. This
lets the pursuit survive a need interruption: the survival ladder in ``_act``
runs first, and the current approach resumes after the need is answered.

The assignment has this shape (``Player.active_pursuit``):

.. code-block:: json
   {
     "assignment_id": "pursuit_mikka_scrap_run",
     "template_id": "haul",
     "bindings": {
       "source": "Scrap Pile",   // bound source area
       "item": "scrap",          // item tag to move (or "item_name")
       "sink": "Workshop"        // bound destination area
     },
     "label": "scrap_run",
     "reason": "Move scrap to the workshop for repairs.",
     "repeat": false
   }

The runner **resumes** the character's own assignment; it does not scan the graph
for ``pursuit`` nodes (that node type is retired). A plan never fabricates an item
— if the source holds nothing matching, ``take`` fails and the plan is abandoned
with a trace.

Trace vocabulary: each progressed short-term step writes
``why="plan:<label>"``; plan completion/failure writes ``plan:<label>:done`` or
``plan:<label>:failed``. Pursuit start/completion has the separate
``pursuit:<label>`` prefix.
"""
from __future__ import annotations

import logging

from graph import Edge, EDGE_CARRYING
from engine.lived_log import record

logger = logging.getLogger(__name__)

TRAVEL_MINUTES = 1
TAKE_MINUTES = 2

#: Spatial relations an item can sit in, for "is it already here" checks.
_SPATIAL = ("in", "on", "under", "behind", "beside", "at")


# ───────────────────────────── building ─────────────────────────────────────

def build_plan(pursuit):
    """Build the current short-term plan for a character's pursuit assignment.

    *pursuit* is the character-side ``Player.active_pursuit`` dict: it carries the
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
    return {
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


# ───────────────────────────── matching ─────────────────────────────────────

def _match_item(node, spec):
    props = node.properties or {}
    tags = {str(t).lower() for t in (props.get("tags") or [])}
    want = {str(t).lower() for t in (spec.get("tags") or [])}
    if want and not (want & tags):
        return False
    name = spec.get("name")
    if name:
        needle = name.lower()
        if needle not in str(node.name or "").lower() and needle not in str(node.id or "").lower():
            return False
    return bool(want or name)


def _is_fixture(node):
    props = node.properties or {}
    tags = {str(t).lower() for t in (props.get("tags") or [])}
    return "fixture" in tags


def _carried_matching(sim, p, spec):
    for node in sim._carried_nodes(p):
        if _match_item(node, spec):
            return node
    return None


def _in_area_matching(sim, p, spec):
    area_id = sim.gs.area_node_id(p.current_area) if p.current_area else None
    if not area_id:
        return None
    for node in sim._spatial_items(area_id):
        if _is_fixture(node):
            continue
        if _match_item(node, spec):
            return node
    return None


# ───────────────────────────── execution ────────────────────────────────────

def _check_activity_completion(activity: Optional[dict], condition: dict, player) -> bool:
    ctype = condition.get("type")
    if ctype == "duration_elapsed":
        if activity.get("duration_minutes") is not None:
            return activity.get("elapsed_minutes", 0.0) >= activity["duration_minutes"]
        if activity.get("duration_ticks") is not None:
            return activity.get("elapsed_ticks", 0) >= activity["duration_ticks"]
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


def _satisfied(sim, p, step):
    kind = step.get("kind")
    if kind == "travel":
        if step.get("area"):
            return p.current_area == step["area"]
        return p.current_area in sim._areas_with(step.get("tags") or [])
    if kind == "take":
        return _carried_matching(sim, p, step["spec"]) is not None
    if kind == "drop":
        carried = _carried_matching(sim, p, step["spec"])
        return carried is None and _in_area_matching(sim, p, step["spec"]) is not None
    if kind == "activity":
        activity = getattr(p, "activity", None)
        want = str(step.get("activity") or "").strip().lower()
        if not want:
            return activity is None
        current_type = (activity or {}).get("type", "").lower()
        if current_type != want:
            last_type = getattr(p, "_last_completed_activity_type", None)
            if last_type and str(last_type).lower() == want:
                p._last_completed_activity_type = None
                return True
            return False
        catch_target = step.get("catch_count_target")
        if catch_target is not None:
            if activity.get("catch_count", 0) >= int(catch_target):
                return True
        # task-726: compare each unit against its own elapsed counter. The old
        # `duration_ticks or duration_minutes` compared a minutes value against
        # elapsed_ticks, so a minutes duration never elapsed correctly.
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
                if _check_activity_completion(activity, condition, p):
                    return True
        except Exception:
            pass
        return False
    return True


def _where(p):
    return p.current_area or "?"


def _run(sim, p, plan, step):
    """Run one step. Returns minutes used, None if it could not progress, or
    the string ``"failed"`` when a precondition is broken."""
    why = f"plan:{plan['label']}"
    kind = step.get("kind")

    if kind == "travel":
        if step.get("area"):
            moved = sim._travel_to_area(p, step["area"], why)
        else:
            moved = sim._travel_toward(p, step["tags"], why)
        if moved:
            return TRAVEL_MINUTES
        # No route this action: not a failure, the plan waits. But if we are
        # already at a tags-source, the satisfied check above handles it.
        if _satisfied(sim, p, step):
            return None
        return "failed"

    if kind == "take":
        node = _in_area_matching(sim, p, step["spec"])
        if node is None:
            record(p, sim.gs.time_ticks, "plan",
                   f"nothing to take for {plan['label']} at {_where(p)}",
                   why=f"{why}:failed", area=p.current_area, tags=["plan"])
            return "failed"
        sim._carry(p, node)
        record(p, sim.gs.time_ticks, "plan",
               f"took {node.name} for {plan['label']}",
               why=why, area=p.current_area, tags=["plan"])
        return TAKE_MINUTES

    if kind == "drop":
        node = _carried_matching(sim, p, step["spec"])
        if node is None:
            return "failed"
        area_id = sim.gs.area_node_id(p.current_area) if p.current_area else None
        if not area_id:
            return "failed"
        graph = sim.gs.graph
        for e in list(graph.edges):
            if e.source == node.id and e.type != EDGE_CARRYING:
                graph.remove_edge(e.source, e.target, e.type)
            if e.source == node.id and e.type == EDGE_CARRYING:
                graph.remove_edge(e.source, e.target, e.type)
        graph.add_edge(Edge(source=node.id, target=area_id, type="in"))
        record(p, sim.gs.time_ticks, "plan",
               f"delivered {node.name} to {_where(p)}",
               why=why, area=p.current_area, tags=["plan"])
        return TAKE_MINUTES

    if kind == "activity":
        want = str(step.get("activity") or "").strip().lower()
        if not want:
            return "failed"
        current = (getattr(p, "activity", None) or {}).get("type", "").lower()
        if current == want:
            return None
        target_item = step.get("target_item")
        # task-726: keep the units separate — a minutes value must never be
        # passed as a tick count.
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
        try:
            msg = sim.gs.activities.start_activity(
                p.name, want, target_item, dur_ticks,
                duration_minutes=dur_minutes,
                catch_count_target=catch_target,
            )
            record(p, sim.gs.time_ticks, "plan",
                   f"started {want} for {plan['label']}: {msg}",
                   why=why, area=p.current_area, tags=["plan"])
            return None
        except Exception as exc:
            record(p, sim.gs.time_ticks, "plan",
                   f"could not start {want} for {plan['label']}: {exc}",
                   why=f"{why}:failed", area=p.current_area, tags=["plan"])
            return "failed"

    return "failed"


def _finish(sim, p, plan, outcome):
    record(p, sim.gs.time_ticks, "plan",
           f"plan {plan['label']} {outcome}",
           why=f"plan:{plan['label']}:{outcome}",
           area=p.current_area, tags=["plan"])
    done = getattr(p, "completed_pursuits", None)
    if done is None:
        done = []
        p.completed_pursuits = done
    if plan.get("assignment_id") and plan["assignment_id"] not in done:
        done.append(plan["assignment_id"])
    record(p, sim.gs.time_ticks, "pursuit",
           f"pursuit {plan['label']} {outcome}",
           why=f"pursuit:{plan['label']}:{outcome}",
           area=p.current_area, tags=["pursuit"])
    active = getattr(p, "active_pursuit", None)
    if isinstance(active, dict) and active.get("assignment_id") == plan.get("node_id"):
        p.active_pursuit = None
    p.plan = None


def _sync_pursuit_step(p, plan):
    """Keep the saved pursuit's progress aligned with its current plan."""
    pursuit = getattr(p, "active_pursuit", None)
    if isinstance(pursuit, dict) and pursuit.get("assignment_id") == plan.get("assignment_id"):
        pursuit["step_index"] = int(plan.get("index", 0) or 0)


def advance(sim, p):
    """Advance the stored plan by (at most) one action. Returns minutes or None."""
    plan = getattr(p, "plan", None)
    if not plan:
        return None
    steps = plan.get("steps") or []
    while True:
        idx = int(plan.get("index", 0))
        if idx >= len(steps):
            _finish(sim, p, plan, "done")
            return None
        step = steps[idx]
        if _satisfied(sim, p, step):
            plan["index"] = idx + 1
            _sync_pursuit_step(p, plan)
            continue
        outcome = _run(sim, p, plan, step)
        if outcome == "failed":
            _finish(sim, p, plan, "failed")
            return None
        # Resolve completion in the same call that performed the step: a drop
        # that just landed must not depend on getting one more action before the
        # timeframe ends, or the next tick re-checks a step it already finished
        # and (now standing somewhere else) fails a plan that actually succeeded.
        if outcome and _satisfied(sim, p, step):
            plan["index"] = idx + 1
            _sync_pursuit_step(p, plan)
            if plan["index"] >= len(steps):
                _finish(sim, p, plan, "done")
        return outcome


# ───────────────────────────── resume ───────────────────────────────────────

def maybe_assign(sim, p):
    """Resume the character's own assigned pursuit, if any.

    The assignment is character data (``Player.active_pursuit``); this module no
    longer scans the graph for pursuit nodes - task-818 retired that node type, so
    a pursuit is started by whatever assigns the character (an author, a trigger,
    a goal), not by a node the runner discovers. ``Player.plan`` is only the
    current short-term approach, rebuilt from the assignment's template/bindings.
    """
    if p.state == "dead" or p.activity:
        return False
    pursuit = getattr(p, "active_pursuit", None)
    if not isinstance(pursuit, dict):
        return False
    if getattr(p, "plan", None):
        return False
    plan = build_plan(pursuit)
    if not plan or plan.get("pursuit_template") != pursuit.get("template_id"):
        return False
    plan["index"] = max(0, int(pursuit.get("step_index", 0) or 0))
    p.plan = plan
    if plan["index"] == 0:
        # The pursuit "starts" when its plan first runs; the trace vocabulary is
        # unchanged (`pursuit:<label>:start`).
        record(p, sim.gs.time_ticks, "pursuit",
               f"started pursuit {plan['label']} because {plan['reason']}",
               why=f"pursuit:{plan['label']}:start",
               area=p.current_area, tags=["pursuit"])
    return True
