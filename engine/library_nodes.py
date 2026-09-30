"""Public, deterministic library-item node builder (task-398).

`routes/library_ops.py::_spawn_library_item_node` builds a world node from a
library entry, but it is a route-private helper that takes a Flask `app`,
mutates a graph, and mints node ids from `time.time()` plus `random.randint`.
That is fine for "a player picks up an item" and useless for a generator: a
recipe has to be able to say *which* node it wants, build it without touching a
graph, and produce the same patch for the same seed.

So the property mapping lives here, once, and both callers use it:

  - the route keeps its clock-based id and its graph mutation, and delegates the
    properties;
  - a generation recipe passes a stable, scoped `node_id` and gets back a `Node`
    plus the nodes and edges for its contents and triggers, ready to stage into
    a `GenerationPatch`.

Nothing here imports Flask or a graph. `lookup` is injected, so the same
function serves the route, a generator, and a test.
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional, Tuple

from graph import (
    EDGE_AT,
    EDGE_BEHIND,
    EDGE_BESIDE,
    EDGE_IN,
    EDGE_ON,
    EDGE_TRIGGERS,
    EDGE_UNDER,
    Edge,
    Node,
)

#: relation name -> graph edge type. `routes/graph_ops.py` and
#: `routes/library_ops.py` each kept their own copy; this is the engine-side one
#: so a generator and the route agree on what "on" means.
RELATION_EDGE_TYPES = {
    "in": EDGE_IN,
    "on": EDGE_ON,
    "under": EDGE_UNDER,
    "behind": EDGE_BEHIND,
    "beside": EDGE_BESIDE,
    "at": EDGE_AT,
}

#: spatial relations a library `contents` ref may use
_SPATIAL_RELATIONS = ("in", "on", "under", "behind", "beside", "at")


def library_item_properties(lib_item: dict, library_id: str,
                            extra: Optional[dict] = None) -> dict:
    """The ``properties`` every materialised library item node carries.

    One definition, so a library entry placed by a player and the same entry
    placed by a recipe are the same node. `extra` is merged last and is how a
    generator attaches provenance without this module knowing what provenance
    is.
    """

    props: Dict = {
        "description": lib_item.get("description", ""),
        "uses": _int(lib_item.get("uses", -1)),
        "weight": _float(lib_item.get("weight", 0.1)),
        "action_costs": lib_item.get("action_costs", {}),
        "skill_check": lib_item.get("skill_check", {}),
        "equip_slots": lib_item.get("equip_slots", []),
        "tags": lib_item.get("tags", []),
        "current_state": "hidden" if lib_item.get("hidden", False)
                         else lib_item.get("current_state", "normal"),
        "light_level": lib_item.get("light_level", "dim"),
        "target_temperature": lib_item.get("target_temperature"),
        "heating_rate": lib_item.get("heating_rate"),
        "sound_level": lib_item.get("sound_level"),
        "sound_pattern": lib_item.get("sound_pattern"),
        "stun_chance": lib_item.get("stun_chance"),
        "stun_duration": lib_item.get("stun_duration"),
        "library_id": library_id,
        "defense": lib_item.get("defense", 0),
        "damage": lib_item.get("damage", 0),
        "insulation": lib_item.get("insulation", 0),
        "resistances": lib_item.get("resistances", {}),
        "image": lib_item.get("image") or None,
    }
    # Gauges (task-410: a plant's `growth` counter). Without this the counter is
    # dropped at placement, so the item's own triggers can never see it.
    if lib_item.get("parameters"):
        props["parameters"] = dict(lib_item["parameters"])
    if extra:
        props.update(extra)
    return props


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def content_ref_id(ref) -> Optional[str]:
    if isinstance(ref, str):
        return ref.strip() or None
    if isinstance(ref, dict):
        return ref.get("id") or None
    return None


def content_relation(ref, default: str = "in") -> str:
    if isinstance(ref, dict):
        rel = (ref.get("relation") or default)
        rel = str(rel).strip().lower()
        if rel in _SPATIAL_RELATIONS:
            return rel
    return default


def build_item_node(library_id: str, lib_item: dict, node_id: str,
                    extra: Optional[dict] = None) -> Node:
    """The item node itself. Deterministic: no clock, no RNG, no graph."""
    # Imported here rather than at module scope so this file has no import-time
    # dependency on the actions normaliser; `engine.item_actions` is where the
    # route gets it from too, so there is one definition either way.
    from engine.item_actions import normalize_item_actions

    props = library_item_properties(lib_item, library_id, extra)
    props["actions"] = normalize_item_actions(lib_item.get("actions", "examine,take,use"))
    return Node(id=node_id, type="item",
                name=lib_item.get("name", library_id), properties=props)


def build_item_subtree(library_id: str, lib_item: dict, node_id: str,
                       lookup: Callable[[str], Optional[dict]],
                       extra: Optional[dict] = None) -> Tuple[List[Node], List[Edge], List[str]]:
    """A library item and everything it contains, as nodes and edges.

    Returns ``(nodes, edges, missing_content_ids)``. Child and trigger ids are
    derived from ``node_id`` and their position, so the same library entry
    staged twice produces the same ids — which is what lets
    :func:`engine.generation.apply_patch` reject a duplicate generation rather
    than writing a second copy under a fresh name.

    `extra` is merged into the item node's properties *and* into every
    descendant's, because a generator stamps one `generated` fragment over the
    whole subtree and a child missing it would read as hand-authored — which is
    exactly the state a later regenerate is allowed to overwrite.

    `missing_content_ids` is returned rather than logged: a recipe must be able
    to say "this library entry references something that does not exist" in its
    report instead of quietly shipping a box with nothing in it.
    """
    nodes: List[Node] = [build_item_node(library_id, lib_item, node_id, extra)]
    edges: List[Edge] = []
    missing: List[str] = []

    for i, ref in enumerate(lib_item.get("contents") or []):
        child_id = content_ref_id(ref)
        if not child_id:
            continue
        child_entry = lookup(child_id)
        if not child_entry:
            missing.append(child_id)
            continue
        child_node_id = f"{node_id}_content_{i}"
        child_nodes, child_edges, child_missing = build_item_subtree(
            child_id, child_entry, child_node_id, lookup, extra=extra)
        nodes.extend(child_nodes)
        edges.extend(child_edges)
        missing.extend(child_missing)
        edges.append(Edge(source=child_node_id, target=node_id,
                          type=RELATION_EDGE_TYPES.get(
                              content_relation(ref), EDGE_IN)))

    for i, trigger_data in enumerate(lib_item.get("triggers") or []):
        trigger_node, trigger_edge = build_trigger_node(
            node_id, trigger_data, i, extra)
        if trigger_node is not None:
            nodes.append(trigger_node)
            edges.append(trigger_edge)

    return nodes, edges, missing


def build_trigger_node(owner_id: str, trigger_data: dict, index: int,
                       extra: Optional[dict] = None) -> Tuple[Optional[Node], Optional[Edge]]:
    """A trigger node and its edge, with a deterministic id.

    The id is ``trigger_<owner>_<type>_<index>``: derived, not minted from a
    clock, so re-running a recipe cannot produce a second copy of the same
    trigger under a new name.
    """
    trigger_type = trigger_data.get("trigger_type", "on_examine")
    effect_type = trigger_data.get("effect_type", "message")
    effect_params = trigger_data.get("effect_params", {})
    target_name = trigger_data.get("target_name", "")
    condition = trigger_data.get("condition")
    conditions = trigger_data.get("conditions", [])
    effects = trigger_data.get("effects", [])
    target_tag = trigger_data.get("target_tag", "")

    trigger_id = f"trigger_{owner_id}_{trigger_type}_{index}"
    props: Dict = {"trigger_type": trigger_type, "target_name": target_name}
    if target_tag:
        props["target_tag"] = target_tag
    if effects:
        props["effects"] = effects
    else:
        props["effect_type"] = effect_type
        props["effect_params"] = effect_params
    if condition:
        props["condition"] = condition
    if conditions:
        props["conditions"] = conditions
    if extra:
        props.update(extra)

    first_effect_type = (effects[0].get("type") if effects else None) or effect_type
    node = Node(id=trigger_id, type="logic_trigger",
                name=f"{trigger_type} → {first_effect_type}", properties=props)
    return node, Edge(source=owner_id, target=trigger_id, type=EDGE_TRIGGERS,
                      properties=dict(props))


def spatial_edge(source: str, target: str, relation: str = "in") -> Edge:
    """A spatial placement edge in the existing relation vocabulary."""
    return Edge(source=source, target=target,
                type=RELATION_EDGE_TYPES.get(str(relation).lower(), EDGE_IN))
