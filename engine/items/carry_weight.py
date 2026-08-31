"""Carry-weight math for characters (encumbrance).

Moved verbatim from engine/item_actions.py as part of the task-314
verb-family split. Pure graph functions — no class context needed.
`engine.item_actions` re-exports the public names so existing imports
(routes, serialization, effects) keep working.
"""

from graph import EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN

#: base carry-weight capacity for a character (kg); scaled by trait
#: ``carry_capacity_mod`` effects (trait schema v2).
BASE_CARRY_CAPACITY = 100.0


def _node_effective_weight(node, is_equipped=False, container_mod=1.0) -> float:
    """Compute an item's effective weight for encumbrance.

    Applies ``equipped_weight_mod`` when *is_equipped* and
    ``container_weight_mod`` when nested inside a carried container.
    """
    weight = float(node.properties.get("weight", 0) or 0)
    if is_equipped:
        weight *= float(node.properties.get("equipped_weight_mod", 1.0) or 1.0)
    weight *= container_mod
    return weight


def _sum_container_contents(graph, container_id: str, container_mod: float) -> float:
    """Recursively sum effective weight of everything inside *container_id*."""
    total = 0.0
    for edge in graph.get_edges_for_target(container_id, EDGE_IN):
        node = graph.get_node(edge.source)
        if not node:
            continue
        total += _node_effective_weight(node, is_equipped=False, container_mod=container_mod)
        if "container" in [t.lower() for t in (node.properties.get("tags", []) or [])]:
            nested_mod = float(node.properties.get("container_weight_mod", 1.0) or 1.0)
            total += _sum_container_contents(graph, edge.source, container_mod * nested_mod)
    return total


def sum_carry_weight(graph, player_id: str) -> float:
    """Sum effective carry weight for all items carried/equipped by a player,
    including nested container contents with ``container_weight_mod`` applied."""
    total = 0.0
    carried_ids = set()
    equipped_ids = set()
    for edge in graph.get_edges_for_target(player_id, EDGE_CARRYING):
        carried_ids.add(edge.source)
    for edge in graph.get_edges_for_target(player_id, EDGE_EQUIPPED):
        equipped_ids.add(edge.source)

    for item_id in carried_ids:
        node = graph.get_node(item_id)
        if node:
            total += _node_effective_weight(node, is_equipped=False, container_mod=1.0)
            if "container" in [t.lower() for t in (node.properties.get("tags", []) or [])]:
                container_mod = float(node.properties.get("container_weight_mod", 1.0) or 1.0)
                total += _sum_container_contents(graph, item_id, container_mod)

    for item_id in equipped_ids:
        node = graph.get_node(item_id)
        if node:
            total += _node_effective_weight(node, is_equipped=True, container_mod=1.0)
            if "container" in [t.lower() for t in (node.properties.get("tags", []) or [])]:
                container_mod = float(node.properties.get("container_weight_mod", 1.0) or 1.0)
                total += _sum_container_contents(graph, item_id, container_mod)

    return total


def reconcile_item_weight(node) -> None:
    """Scale an item's weight by remaining uses when ``max_uses`` is tracked
    (task-155): ``weight = base_weight * (uses / max_uses)``.

    Items without ``max_uses`` (or with infinite uses, -1) keep static weight.
    ``base_weight`` is captured on first reconcile so repeated calls are
    idempotent. Callers: every place that decrements ``uses``.
    """
    props = node.properties
    max_uses = int(props.get("max_uses", 0) or 0)
    if max_uses <= 0:
        return
    uses = int(props.get("uses", -1) or 0)
    if uses < 0:
        return
    if "base_weight" not in props:
        props["base_weight"] = float(props.get("weight", 0) or 0)
    base = float(props.get("base_weight", 0) or 0)
    props["weight"] = round(base * (uses / max_uses), 3)


def get_carry_load_ratio(graph, player_manager, player_name: str = None) -> dict:
    """Return carry-weight stats for a character.

    Returns ``{"current": float, "capacity": float, "ratio": float}``.
    ``player_name`` defaults to the active player.
    """
    from engine.traits import TraitSystem
    player_name = player_name or player_manager.active_player
    player = player_manager.players.get(player_name)
    if not player:
        return {"current": 0.0, "capacity": 0.0, "ratio": 0.0}
    player_id_fn = getattr(player_manager, 'get_player_node_id', None) or getattr(player_manager, '_player_node_id', None)
    if player_id_fn is None:
        return {"current": 0.0, "capacity": 0.0, "ratio": 0.0}
    player_id = player_id_fn(player_name)
    capacity = BASE_CARRY_CAPACITY * TraitSystem.get_carry_capacity_mod(player)
    current = sum_carry_weight(graph, player_id)
    ratio = current / capacity if capacity > 0 else 0.0
    return {"current": current, "capacity": capacity, "ratio": ratio}
