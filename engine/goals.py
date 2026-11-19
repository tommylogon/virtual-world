"""Character goals - what a character is trying to achieve (task-807, task-822).

A goal is character-private data. It belongs to the mind of the character, not
to the world: it is stored on the character's own record (``Player.goals``,
beside ``Player.schedule``) and never as a graph node. Nodes are the physical
things in the world - areas, ways, items, characters - and a goal, being an
intention, is not one of them.

A goal record (the 15 fields of task-822)::

    {
      "id": "become_chief",
      "what": "Become chief of the camp",
      "why": "I want respect and power",
      "motivation": "I want respect and power",
      "intention": "because then the others will not push me around",
      "hoped_for": "the chief's staff",
      "source": "self",
      "opened_tick": 0,
      "priority": 1,
      "visibility": "known",
      "blocks": [{"ref": "character:Croak-Mother", "note": "she will not approve"}],
      "achieve": [{"ref": "item:item_chiefs_staff", "note": "symbol of authority"}],
      "achieve_mode": "all",
      "links": ["rally_clan"],
      "deadline": 100,
      "status": "active"
    }

``status`` is stored; ``blocked`` and ``progress`` are projections computed on
read.

@module goals
@contributes GOAL_STATUSES, normalize, find, set_goal, set_status, active, describe, reached, sync_reached, dispatch_goal_reached
@docs docs/virtualWorld/design/Character Pursuits.md
"""
from __future__ import annotations

import re

#: The lifecycle of a goal. ``proposed`` is the default for a goal that is
#: authored or created but not yet adopted by the character; ``dormant`` is a
#: goal the character holds but is not working right now, which is a different
#: state from "not yet adopted" and is what authored long-term ambitions load
#: as. ``reached`` is the terminal success; ``dropped`` covers both abandonment
#: and a missed deadline.
GOAL_STATUSES = ("proposed", "active", "dormant", "reached", "blocked", "dropped")

DEFAULT_STATUS = "proposed"

#: Statuses that mean a goal is settled: it no longer blocks anything that waits
#: on it. A goal still proposed/active/blocked is an outstanding blocker.
TERMINAL_STATUSES = frozenset({"reached", "dropped"})

#: Provenance sources for goals (task-822).
GOAL_SOURCES = ("self", "obligation", "schedule", "need", "event")

#: Visibility tiers for goals (task-822).
GOAL_VISIBILITIES = ("known", "private", "secret")

#: The lifecycle of an obligation. An obligation is an *input* to the mind: it
#: becomes a goal only when the character accepts it.
# ``forgotten`` is an offer nobody answered by its due tick; ``failed`` is an
# accepted obligation that passed its due tick unfulfilled (task-896).
OBLIGATION_STATUSES = ("offered", "accepted", "refused", "forgotten", "done", "failed")

OBLIGATION_DEFAULT_STATUS = "offered"

_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text):
    """A stable id from a goal's ``what`` text, e.g. "Become chief" -> "become_chief"."""
    return _SLUG.sub("_", str(text or "").strip().lower()).strip("_")


def _ref_list(value):
    """Normalise a ``blocks`` / ``links`` / ``achieve`` value.

    Accepts a list or a comma/semicolon string. Refs can be bare strings or
    dicts carrying ``ref`` and ``note`` (task-822).
    """
    if not value:
        return []
    if isinstance(value, str):
        value = value.replace(";", ",").split(",")
    out = []
    for item in value:
        if isinstance(item, dict):
            ref = str(item.get("ref") or "").strip()
            note = str(item.get("note") or "").strip()
            if ref:
                if note:
                    out.append({"ref": ref, "note": note})
                else:
                    out.append(ref)
        else:
            ref = str(item or "").strip()
            if ref:
                out.append(ref)
    return out


