"""Dynamic people/items glimpsed through open or see-through ways (task-201).

Extended by task-498 with a **chained** sightline: an observer sees along a run
of open or see-through ways, as long as the floor does not change and the run
does not turn. See :func:`sightline_run` for the chain and the two decisions the
task asked to have made explicitly.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from graph import EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT

_SPATIAL = (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT)

#: How many ways a sightline may run through before it stops (task-498).
#:
#: Configurable because it is a taste decision, not a fact, and a taste decision
#: belongs where it can be argued with. Three is the default because a run of
#: three open doorways is a corridor you can see down, and a run of four is
#: almost always a plan that has lost sight of its own exits. Higher values
#: compound: each step reports that room's contents, so a depth of five is
#: effectively an inventory of the building.
DEFAULT_SIGHTLINE_DEPTH = 3

_SIGHTLINE_CONFIG_KEY = "sightline.depth"


def sightline_depth() -> int:
    """The configured cap, clamped to something a sightline can be."""
    from engine.runtime_config import config

    try:
        value = int(config.get(_SIGHTLINE_CONFIG_KEY, DEFAULT_SIGHTLINE_DEPTH))
    except (TypeError, ValueError):
        return DEFAULT_SIGHTLINE_DEPTH
    return max(0, value)


def _way_floor(way_node) -> Optional[int]:
    """The storey a way sits on, or None when the world does not say."""
    props = (getattr(way_node, "properties", None) or {})
    floor = props.get("floor")
    if floor is None:
        return None
    try:
        return int(floor)
    except (TypeError, ValueError):
        return None


def _is_sight_passable(way_node) -> bool:
    """An open or see-through way. Anything else stops the line."""
    props = (getattr(way_node, "properties", None) or {})
    if props.get("see_through"):
        return True
    # Closed, locked, blocked, hidden: a wall. The state vocabulary is
    # `engine.barriers.WAY_STATES`, read through the same normalisation sound and
    # light use, so a new state cannot be "open by omission" here.
    from engine.barriers import declared_state

    return declared_state(way_node) == "open"


def sightline_run(graph, origin_area_id: str, direction: str, *,
                  depth: Optional[int] = None) -> List[Dict[str, Any]]:
    """Areas visible along a straight run of ways from *origin_area_id*.

    Returns ``[{"area_id", "area_name", "depth", "direction"}, ...]``, nearest
    first, excluding the origin. Two things break a chain, and both are the task's
    own rules:

    * **a floor step.** A way's ``floor`` is the storey it sits on, and a step
      between two ways means the line of sight leaves the storey it started on.
      Ways with no ``floor`` recorded are treated as level with each other,
      because a hand-placed way that never declared a storey has not claimed a
      different one.
    * **a turn.** The run continues only through the way *opposite* the one it
      came in by, so a corner stops it. You cannot see round a corner, and a
      chain that turned would report rooms behind the observer's shoulder.

    The cap is *depth*, not hops: one open way is what task-201 already did, and
    this returns the whole run so a caller can render the first step, the far end,
    or the lot.
    """
    cap = sightline_depth() if depth is None else max(0, int(depth))
    if cap <= 0 or not direction:
        return []

    # A straight run keeps the SAME compass direction at every hop. The graph
    # already encodes the turn: the edge out of a room names the direction the
    # way lies in, so looking east from a room whose only east way leads back the
    # way we came finds a way we have already seen and the run stops. Flipping the
    # direction each hop would walk back down the corridor we arrived by.
    #
    # The first hop is therefore the requested direction itself, not its opposite:
    # the origin's edge out of the room already carries the travel direction.
    seen: Set[str] = {origin_area_id}
    out: List[Dict[str, Any]] = []
    current = origin_area_id
    forward = direction
    floor = None
    floor_known = False

    for step in range(1, cap + 1):
        step_way, _step_direction = _forward_way(graph, current, forward)
        if step_way is None:
            break
        step_floor = _way_floor(step_way)
        if step_floor is not None:
            if floor_known and step_floor != floor:
                break                     # the run left the storey it started on
            floor, floor_known = step_floor, True

        target = _area_across(graph, step_way, current)
        if target is None or target in seen:
            break
        seen.add(target)
        node = graph.get_node(target)
        out.append({
            "area_id": target,
            "area_name": (getattr(node, "name", "") or target) if node else target,
            "depth": step,
            "direction": forward,
            "way_id": step_way.id,
            "floor": step_floor,
        })
        current = target
    return out


def _forward_way(graph, area_id: str, direction: str):
    """The way out of *area_id* in *direction*, as ``(way_node, direction)``."""
    from graph import EDGE_CONNECTION

    for edge in graph.get_edges_for_source(area_id, EDGE_CONNECTION):
        node = graph.get_node(edge.target)
        if not node or node.type != "way":
            continue
        this_way = str(edge.properties.get("direction") or "")
        if this_way and this_way != direction:
            continue
        if not _is_sight_passable(node):
            continue
        return node, this_way
    return None, direction


def _area_across(graph, way_node, from_area_id: str) -> Optional[str]:
    """The area on the far side of *way_node* from *from_area_id*."""
    from graph import EDGE_CONNECTION

    for edge in graph.get_edges_for_source(way_node.id, EDGE_CONNECTION):
        target = edge.target
        if target and target != from_area_id:
            node = graph.get_node(target)
            if node is not None and node.type == "area":
                return str(target)
    return None


def normalize_visible_items(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        text = raw.strip()
        return [text] if text else []
    if isinstance(raw, list):
        return [str(name).strip() for name in raw if str(name).strip()]
    return []


def collect_items_in_area(graph, area_id: str, allowed_names: Optional[List[str]] = None) -> List[str]:
    """Return item names present in *area_id* (direct, spatial, container contents)."""
    allowed = {n.lower() for n in allowed_names} if allowed_names else None
    items: List[str] = []
    seen = set()

    def maybe_add(node) -> None:
        if not node or node.type != "item":
            return
        if node.properties.get("current_state") == "hidden":
            return
        if node.id in seen:
            return
        if allowed is not None and node.name.lower() not in allowed:
            return
        seen.add(node.id)
        items.append(node.name)

    anchor_ids = set()
    for edge in graph.get_edges_for_target(area_id, EDGE_IN):
        node = graph.get_node(edge.source)
        if node and node.type == "item":
            maybe_add(node)
            anchor_ids.add(node.id)

    anchors = set(anchor_ids)
    anchors.add(area_id)
    for edge in graph.edges:
        if edge.type in _SPATIAL and edge.target in anchors:
            maybe_add(graph.get_node(edge.source))

    for item_id in list(seen):
        container = graph.get_node(item_id)
        if not container or container.type != "item":
            continue
        if container.properties.get("current_state") == "locked":
            continue
        for edge in graph.get_edges_for_target(item_id, EDGE_IN):
            maybe_add(graph.get_node(edge.source))

    return items


def _character_beyond_label(player_manager, pdata, active_player_obj) -> str:
    from engine.activities import activity_description

    pname = pdata["name"]
    pstate = pdata.get("state", "awake")
    known = active_player_obj is not None and active_player_obj.has_met(pname)
    if known:
        label = pname
    else:
        target_player = player_manager.players.get(pname)
        label = target_player.unknown_display_name() if target_player else pname
    if pstate in ("dead", "ghost"):
        return f"{label} (ghost)"
    activity = getattr(player_manager.players.get(pname), "activity", None)
    if activity and activity.get("visible", True):
        act_text = activity_description(activity)
        if act_text:
            return f"{label} ({act_text})"
    if pstate != "awake":
        return f"{label} ({pstate})"
    return label


def build_beyond_suffix(graph, player_manager, target_area_id, target_area_name, edge_props, active_player_obj) -> str:
    """Suffix for exit/examine lines, e.g. ' Beyond you can see: Lyrie, the clock.'"""
    allow_chars = bool(edge_props.get("allow_see_characters"))
    visible_items = normalize_visible_items(edge_props.get("visible_items"))
    if not allow_chars and not visible_items:
        return ""

    parts: List[str] = []
    if allow_chars and target_area_name:
        for pdata in player_manager.get_players_in_area(target_area_name):
            parts.append(_character_beyond_label(player_manager, pdata, active_player_obj))

    if visible_items and target_area_id:
        for name in collect_items_in_area(graph, target_area_id, visible_items):
            parts.append(f"the {name}")

    if not parts:
        return ""
    return f" Beyond you can see: {', '.join(parts)}."


#: What a chained sightline discloses, and what it does not (task-498).
#:
#: The task asked this to be decided and recorded rather than left implicit, so:
#:
#: **A sightline reveals a room's NAME and who or what is standing in it. It never
#: reveals that room's exits, its description, or anything past it.**
#:
#: Contents are included because excluding them would be inconsistent with the
#: depth-1 behaviour task-201 established and would make a corridor report *less*
#: the further you could see, which is backwards. Exits and descriptions are
#: excluded because those are the parts that would let a character navigate a
#: floor they have not walked — which is task-499's fog of war, and a sightline
#: that hands over the exits undoes it without anyone deciding that it should.
#: A third step's contents are one step further from the eye than the first's, but
#: they are still in a straight line of sight, so they are reported; the depth cap
#: is what bounds the compounding.
def chained_sightline_summary(graph, player_manager, run: List[Dict[str, Any]],
                              active_player_obj) -> str:
    """A ``' Through the corridor you can see: ...'`` clause for a *run*.

    Empty when the run is empty or nothing is visible down it, so a caller can
    concatenate unconditionally.
    """
    if not run:
        return ""
    seen_people: List[str] = []
    seen_items: List[str] = []
    # The room that produced the most recent sighting, so the clause can say
    # *where* down the line rather than naming the far room on its own — the
    # content is what matters and the room is only useful as a pointer to it.
    content_room = ""
    for step in run:
        area_id = str(step.get("area_id") or "")
        area_name = str(step.get("area_name") or area_id or "")
        if not area_name:
            continue
        found_here = False
        for pdata in player_manager.get_players_in_area(area_name):
            label = _character_beyond_label(player_manager, pdata, active_player_obj)
            found_here = True
            if label not in seen_people:
                seen_people.append(label)
        for name in collect_items_in_area(graph, area_id):
            found_here = True
            if name not in seen_items:
                seen_items.append(name)
        if found_here:
            content_room = area_name

    if not seen_people and not seen_items:
        return ""
    parts = seen_people + [f"the {n}" for n in seen_items]
    where = f", in {content_room}," if content_room else ""
    lead = "far down the line" if len(run) > 1 else "beyond"
    return f" {lead.capitalize()} you can make out{where} {', '.join(parts)}."
