"""Authored multi-step plans for the background tier (task-426).

A plan is stored on ``Player.plan`` and advanced **one step per action** — it is
*not* recomputed each tick. That is what lets a plan survive a need interruption:
the survival ladder in ``_act`` runs first, returns, and the plan is still there,
so the next satisfied action resumes exactly where it stopped.

Templates are data, selected algorithmically and knowledge-gated. A ``plan``
graph node (the same shape as a crafting ``recipe`` node, task-2) declares one:

.. code-block:: json
   {
     "template": "haul",
     "actor": "Mikka",           // display name OR node id; ids win
     "source": "Scrap Pile",     // area name the plan takes from
     "item": "scrap",            // item tag to move (or "item_name")
     "sink": "Workshop",         // area name the plan delivers to
     "label": "scrap_run",
     "repeat": false
   }

v1 templates:

``haul``
    ``[travel(source), take(item), travel(sink), drop(item)]`` — move a thing
    from where it is to where it belongs.
``gather``
    ``[travel(area-with-tags), take(item), travel(home), drop(item)]`` — fetch a
    resource from the wild to a home area.

Selection is deterministic (plan nodes are considered in id order) and
knowledge-gated: a plan is only started when its source is reachable from the
character's current area. A plan never fabricates an item — if the source holds
nothing matching, ``take`` fails and the plan is abandoned with a trace.

Trace vocabulary: each progressed step writes ``why="plan:<label>"``; completion
writes ``plan:<label>:done`` and a broken precondition ``plan:<label>:failed``,
so ``engine/soak_telemetry`` groups the whole run under the ``plan`` prefix.
"""
from __future__ import annotations

import logging

from graph import Edge, EDGE_CARRYING
from engine.lived_log import record

logger = logging.getLogger(__name__)

#: Graph node type that declares a plan (mirrors ``recipe``).
PLAN_NODE_TYPE = "plan"

TRAVEL_MINUTES = 1
TAKE_MINUTES = 2

#: A group goal is capped so one authored node cannot drag an unbounded crowd
#: into a single rally. Templates are fixed-length, and a member with no plan
#: falls back to the task-409 per-step planner — that is the "bounded with a
#: fallback" the task asks for, not a second planner.
MAX_PARTICIPANTS = 16

#: Spatial relations an item can sit in, for "is it already here" checks.
_SPATIAL = ("in", "on", "under", "behind", "beside", "at")


# ───────────────────────────── building ─────────────────────────────────────

def _spec(props):
    """The item match spec a plan node declares."""
    tag = props.get("item")
    name = props.get("item_name")
    return {
        "tags": [str(tag)] if tag else [],
        "name": str(name) if name else None,
    }