def _split_ref(ref):
    """('item', 'torch_01') from 'item:torch_01' or {'ref': 'item:torch_01'}."""
    if isinstance(ref, dict):
        text = str(ref.get("ref") or "").strip()
    else:
        text = str(ref or "").strip()
    if ":" in text:
        prefix, _, value = text.partition(":")
        return prefix.strip().lower(), value.strip()
    return "goal", text


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

        # Want and drive
        why = str(raw.get("why") or raw.get("motivation") or "").strip()
        if why:
            goal["why"] = why
            goal["motivation"] = why
        intention = str(raw.get("intention") or "").strip()
        if intention:
            goal["intention"] = intention
        hoped_for = str(raw.get("hoped_for") or "").strip()
        if hoped_for:
            goal["hoped_for"] = hoped_for

        # Provenance and standing
        if "source" in raw:
            raw_source = str(raw.get("source") or "self").strip()
            if raw_source.startswith(("self", "obligation:", "schedule:", "need:", "event:")):
                goal["source"] = raw_source
            else:
                goal["source"] = "self"

        if "opened_tick" in raw:
            try:
                goal["opened_tick"] = int(raw.get("opened_tick") or 0)
            except (TypeError, ValueError):
                goal["opened_tick"] = 0

        if "priority" in raw:
            try:
                goal["priority"] = int(raw.get("priority") or 0)
            except (TypeError, ValueError):
                goal["priority"] = 0

        if "visibility" in raw:
            vis = str(raw.get("visibility") or "known").strip().lower()
            if vis not in GOAL_VISIBILITIES:
                vis = "known"
            goal["visibility"] = vis

        # Shape: gate, target, relation
        for key in ("blocks", "achieve", "links"):
            if key in raw:
                refs = _ref_list(raw.get(key))
                if refs:
                    goal[key] = refs

        if "achieve_mode" in raw or "combinator" in raw:
            am = str(raw.get("achieve_mode") or raw.get("combinator") or "all").strip().lower()
            goal["achieve_mode"] = "any" if am == "any" else "all"

        if "deadline" in raw:
            dl = raw.get("deadline")
            if dl is not None:
                try:
                    goal["deadline"] = int(dl)
                except (TypeError, ValueError):
                    pass

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


def set_goal(goals, what, *, motivation="", why="", intention="", hoped_for="",
             source=None, opened_tick=None, priority=None, visibility=None,
             blocks=None, achieve=None, achieve_mode=None, links=None,
             deadline=None, status="active", tick=None, log=None):
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
    drive = str(why or motivation).strip()
    if drive:
        record["why"] = drive
        record["motivation"] = drive
    if str(intention).strip():
        record["intention"] = str(intention).strip()
    if str(hoped_for).strip():
        record["hoped_for"] = str(hoped_for).strip()
    if source is not None:
        record["source"] = source
    if opened_tick is not None:
        record["opened_tick"] = int(opened_tick)
    if priority is not None:
        record["priority"] = int(priority)
    if visibility is not None:
        record["visibility"] = visibility
    if blocks:
        record["blocks"] = _ref_list(blocks)
    if achieve:
        record["achieve"] = _ref_list(achieve)
    if achieve_mode is not None:
        record["achieve_mode"] = achieve_mode
    if links:
        record["links"] = _ref_list(links)
    if deadline is not None:
        record["deadline"] = int(deadline)

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


def goal_resolver(goals):
    """The ``goal`` resolver: a goal ref is met once the referenced goal is
    terminal (reached or dropped), or when no such goal exists."""
    by_id = {g["id"]: g for g in normalize(goals)}

    def met(ref):
        g = by_id.get(ref)
        return g is None or g["status"] in TERMINAL_STATUSES

    return met


def resolve_ref(ref, resolvers) -> bool:
    """True if *ref* is satisfied according to *resolvers*.

    Unknown prefixes fail closed (return False).
    """
    prefix, value = _split_ref(ref)
    predicate = resolvers.get(prefix)
    if predicate is None:
        return False
    try:
        return bool(predicate(value))
    except Exception:
        return False


def resolve_blocks(goal, resolvers):
    """The ``blocks`` refs of *goal* that are not yet satisfied."""
    outstanding = []
    for ref in goal.get("blocks") or []:
        if not resolve_ref(ref, resolvers):
            outstanding.append(ref)
    return outstanding


def is_blocked(goal, resolvers):
    """True when *goal* still has at least one unsatisfied ``blocks`` ref."""
    return bool(resolve_blocks(goal, resolvers))


