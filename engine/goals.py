"""Character goals -- what a character is trying to achieve (task-807).

A goal is character-private data. It belongs to the mind of the character, not
to the world: it is stored on the character's own record (``Player.goals``,
beside ``Player.schedule``) and never as a graph node. Nodes are the physical
things in the world -- areas, ways, items, characters -- and a goal, being an
intention, is not one of them.

A goal record::

    {
      "id": "become_chief",
      "what": "Become chief of the camp",
      "status": "active",
      "motivation": "I want respect and power",
      "intention": "because then the others will not push me around"
    }

``motivation`` and ``intention`` are GIMP's M and I: the drive that produced the
goal, and the reason to pursue *this* one. They are stored on the goal, which is
their single home; MOSIAC reads the goal rather than keeping a second copy.

``status`` is one of :data:`GOAL_STATUSES`. A malformed goal (neither an id nor
a ``what``) is dropped rather than guessed, the same contract as
``engine.schedule.normalize``. An empty list means "no goals", which is a valid
state and what every character was before this task.

@module goals
@contributes GOAL_STATUSES, normalize, find, set_goal, set_status, active, describe
@docs docs/virtualWorld/design/Character Pursuits.md
"""
from __future__ import annotations

import re

#: The lifecycle of a goal. ``proposed`` is the default for a goal that is
#: authored or created but not yet adopted by the character.
GOAL_STATUSES = ("proposed", "active", "reached", "blocked", "dropped")

DEFAULT_STATUS = "proposed"

#: Statuses that mean a goal is settled: it no longer blocks anything that waits
#: on it. A goal still proposed/active/blocked is an outstanding blocker.
TERMINAL_STATUSES = frozenset({"reached", "dropped"})

#: The lifecycle of an obligation. An obligation is an *input* to the mind: it
#: becomes a goal only when the character accepts it.
OBLIGATION_STATUSES = ("offered", "accepted", "refused", "forgotten", "done")

OBLIGATION_DEFAULT_STATUS = "offered"

_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text):
    """A stable id from a goal's ``what`` text, e.g. "Become chief" -> "become_chief"."""
    return _SLUG.sub("_", str(text or "").strip().lower()).strip("_")


def normalize(goals):
    """Validated, de-duplicated copy. Malformed goals are dropped, not guessed.

    Dropping is deliberate: a goal with neither an id nor a ``what`` cannot be
    referred to or displayed, and inventing one would give the character an
    intention nobody authored.
    """
    if not goals:
        return []
    if isinstance(goals, dict):
        goals = goals.get("goals") or []
    out = []
    seen = set()
    for raw in goals:
        if not isinstance(raw, dict):
            continue
        what = str(raw.get("what") or raw.get("target") or "").strip()
        gid = str(raw.get("id") or "").strip() or slug(what)
        if not gid or not what or gid in seen:
            continue
        seen.add(gid)
        status = str(raw.get("status") or DEFAULT_STATUS).strip().lower()
        if status not in GOAL_STATUSES:
            status = DEFAULT_STATUS
        goal = {"id": gid, "what": what, "status": status}
        for key in ("motivation", "intention"):
            value = str(raw.get(key) or "").strip()
            if value:
                goal[key] = value
        for key in ("blocks", "links"):
            refs = _ref_list(raw.get(key))
            if refs:
                goal[key] = refs
        out.append(goal)
    return out


def active(goals):
    """The goals currently being pursued (``status`` == ``active``)."""
    return [g for g in normalize(goals) if g["status"] == "active"]


def find(goals, ref):
    """The goal whose id or (lower-cased) ``what`` matches *ref*, or None."""
    ref = str(ref or "").strip().lower()
    if not ref:
        return None
    for goal in normalize(goals):
        if goal["id"].lower() == ref or goal["what"].lower() == ref:
            return goal
    return None


def set_goal(goals, what, *, motivation="", intention="", status="active", tick=None, log=None):
    """Add a goal, or update the one with the same id. Returns ``(goals, error)``.

    The id is derived from ``what`` (``slug``), so stating the same want twice
    updates it in place rather than stacking a duplicate. When *log* is given,
    the transition is appended to it (task-811) with *tick*.
    """
    what = str(what or "").strip()
    if not what:
        return normalize(goals), "A goal needs something to aim for."
    if status not in GOAL_STATUSES:
        status = "active"
    record = {"id": slug(what), "what": what, "status": status}
    if str(motivation).strip():
        record["motivation"] = str(motivation).strip()
    if str(intention).strip():
        record["intention"] = str(intention).strip()
    records = normalize(goals)
    for index, goal in enumerate(records):
        if goal["id"] == record["id"]:
            records[index] = {**goal, **record}
            if log is not None:
                log.append(_event(records[index], records[index]["status"], tick))
            return records, None
    records.append(record)
    if log is not None:
        log.append(_event(record, record["status"], tick))
    return records, None


