"""Companion and reveal bookkeeping (task-391).

Three spell effects (``create_illusory_companion``, ``bind_companion``,
``reveal_hidden``) mark the world and then get out of the way; the actual
passage of time is handled here, once per turn.

This lives in its own module rather than inside the effect handlers because the
handlers run *inside* an action, and these effects are all duration-based: the
cast has to be over long before the thing expires. Keeping the sweep here also
means a spell author never has to think about the tick loop — they set a
``duration`` and it happens.

Called from ``engine/tick_manager.py`` on every turn, alongside the other
world-state sweeps. It is deliberately cheap and defensive: a companion whose
owner has vanished, or a reveal whose node was deleted mid-duration, is cleaned
up rather than raising.
"""

import logging

from graph import Edge, EDGE_IN

logger = logging.getLogger(__name__)


def _owner_player(gs, owner_name: str):
    """Resolve a companion's owner to a Player, or None if they are gone."""
    if not owner_name:
        return None
    players = getattr(gs, "players", {}) or {}
    if owner_name in players:
        return players[owner_name]
    needle = str(owner_name).lower()
    for key, player_obj in players.items():
        if str(key).lower() == needle:
            return player_obj
        if str(getattr(player_obj, "name", "")).lower() == needle:
            return player_obj
    return None


def _despawn_character(gs, key: str, player_obj) -> None:
    """Remove a character from the roster and the graph, cleanly.

    There is no engine-level despawn API (nothing else needed one before
    task-391), so this does the full teardown: both lookup maps, the anchor
    node, and its ``in`` edge. A companion that lingers half-removed shows up
    in every subsequent area description, so all four steps matter.
    """
    pm = getattr(gs, "player_manager", None)
    if pm is not None:
        players_by_id = getattr(pm, "_players_by_id", None)
        if isinstance(players_by_id, dict):
            players_by_id.pop(getattr(player_obj, "id", None), None)
        players_by_node = getattr(pm, "_players_by_node_id", None)
        node_id = None
        if isinstance(players_by_node, dict):
            node_id = players_by_node.pop(key, None)
        if node_id is None and pm.get_player_node_id:
            try:
                node_id = pm.get_player_node_id(key)
            except Exception:
                node_id = None
    else:
        node_id = getattr(player_obj, "node_id", None)

    players = getattr(gs, "players", None)
    if isinstance(players, dict):
        players.pop(key, None)
    if getattr(gs, "active_player", None) == key:
        gs.active_player = next(iter(players or {}), None)

    if node_id:
        try:
            gs.graph.remove_edges_for_node(node_id, EDGE_IN)
            gs.graph.remove_node(node_id)
        except Exception:
            logger.debug("[companions] node teardown failed for %s", node_id)


def expire_illusory_companions(gs) -> int:
    """Drop conjured companions whose duration ran out, or whose caster left.

    A conjured thing belongs to the moment it was made. It goes when its time is
    up, and — unless the author opted out — when the caster walks out of the
    area, because the fiction is that it exists only where they are paying
    attention to it.
    """
    players = getattr(gs, "players", {}) or {}
    tick = int(getattr(gs, "time_ticks", 0) or 0)
    removed = 0
    for key in list(players.keys()):
        player_obj = players.get(key)
        if player_obj is None or not getattr(player_obj, "illusory", False):
            continue

        expires = getattr(player_obj, "illusory_expires_tick", None)
        expired = expires is not None and tick >= int(expires)

        left = False
        if getattr(player_obj, "illusory_vanish_on_leave", True):
            owner = _owner_player(gs, getattr(player_obj, "illusory_owner", ""))
            if owner is not None and getattr(owner, "current_area", None) != getattr(
                player_obj, "current_area", None
            ):
                left = True

        if expired or left:
            _despawn_character(gs, key, player_obj)
            removed += 1
    return removed


def follow_bound_companions(gs) -> int:
    """Move ``bind_companion`` nodes into their owner's area.

    A bound familiar trails its caster: whenever the owner is somewhere the
    companion is not, the companion is moved there. This is what makes the
    Ember Companion worth casting — a light that stays with you.
    """
    graph = getattr(gs, "graph", None)
    if graph is None:
        return 0
    pm = getattr(gs, "player_manager", None)
    tick = int(getattr(gs, "time_ticks", 0) or 0)
    moved = 0

    for node in list(graph.nodes.values()):
        bond = (node.properties or {}).get("companion")
        if not isinstance(bond, dict):
            continue
        expires = bond.get("expires_tick")
        if expires is not None and tick >= int(expires):
            node.properties = dict(node.properties)
            node.properties.pop("companion", None)
            tags = [t for t in (node.properties.get("tags") or []) if t != "companion"]
            node.properties["tags"] = tags
            graph.nodes[node.id] = node
            continue

        owner = _owner_player(gs, bond.get("owner", ""))
        if owner is None or not getattr(owner, "current_area", None):
            continue
        owner_node_id = None
        if pm is not None and getattr(pm, "get_player_node_id", None):
            try:
                owner_node_id = pm.get_player_node_id(owner.name)
            except Exception:
                owner_node_id = None
        if not owner_node_id:
            continue
        try:
            area_node = graph.get_node(owner_node_id)
        except Exception:
            area_node = None
        if area_node is None:
            continue

        # Already with the owner? Nothing to do.
        for edge in graph.get_edges_for_source(node.id, EDGE_IN):
            if edge.target == owner_node_id:
                break
        else:
            graph.remove_edges_for_node(node.id, EDGE_IN)
            graph.add_edge(
                Edge(source=node.id, target=owner_node_id, type=EDGE_IN)
            )
            moved += 1
    return moved


def expire_reveals(gs) -> int:
    """Re-hide things ``reveal_hidden`` uncovered once the duration lapses.

    Restores the state each node was recorded in, not a blanket ``hidden`` — a
    door that was ``open`` when the spell found it must go back to ``open``.
    """
    graph = getattr(gs, "graph", None)
    if graph is None:
        return 0
    tick = int(getattr(gs, "time_ticks", 0) or 0)
    rehidden = 0

    for node in list(graph.nodes.values()):
        props = node.properties or {}
        if "_reveal_previous_state" not in props:
            continue
        expires = props.get("_reveal_expires_tick")
        if expires is not None and tick < int(expires):
            continue
        node.properties = dict(props)
        node.properties["current_state"] = node.properties.pop(
            "_reveal_previous_state", "hidden"
        )
        node.properties.pop("_reveal_expires_tick", None)
        graph.nodes[node.id] = node
        rehidden += 1
    return rehidden


def process_companions(gs) -> dict:
    """Run every task-391 sweep. Called once per turn from the tick manager."""
    try:
        illusory = expire_illusory_companions(gs)
    except Exception as exc:
        logger.warning("[companions] illusory expiry: %s", exc)
        illusory = 0
    try:
        followed = follow_bound_companions(gs)
    except Exception as exc:
        logger.warning("[companions] follow: %s", exc)
        followed = 0
    try:
        rehidden = expire_reveals(gs)
    except Exception as exc:
        logger.warning("[companions] reveal expiry: %s", exc)
        rehidden = 0
    return {"illusory_expired": illusory, "followed": followed, "rehidden": rehidden}