def resolve_achieve(goal, resolvers):
    """(met, unmet) lists of refs for *goal*'s achieve list."""
    met = []
    unmet = []
    for ref in goal.get("achieve") or []:
        if resolve_ref(ref, resolvers):
            met.append(ref)
        else:
            unmet.append(ref)
    return met, unmet


def reached(goal, resolvers) -> bool:
    """True iff the goal's achieve predicates are satisfied.

    A goal without achieve predicates returns False.
    Combinator is 'all' (default) or 'any'.
    """
    achieve = goal.get("achieve") or []
    if not achieve:
        return False
    mode = str(goal.get("achieve_mode") or goal.get("combinator") or "all").strip().lower()
    met, unmet = resolve_achieve(goal, resolvers)
    if mode == "any":
        return len(met) > 0
    return len(unmet) == 0


def goal_progress(goal, resolvers) -> dict:
    """Projected progress over the world for *goal*. Never stored."""
    achieve = goal.get("achieve") or []
    met, unmet = resolve_achieve(goal, resolvers)
    return {
        "met": met,
        "unmet": unmet,
        "count": len(met),
        "total": len(achieve),
        "done": reached(goal, resolvers),
    }


def dispatch_goal_reached(graph, triggers, player, goal, game_state=None):
    """Dispatch a ``goal_reached`` event when a goal is reached (task-823).

    Raises world event ``goal_reached`` carrying actor and goal id,
    evaluated against ordinary triggers registered for ``on_goal_reached``
    or ``goal_reached``.
    """
    if graph is None or triggers is None or not goal:
        return []
    actor_name = getattr(player, "name", str(player))
    goal_id = goal.get("id") or goal.get("what", "")
    context = {
        "actor": actor_name,
        "target_name": actor_name,
        "triggering_character": player,
        "goal_id": goal_id,
        "goal": goal,
        "what": goal.get("what", ""),
        "event": "goal_reached",
        "event_type": "goal_reached",
        "trigger_type": "goal_reached",
        "game_state": game_state,
    }
    sources = set()
    for tt in ("goal_reached", "on_goal_reached"):
        if hasattr(graph, "get_trigger_sources"):
            sources.update(graph.get_trigger_sources(tt))

    pnode_id = f"player_{actor_name}".replace(" ", "_")
    pnode = graph.get_node(pnode_id) if hasattr(graph, "get_node") else getattr(graph, "nodes", {}).get(pnode_id)
    if pnode and (pnode.properties or {}).get("triggers"):
        sources.add(pnode.id)

    if not sources and hasattr(graph, "nodes"):
        nodes_dict = graph.nodes if isinstance(graph.nodes, dict) else {}
        for n in nodes_dict.values():
            props = getattr(n, "properties", {}) or {}
            for t in props.get("triggers", []):
                tt = t.get("trigger_type") if isinstance(t, dict) else ""
                if tt in ("goal_reached", "on_goal_reached") or (isinstance(tt, list) and any(x in ("goal_reached", "on_goal_reached") for x in tt)):
                    sources.add(n.id)

    outputs = []
    for source_id in sources:
        node = graph.get_node(source_id) if hasattr(graph, "get_node") else getattr(graph, "nodes", {}).get(source_id)
        if node is None:
            continue
        for tt in ("goal_reached", "on_goal_reached"):
            try:
                res = triggers._execute_triggers(
                    node,
                    tt,
                    context=context,
                    game_state=game_state,
                )
                if res:
                    outputs.extend(res)
            except Exception:
                pass
    return outputs