def set_status(goals, ref, status, *, tick=None, log=None):
    """Move the goal matching *ref* to *status*. Returns ``(goals, error)``.

    Completing is ``reached`` and dropping is ``dropped``; both are this with a
    different status, so there is one rule that changes a goal's state. When
    *log* is given, the transition is appended to it (task-811) with *tick*.
    """
    records = normalize(goals)
    if status not in GOAL_STATUSES:
        return records, f"Unknown goal status {status!r}."
    target = find(records, ref)
    if target is None:
        return records, f"No goal matches {ref!r}."
    for goal in records:
        if goal["id"] == target["id"]:
            goal["status"] = status
            if log is not None:
                log.append(_event(goal, status, tick))
    return records, None


def _ref_list(value):
    """Normalise a ``blocks`` / ``links`` value to a clean list of strings.

    Accepts a list or a comma/semicolon string, so a form field and an authored
    list are the same thing.
    """
    if not value:
        return []
    if isinstance(value, str):
        value = value.replace(";", ",").split(",")
    out = []
    for item in value:
        ref = str(item or "").strip()
        if ref:
            out.append(ref)
    return out


def _split_ref(ref):
    """``('item', 'torch_01')`` from ``'item:torch_01'``.

    A bare ref with no prefix is a goal id, so the common case (one goal waiting
    on another) needs no ceremony.
    """
    text = str(ref or "").strip()
    if ":" in text:
        prefix, _, value = text.partition(":")
        return prefix.strip().lower(), value.strip()
    return "goal", text


def goal_resolver(goals):
    """The ``goal`` resolver: a goal ref is met once the referenced goal is
    terminal (reached or dropped), or when no such goal exists."""
    by_id = {g["id"]: g for g in normalize(goals)}

    def met(ref):
        g = by_id.get(ref)
        return g is None or g["status"] in TERMINAL_STATUSES

    return met


def resolve_blocks(goal, resolvers):
    """The ``blocks`` refs of *goal* that are not yet satisfied.

    *resolvers* maps a ref prefix (``goal``, ``item``, ``character``, ``event``)
    to a predicate taking the value after the prefix. A prefix with no resolver
    counts as outstanding, so an unknown blocker holds the goal rather than
    silently freeing it.
    """
    outstanding = []
    for ref in goal.get("blocks") or []:
        prefix, value = _split_ref(ref)
        predicate = resolvers.get(prefix)
        if predicate is None or not predicate(value):
            outstanding.append(ref)
    return outstanding


def is_blocked(goal, resolvers):
    """True when *goal* still has at least one unsatisfied ``blocks`` ref."""
    return bool(resolve_blocks(goal, resolvers))


def outstanding_blocks(goals, resolvers):
    """``{goal_id: [refs still outstanding]}`` for every blocked goal."""
    out = {}
    for goal in normalize(goals):
        refs = resolve_blocks(goal, resolvers)
        if refs:
            out[goal["id"]] = refs
    return out


def with_blockers(goals, resolvers):
    """A copy of *goals* where each blocked goal carries a derived ``blocked_by``.

    A projection for the payload and the UI, not persisted state: the stored goal
    keeps only its authored ``blocks``.
    """
    out = []
    for goal in normalize(goals):
        decorated = dict(goal)
        refs = resolve_blocks(goal, resolvers)
        if refs:
            decorated["blocked_by"] = refs
        out.append(decorated)
    return out


def _event(goal, status, tick):
    """One append-only goal-history entry (task-811)."""
    return {"goal_id": goal["id"], "what": goal["what"], "status": status,
            "tick": int(tick or 0)}


def history(log):
    """A validated copy of a goal log, in the order it was recorded.

    Malformed rows are dropped, the same contract as ``normalize``: a history
    that cannot be read is not guessed at.
    """
    if not log:
        return []
    out = []
    for raw in log:
        if not isinstance(raw, dict):
            continue
        gid = str(raw.get("goal_id") or raw.get("id") or "").strip()
        status = str(raw.get("status") or "").strip().lower()
        if not gid or status not in GOAL_STATUSES:
            continue
        out.append({"goal_id": gid, "what": str(raw.get("what") or "").strip(),
                    "status": status, "tick": int(raw.get("tick") or 0)})
    return out


def world_resolvers(graph, holder_id, goals=None):
    """Resolvers backed by the live world.

    ``goal`` uses the character's other goals; ``item`` is met when the holder
    carries or owns the node; ``character`` is met while the node exists. Kept
    behind a function so ``goals.py`` stays dependency-light and a plain model
    test needs no graph.
    """
    resolvers = {"goal": goal_resolver(goals or [])}
    if graph is None:
        return resolvers

    def held(node_id):
        try:
            from graph import EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
            node = graph.get_node(node_id)
            # Worn or carried: an edge item -> holder. (EDGE_EQUIPPED and
            # EDGE_CARRYING point at the player, so read them from the target.)
            for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
                if any(e.source == node_id
                       for e in graph.get_edges_for_target(holder_id, edge_type)):
                    return True
            # Inside one of the holder's containers (an item -> container `in`).
            if node is not None and getattr(node, 'type', None) == 'item':
                if any(e.source == node_id
                       for e in graph.get_edges_for_target(holder_id, EDGE_IN)):
                    return True
            if node is not None:
                from engine.items.ownership import owner_of
                return owner_of(node) == holder_id
        except Exception:
            return False
        return False

    def exists(node_id):
        try:
            return graph.get_node(node_id) is not None
        except Exception:
            return False

    resolvers["item"] = held
    resolvers["character"] = exists
    return resolvers