def build_plan(node):
    """A stored plan dict from a ``plan`` node, or None for an unknown template."""
    props = node.properties or {}
    template = str(props.get("template") or "").strip().lower()
    label = str(props.get("label") or node.id)
    spec = _spec(props)
    has_item = bool(spec["tags"] or spec["name"])
    if template == "haul":
        source = props.get("source")
        sink = props.get("sink")
        if not source or not sink or not has_item:
            return None
        steps = [
            {"kind": "travel", "area": source, "to": f"{source}"},
            {"kind": "take", "spec": spec},
            {"kind": "travel", "area": sink, "to": f"{sink}"},
            {"kind": "drop", "spec": spec},
        ]
    elif template == "gather":
        source_tags = props.get("source_tags") or []
        home = props.get("home")
        if not source_tags or not home or not has_item:
            return None
        steps = [
            {"kind": "travel", "tags": [str(t) for t in source_tags], "to": "source"},
            {"kind": "take", "spec": spec},
            {"kind": "travel", "area": home, "to": f"{home}"},
            {"kind": "drop", "spec": spec},
        ]
    elif template == "rally":
        # A group goal: every participant walks to one place. It is a *record*
        # (leader, goal, rally point) enforced by a one-step local plan, so
        # emergence comes from each member planning locally, not from the
        # leader commanding a shared plan object (task-426).
        rally = props.get("rally_area")
        if not rally:
            return None
        steps = [{"kind": "travel", "area": rally, "to": f"{rally}"}]
    else:
        return None
    return {
        "node_id": node.id,
        "template": template,
        "label": label,
        "index": 0,
        "steps": steps,
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

def _satisfied(sim, p, step):
    kind = step.get("kind")
    if kind == "travel":
        if step.get("area"):
            return p.current_area == step["area"]
        return p.current_area in sim._areas_with(step.get("tags") or [])
    if kind == "take":
        return _carried_matching(sim, p, step["spec"]) is not None
    if kind == "drop":
        # Done once the item sits in this area and is no longer carried.
        carried = _carried_matching(sim, p, step["spec"])
        return carried is None and _in_area_matching(sim, p, step["spec"]) is not None
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

    return "failed"


def _finish(sim, p, plan, outcome):
    record(p, sim.gs.time_ticks, "plan",
           f"plan {plan['label']} {outcome}",
           why=f"plan:{plan['label']}:{outcome}",
           area=p.current_area, tags=["plan"])
    done = getattr(p, "completed_plans", None)
    if done is None:
        done = []
        p.completed_plans = done
    if plan.get("node_id") and plan["node_id"] not in done:
        done.append(plan["node_id"])
    p.plan = None


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
            if plan["index"] >= len(steps):
                _finish(sim, p, plan, "done")
        return outcome


# ───────────────────────────── selection ────────────────────────────────────

def _is_actor(sim, p, node):
    """Is *p* the actor of a plan node, one of its participants, or of its role?

    ``actor``/``participants`` are the authored case (an id or display name);
    ``role`` is the algorithmic one — any character carrying the tag may claim
    the plan (e.g. every ``tinkerer`` runs the scrap run).
    """
    props = node.properties or {}
    pid = sim.gs._player_node_id(p.name)
    candidates = []
    actor = props.get("actor")
    if actor:
        candidates.append(str(actor))
    for member in (props.get("participants") or [])[:MAX_PARTICIPANTS]:
        candidates.append(str(member))
    for cand in candidates:
        if cand == p.name or (pid and cand.lower() == str(pid).lower()):
            return True
    role = props.get("role")
    if role:
        tags = {str(t).lower() for t in (getattr(p, "tags", None) or [])}
        if str(role).lower() in tags:
            return True
    return False


def _source_reachable(sim, p, plan):
    """Knowledge gate: the source must be reachable now, or the plan waits."""
    from engine import traversal
    avoid = traversal.avoid(sim.gs, p)
    for step in plan.get("steps", []):
        if step.get("kind") != "travel":
            continue
        if step.get("area"):
            if p.current_area == step["area"]:
                return True
            return sim._target_step(p, None, areas={step["area"]}, avoid=avoid) is not None
        if step.get("tags"):
            if p.current_area in sim._areas_with(step["tags"]):
                return True
            return sim._target_step(p, step["tags"], avoid=avoid) is not None
    return False


def maybe_assign(sim, p):
    """Start a due plan for *p* if one is authored, reachable, and not yet done."""
    if getattr(p, "plan", None) or p.state == "dead" or p.activity:
        return False
    done = set(getattr(p, "completed_plans", []) or [])
    nodes = sorted(
        (n for n in sim.gs.graph.nodes.values() if n.type == PLAN_NODE_TYPE),
        key=lambda n: n.id,
    )
    for node in nodes:
        props = node.properties or {}
        if node.id in done and not props.get("repeat"):
            continue
        if not _is_actor(sim, p, node):
            continue
        plan = build_plan(node)
        if not plan or not _source_reachable(sim, p, plan):
            continue
        p.plan = plan
        record(p, sim.gs.time_ticks, "plan",
               f"started plan {plan['label']}", why=f"plan:{plan['label']}:start",
               area=p.current_area, tags=["plan"])
        return True
    return False