def sync_reached(player, resolvers, tick=None, log=None, on_goal_reached=None):
    """Evaluate active goals for *player*, moving satisfied goals to ``reached``
    and expired goals to ``dropped`` (task-822, task-823).

    Appends transitions to ``log`` if given, or to ``player.goal_log`` if present.
    When a goal flips to reached, raises ``goal_reached`` world event via
    ``on_goal_reached`` (task-823).
    Returns the updated goals list.
    """
    if not player:
        return []
    pgoals = getattr(player, "goals", None)
    if not pgoals:
        return []
    if log is None:
        log = getattr(player, "goal_log", None)
    if on_goal_reached is None and isinstance(resolvers, dict):
        on_goal_reached = resolvers.get("_on_goal_reached")

    for goal in pgoals:
        if goal.get("status") != "active":
            continue
        deadline = goal.get("deadline")
        if deadline is not None and tick is not None and int(tick) >= int(deadline):
            goal["status"] = "dropped"
            if log is not None:
                log.append(_event(goal, "dropped", tick))
            continue
        if reached(goal, resolvers):
            goal["status"] = "reached"
            if log is not None:
                log.append(_event(goal, "reached", tick))
            if on_goal_reached is not None:
                try:
                    on_goal_reached(player, goal)
                except Exception:
                    pass

    return pgoals


def outstanding_blocks(goals, resolvers):
    """``{goal_id: [refs still outstanding]}`` for every blocked goal."""
    out = {}
    for goal in normalize(goals):
        refs = resolve_blocks(goal, resolvers)
        if refs:
            out[goal["id"]] = refs
    return out


def with_blockers(goals, resolvers):
    """A copy of *goals* where each goal carries derived ``progress``
    and blocked goals carry derived ``blocked_by``.

    A projection for the payload and the UI, not persisted state: the stored goal
    keeps only its authored fields.
    """
    out = []
    for goal in normalize(goals):
        decorated = dict(goal)
        refs = resolve_blocks(goal, resolvers)
        if refs:
            decorated["blocked_by"] = refs
        decorated["progress"] = goal_progress(goal, resolvers)
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