def normalize_obligations(obligations):
    """Validated, de-duplicated copy. Malformed rows are dropped, not guessed."""
    if not obligations:
        return []
    if isinstance(obligations, dict):
        obligations = obligations.get("obligations") or []
    out = []
    seen = set()
    for raw in obligations:
        if not isinstance(raw, dict):
            continue
        charge = str(raw.get("charge") or raw.get("what") or "").strip()
        oid = str(raw.get("id") or "").strip() or slug(charge)
        if not oid or not charge or oid in seen:
            continue
        seen.add(oid)
        status = str(raw.get("status") or OBLIGATION_DEFAULT_STATUS).strip().lower()
        if status not in OBLIGATION_STATUSES:
            status = OBLIGATION_DEFAULT_STATUS
        record = {"id": oid, "charge": charge, "status": status}
        for key in ("from", "reward", "goal_id"):
            value = str(raw.get(key) or "").strip()
            if value:
                record[key] = value
        try:
            due = int(raw.get("due") or 0)
        except (TypeError, ValueError):
            due = 0
        if due:
            record["due"] = due
        out.append(record)
    return out


def offer_obligation(obligations, charge, *, from_name="", reward="", due=0):
    """Add an offered obligation. Returns ``(obligations, obligation, error)``.

    An offer is the world's side of the exchange: a mission, a promise owed, an
    appointment. It sits `offered` until the character answers it.
    """
    charge = str(charge or "").strip()
    if not charge:
        return normalize_obligations(obligations), None, "An obligation needs a charge."
    record = {"id": slug(charge), "charge": charge, "status": "offered"}
    if str(from_name).strip():
        record["from"] = str(from_name).strip()
    if str(reward).strip():
        record["reward"] = str(reward).strip()
    if due:
        record["due"] = int(due)
    records = normalize_obligations(obligations)
    for index, existing in enumerate(records):
        if existing["id"] == record["id"]:
            records[index] = record
            return records, record, None
    records.append(record)
    return records, record, None


def find_obligation(obligations, ref):
    """The obligation whose id or (lower-cased) charge matches *ref*, or None."""
    ref = str(ref or "").strip().lower()
    if not ref:
        return None
    for obligation in normalize_obligations(obligations):
        if obligation["id"].lower() == ref or obligation["charge"].lower() == ref:
            return obligation
    return None


def respond_obligation(obligations, ref, action, *, goals=None,
                       motivation="", intention="", tick=None, log=None):
    """Answer an obligation: accept, refuse, alter or forget it.

    Accepting is the only answer that spawns a goal -- the intention the
    obligation generates. Refusing spawns nothing. Returns
    ``(obligations, goals, error)``; *goals* is the caller's list when only the
    obligation changes, so a caller that passed none gets its old list back.
    """
    aliases = {"accept": "accepted", "refuse": "refused", "decline": "refused",
               "forget": "forgotten", "done": "done", "complete": "done",
               "alter": "offered", "reopen": "offered"}
    status = aliases.get(str(action or "").strip().lower())
    if status is None:
        return normalize_obligations(obligations), goals, f"Unknown answer {action!r}."
    records = normalize_obligations(obligations)
    target = find_obligation(records, ref)
    if target is None:
        return records, goals, f"No obligation matches {ref!r}."
    for obligation in records:
        if obligation["id"] != target["id"]:
            continue
        obligation["status"] = status
        if status == "accepted":
            spawned, error = set_goal(
                goals or [],
                obligation["charge"],
                motivation=motivation,
                intention=intention or f"obligation to {obligation.get('from', 'someone')}",
                tick=tick, log=log,
            )
            if error:
                return records, goals, error
            obligation["goal_id"] = slug(obligation["charge"])
            goals = spawned
    return records, goals, None


def expire_obligations(obligations, tick):
    """Mark offered/accepted obligations past their due tick as forgotten."""
    records = normalize_obligations(obligations)
    for obligation in records:
        due = obligation.get("due") or 0
        if due and tick >= due and obligation["status"] in ("offered", "accepted"):
            obligation["status"] = "forgotten"
    return records


def describe_obligations(obligations):
    """A one-line summary, for the inspector and the `obligation` verb."""
    norm = normalize_obligations(obligations)
    if not norm:
        return "no obligations"
    return "; ".join(f"{o['charge']} [{o['status']}]" for o in norm)


def describe(goals):
    """A one-line summary, for the inspector and for debugging a soak."""
    norm = normalize(goals)
    if not norm:
        return "no goals"
    return "; ".join(f"{g['what']} [{g['status']}]" for g in norm)