def world_resolvers(graph, holder_id, goals=None, player=None, game_state=None):
    """Resolvers backed by the live world.

    ``goal`` uses the character's other goals;
    ``item`` is met when the holder carries or owns the node;
    ``character`` is met while the node exists;
    ``present`` is met when the character is co-located with holder;
    ``owns`` is met when the holder owns the node;
    ``tag`` is met when the target (or holder) carries the tag;
    ``flag`` is met when the player's flag is truthy;
    ``known`` is met when player knows/has seen the thing;
    ``at`` is met when holder is in the area;
    ``state`` is met when player state matches.
    """
    resolvers = {"goal": goal_resolver(goals or [])}
    if graph is None and player is None:
        return resolvers

    def held(node_id):
        try:
            from graph import EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
            node = graph.get_node(node_id) if graph else None
            if node is None and graph and node_id in graph.nodes:
                node = graph.nodes[node_id]
            for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
                if graph and any(e.source == node_id
                                 for e in graph.get_edges_for_target(holder_id, edge_type)):
                    return True
            if node is not None and getattr(node, 'type', None) == 'item' and graph:
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
            return graph.get_node(node_id) is not None if graph else False
        except Exception:
            return False

    def is_present(target_val):
        """Co-location: present:character:<name_or_id> or present:<name_or_id>."""
        try:
            if target_val.startswith("character:"):
                target_val = target_val.partition(":")[2]
            holder_area = None
            if player and getattr(player, "current_area", None):
                holder_area = player.current_area
            elif graph and holder_id:
                holder_area = graph.area_of(holder_id)

            if not holder_area:
                return False

            if game_state and hasattr(game_state, "player_manager"):
                tgt_p = game_state.player_manager.players.get(target_val)
                if tgt_p and getattr(tgt_p, "current_area", None):
                    return tgt_p.current_area == holder_area
            if graph:
                target_node = graph.get_node(target_val)
                if target_node:
                    tgt_area = graph.area_of(target_node.id)
                    if tgt_area:
                        return tgt_area == holder_area or getattr(graph.get_node(tgt_area), "name", None) == holder_area
        except Exception:
            return False
        return False

    def owns(node_id):
        try:
            if not graph:
                return False
            node = graph.get_node(node_id)
            if node is not None:
                from engine.items.ownership import owner_of
                return owner_of(node) == holder_id
        except Exception:
            return False
        return False

    def has_known(item_val):
        try:
            if player is not None:
                known_set = getattr(player, "known", None) or []
                if item_val in known_set:
                    return True
                if hasattr(player, "has_seen") and player.has_seen(item_val):
                    return True
        except Exception:
            return False
        return False

    def has_flag(flag_val):
        try:
            if player is not None:
                return bool((getattr(player, "flags", None) or {}).get(flag_val))
        except Exception:
            return False
        return False

    def has_tag(tag_val):
        try:
            parts = tag_val.split(":")
            if len(parts) == 3 and parts[0] == "character":
                cname, ctag = parts[1], parts[2]
                if game_state and hasattr(game_state, "player_manager"):
                    p_obj = game_state.player_manager.players.get(cname)
                    if p_obj:
                        return ctag in getattr(p_obj, "tags", [])
                if graph:
                    cnode = graph.get_node(cname)
                    if cnode:
                        return ctag in getattr(cnode, "tags", [])
                return False
            elif len(parts) == 2:
                nid, ntag = parts[0], parts[1]
                if graph:
                    n = graph.get_node(nid)
                    if n:
                        return ntag in getattr(n, "tags", [])
                return False
            else:
                if player and tag_val in getattr(player, "tags", []):
                    return True
                if graph and holder_id:
                    hnode = graph.get_node(holder_id)
                    if hnode and tag_val in getattr(hnode, "tags", []):
                        return True
        except Exception:
            return False
        return False

    def is_at(area_val):
        try:
            current = getattr(player, "current_area", None)
            if current:
                return current == area_val or (graph and getattr(graph.get_node(current), "name", None) == area_val)
            if graph and holder_id:
                h_area = graph.area_of(holder_id)
                return h_area == area_val or (getattr(graph.get_node(h_area), "name", None) == area_val)
        except Exception:
            return False
        return False

    def has_state(state_val):
        try:
            if player is not None:
                return getattr(player, "state", None) == state_val or getattr(player, "current_state", None) == state_val
        except Exception:
            return False
        return False

    resolvers["item"] = held
    resolvers["character"] = exists
    resolvers["present"] = is_present
    resolvers["owns"] = owns
    resolvers["known"] = has_known
    resolvers["flag"] = has_flag
    resolvers["tag"] = has_tag
    resolvers["at"] = is_at
    resolvers["state"] = has_state
    if game_state is not None:
        resolvers["_game_state"] = game_state
        if hasattr(game_state, "fire_goal_reached_triggers"):
            resolvers["_on_goal_reached"] = lambda p, g: game_state.fire_goal_reached_triggers(p, g)
        elif hasattr(game_state, "triggers") and graph is not None:
            resolvers["_on_goal_reached"] = lambda p, g: dispatch_goal_reached(graph, game_state.triggers, p, g, game_state)
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
        for key in ("from", "from_id", "reward", "goal_id"):
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


def _unique_obligation_id(records, charge):
    """``slug(charge)`` for the first offer; ``_2``, ``_3`` for later ones.

    Two issuers asking for the same thing are two offers, so the id cannot be
    the charge text alone. The first keeps the plain slug so legacy references
    keep resolving.
    """
    base = slug(charge)
    taken = {r["id"] for r in records}
    if base not in taken:
        return base
    n = 2
    while f"{base}_{n}" in taken:
        n += 1
    return f"{base}_{n}"


def offer_obligation(obligations, charge, *, from_name="", from_id="",
                     reward="", due=0):
    """Add an offered obligation. Returns ``(obligations, obligation, error)``.

    An offer is the world's side of the exchange: a mission, a promise owed, an
    appointment. It sits `offered` until the character answers it.

    *from_id* is the issuer's stable node id; *from_name* is the display
    provenance. The same issuer restating a still-open charge revises that
    offer in place; a different issuer asking for the same charge makes a
    distinct offer (task-896).
    """
    charge = str(charge or "").strip()
    if not charge:
        return normalize_obligations(obligations), None, "An obligation needs a charge."
    records = normalize_obligations(obligations)
    issuer_key = str(from_id or from_name or "").strip().lower()
    record = {"charge": charge, "status": "offered"}
    if str(from_name).strip():
        record["from"] = str(from_name).strip()
    if str(from_id).strip():
        record["from_id"] = str(from_id).strip()
    if str(reward).strip():
        record["reward"] = str(reward).strip()
    if due:
        record["due"] = int(due)
    for index, existing in enumerate(records):
        same_issuer = str(existing.get("from_id") or existing.get("from") or "").strip().lower() == issuer_key
        if (existing["charge"].lower() == charge.lower() and same_issuer
                and existing["status"] == "offered"):
            record["id"] = existing["id"]
            records[index] = record
            return records, record, None
    record["id"] = _unique_obligation_id(records, charge)
    records.append(record)
    return records, record, None


def issue_offer(world, issuer_key, recipient_ref, charge, *, reward="", due=0):
    """Explicit in-world offer from one character to another (task-896).

    The record lands on the *recipient's* ``Player.obligations``, with the
    issuer's stable node id in ``from_id`` and the display name in ``from``.
    This is the only path that writes into another character's obligations, and
    the two must share an area. Returns ``(obligation, error)``.
    """
    pm = world.player_manager
    issuer = pm.players.get(issuer_key)
    recipient = pm.players.get(recipient_ref)
    if recipient is None:
        wanted = str(recipient_ref or "").strip().lower()
        for key, p in pm.players.items():
            if str(getattr(p, "name", key)).lower() == wanted or str(key).lower() == wanted:
                recipient, recipient_ref = p, key
                break
    if issuer is None:
        return None, "You have no one to speak as."
    if recipient is None:
        return None, f"There is no {recipient_ref!r} to make an offer to."
    if recipient is issuer:
        return None, "You cannot make an offer to yourself."
    if getattr(recipient, "current_area", None) != getattr(issuer, "current_area", None):
        return None, f"{getattr(recipient, 'name', recipient_ref)} is not here."
    obs, record, error = offer_obligation(
        recipient.obligations, charge,
        from_name=getattr(issuer, "name", issuer_key),
        from_id=pm.get_player_node_id(issuer_key),
        reward=reward, due=due)
    if error:
        return None, error
    recipient.obligations = obs
    return record, None


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

    Accepting is the only answer that spawns a goal - the intention the
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
        if obligation["status"] == status:
            return records, goals, None  # repeated answer: no new goal, no new history
        obligation["status"] = status
        if status == "accepted":
            spawned, error = set_goal(
                goals or [],
                obligation["charge"],
                motivation=motivation,
                intention=intention or f"obligation to {obligation.get('from', 'someone')}",
                source=f"obligation:{obligation['id']}",
                tick=tick, log=log,
            )
            if error:
                return records, goals, error
            obligation["goal_id"] = slug(obligation["charge"])
            goals = spawned
    return records, goals, None


def expire_obligations(obligations, tick):
    """Apply the due tick: an unanswered offer is ``forgotten``; an accepted
    obligation still open past due is ``failed`` (task-896)."""
    records = normalize_obligations(obligations)
    for obligation in records:
        due = obligation.get("due") or 0
        if not due or tick < due:
            continue
        if obligation["status"] == "offered":
            obligation["status"] = "forgotten"
        elif obligation["status"] == "accepted":
            obligation["status"] = "failed"
    return records


def sync_obligations(obligations, goals):
    """Reconcile accepted obligations with their linked goals (task-896).

    A reached goal completes its obligation (``done``); a dropped goal fails
    it. Only ``accepted`` obligations move, so completion happens exactly once.
    Returns ``(obligations, changed_ids)``.
    """
    records = normalize_obligations(obligations)
    by_id = {g["id"]: g for g in normalize(goals)}
    changed = []
    for obligation in records:
        if obligation["status"] != "accepted":
            continue
        goal = by_id.get(obligation.get("goal_id") or "")
        if goal is None:
            continue
        if goal["status"] == "reached":
            obligation["status"] = "done"
            changed.append(obligation["id"])
        elif goal["status"] == "dropped":
            obligation["status"] = "failed"
            changed.append(obligation["id"])
    return records, changed


def describe_obligations(obligations):
    """A one-line summary, for the inspector and the `obligation` action."""
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
