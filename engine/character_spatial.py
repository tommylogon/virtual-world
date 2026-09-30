"""Character spatial position — relations to ways, items, and characters (task-135).

Position is a *relation*, not a coordinate (task-419). There is no metric space
inside an area; a character's position is the set of spatial edges it holds, and
a character holds exactly one `at` edge in the world at a time. The consequences
are spelled out where they are implemented:

  - `enforce_single_at` / `check_spatial_invariants` — the one-`at` invariant, and
    a validator for the paths that write edges without going through the setter.
  - `proximity_hops` / `proximity_phrase` — 1 hop / 2 hops / across the room,
    derived by walking the relation path. Never stored, so a re-authored `beside`
    edge cannot leave a stale distance behind.
  - `spawn_from_pool` / `select_area_anchors` — the anchor vocabulary (a pooled
    resource, a landmark cluster) and its 3-8 per-area budget.
  - `apply_positional_fidelity` — positional detail allocated by the same
    attendance decision as attention, which is what keeps `at` at O(cap).
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from graph import (
    EDGE_AT,
    EDGE_BESIDE,
    EDGE_BEHIND,
    EDGE_CONNECTION,
    EDGE_IN,
    EDGE_ON,
    EDGE_UNDER,
    SPATIAL_EDGE_TYPES,
    Edge,
    Node,
)

_CHARACTER_POSITION_TYPES = tuple(SPATIAL_EDGE_TYPES)


# ── Duck-typed helpers (combat tests patch methods, not attributes) ──────────

def _pm_get_player(player_manager, name: str):
    """Look up a player by name — prefer ``get_player`` (tests patch it)."""
    getter = getattr(player_manager, "get_player", None)
    if callable(getter):
        return getter(name)
    players = getattr(player_manager, "players", None)
    if isinstance(players, dict):
        return players.get(name)
    return None


def _pm_get_player_node_id(player_manager, name: str) -> Optional[str]:
    getter = getattr(player_manager, "get_player_node_id", None)
    if callable(getter):
        return getter(name)
    getter = getattr(player_manager, "player_node_id", None)
    if callable(getter):
        return getter(name)
    helper = getattr(player_manager, "_player_node_id", None)
    if callable(helper):
        return helper(name)
    from engine.node_ids import NodeIDHelper
    return NodeIDHelper.player_node_id(name)


def _pm_active_player(player_manager) -> Optional[str]:
    active = getattr(player_manager, "active_player", None)
    if active is not None:
        return active
    pm = getattr(player_manager, "player_manager", None)
    if pm is not None:
        return getattr(pm, "active_player", None)
    return None


def _pm_current_area_name(player_manager) -> Optional[str]:
    """Return the current area *name* (not node id) for the active player."""
    area = getattr(player_manager, "current_area", None)
    if area is not None:
        name = getattr(area, "name", None)
        if name:
            return name
        if isinstance(area, str):
            return area
    helper = getattr(player_manager, "_get_current_area_id", None)
    if callable(helper):
        area_id = helper()
        if area_id:
            return area_id.replace("area_", "").replace("_", " ")
    active_name = _pm_active_player(player_manager)
    if active_name:
        player = _pm_get_player(player_manager, active_name)
        if player is not None:
            current = getattr(player, "current_area", None)
            if current:
                return current
    return None

_RELATION_PHRASES = (
    ("from below", EDGE_UNDER),
    ("on top of", EDGE_ON),
    ("next to", EDGE_BESIDE),
    ("underneath", EDGE_UNDER),
    ("under", EDGE_UNDER),
    ("beneath", EDGE_UNDER),
    ("below", EDGE_UNDER),
    ("behind", EDGE_BEHIND),
    ("beside", EDGE_BESIDE),
    ("near", EDGE_AT),
    ("at", EDGE_AT),
    ("on", EDGE_ON),
)


def _normalize_tags(node) -> List[str]:
    if not node:
        return []
    props = getattr(node, "properties", None) or {}
    return [str(t).lower().strip() for t in props.get("tags", []) or []]


def is_transit_area(area_node) -> bool:
    if not area_node or area_node.type != "area":
        return False
    props = area_node.properties or {}
    if props.get("transit"):
        return True
    tags = _normalize_tags(area_node)
    return "transit" in tags or "passage" in tags


def clear_character_position_edges(graph, player_node_id: str) -> None:
    for edge_type in _CHARACTER_POSITION_TYPES:
        for edge in list(graph.get_edges_for_source(player_node_id, edge_type)):
            graph.remove_edge(edge.source, edge.target, edge.type)


def set_character_position(
    graph,
    player_node_id: str,
    target_id: str,
    relation: str = EDGE_AT,
) -> None:
    if not player_node_id or not target_id:
        return
    if relation not in SPATIAL_EDGE_TYPES:
        relation = EDGE_AT
    target = graph.get_node(target_id)
    if not target or target.type not in ("way", "item", "character", "player"):
        return
    clear_character_position_edges(graph, player_node_id)
    graph.add_edge(Edge(source=player_node_id, target=target_id, type=relation))


# ── The one-`at` invariant (task-419) ──────────────────────────────────────
#
# Position is a *relation*, not a coordinate, and a character holds exactly one
# `at` edge in the whole world at a time — not one per target. That is what
# keeps the edge set at O(population) instead of O(n²): 40 characters in an area
# are 40 `in <area>` edges and at most `cap` `at` edges, not 40 × 40 pairs.
#
# `set_character_position` already clears first, so the invariant holds on the
# path everything uses. `enforce_single_at` exists for the other path: an effect
# handler, an NL edit, or a load file that wrote an `at` edge directly.

MAX_AT_EDGES_PER_CHARACTER = 1


def enforce_single_at(graph, player_node_id: str, keep_target: Optional[str] = None) -> int:
    """Reduce a character's `at` edges to at most one. Returns how many were removed.

    Deterministic when there is more than one: the lexicographically smallest
    target survives, unless `keep_target` names one — a caller that just moved
    someone should not have the move silently undone by an older edge.
    """
    if not player_node_id:
        return 0
    targets = sorted(edge.target for edge in
                     graph.get_edges_for_source(player_node_id, EDGE_AT))
    if keep_target is not None and keep_target in targets:
        survivors = [keep_target]
    elif targets:
        survivors = targets[:MAX_AT_EDGES_PER_CHARACTER]
    else:
        return 0
    removed = 0
    for target in targets:
        if target in survivors:
            continue
        graph.remove_edge(player_node_id, target, EDGE_AT)
        removed += 1
    return removed


def clear_at(graph, player_node_id: str) -> int:
    """Remove every `at` edge. This is *demotion*, not deduplication.

    `enforce_single_at` reduces to at most one and deliberately keeps the last
    one — a character standing at nothing is still standing somewhere. Taking
    the position away entirely is a different decision, made when a character
    stops being attended, so it gets its own function rather than a flag.
    """
    if not player_node_id:
        return 0
    removed = 0
    for edge in list(graph.get_edges_for_source(player_node_id, EDGE_AT)):
        graph.remove_edge(edge.source, edge.target, edge.type)
        removed += 1
    return removed


def check_spatial_invariants(graph) -> List[Dict[str, Any]]:
    """Every violation of the spatial invariants this model depends on.

    The task asks for a validator, not just a test, because these are properties
    a save file or an NL edit can break without any code running. Each entry is
    `{"kind", "character_id", "detail"}` so a caller can report or repair them.
    """
    violations: List[Dict[str, Any]] = []
    for node in graph.nodes.values():
        if node.type not in ("player", "character"):
            continue
        at_targets = [e.target for e in graph.get_edges_for_source(node.id, EDGE_AT)]
        if len(at_targets) > MAX_AT_EDGES_PER_CHARACTER:
            violations.append({
                "kind": "multiple_at_edges",
                "character_id": node.id,
                "detail": f"holds {len(at_targets)} 'at' edges: {sorted(at_targets)}",
            })
        for target_id in at_targets:
            target = graph.get_node(target_id)
            if target is None:
                violations.append({
                    "kind": "dangling_at_edge",
                    "character_id": node.id,
                    "detail": f"'at' points at missing node {target_id!r}",
                })
            elif target.type not in ("way", "item", "character", "player"):
                violations.append({
                    "kind": "at_non_anchor_target",
                    "character_id": node.id,
                    "detail": f"'at' points at a {target.type} ({target_id!r}), "
                              "which is not an interaction target",
                })
    return violations


# ── Proximity is derived from the relation path, never stored (task-419) ──
#
# `at` is binary on its own, but composed with `beside` / `on` / `under` it
# yields an ordered, discrete proximity:
#
#     you --at--> boulder --beside--> old oak
#
#   1 hop       you are at it
#   2 hops      it is a neighbour of your anchor
#   unreachable elsewhere in the area — the prose says "across the room"
#
# There is no coordinate system. The `beside` chain *is* the coordinate system,
# so the distance has to be walked, never cached: caching it would let a
# re-authored `beside` edge leave a stale proximity behind.

PROXIMITY_AT = 1
PROXIMITY_NEAR = 2
PROXIMITY_ACROSS_ROOM = "across the room"


def proximity_hops(graph, from_node_id: str, target_id: str,
                   max_hops: int = 2) -> Optional[int]:
    """Relational distance 1 / 2 / None, walked from `from_node_id` right now.

    `None` means unreachable *by this model*, which the prose renders as
    "across the room" — it does not mean the target does not exist, only that
    nothing links the viewer to it.
    """
    if not from_node_id or not target_id:
        return None
    if from_node_id == target_id:
        return 0
    seen = {from_node_id}
    frontier = [(from_node_id, 0)]
    while frontier:
        node_id, depth = frontier.pop(0)
        if depth >= max_hops:
            continue
        for edge in graph.get_edges_for_source(node_id, EDGE_AT):
            if edge.target == target_id:
                return depth + 1
            if edge.target not in seen:
                seen.add(edge.target)
                frontier.append((edge.target, depth + 1))
        # Step off the anchor to whatever it is beside / on / under. This is the
        # second hop, and the only reason `max_hops=2` means anything.
        for anchor_id in [e.target for e in graph.get_edges_for_source(node_id, EDGE_AT)]:
            for edge_type in (EDGE_BESIDE, EDGE_ON, EDGE_UNDER, EDGE_BEHIND):
                for edge in graph.get_edges_for_source(anchor_id, edge_type):
                    if edge.target == target_id:
                        return depth + 2
                    if edge.target not in seen:
                        seen.add(edge.target)
                        frontier.append((edge.target, depth + 2))
    return None


def proximity_phrase(graph, from_node_id: str, target_id: str) -> str:
    """The derived phrase. Nothing here is stored on either node."""
    hops = proximity_hops(graph, from_node_id, target_id)
    if hops == PROXIMITY_AT:
        return "at"
    if hops == PROXIMITY_NEAR:
        return "by"
    if hops in (0, None):
        return PROXIMITY_ACROSS_ROOM
    return PROXIMITY_ACROSS_ROOM


# ── Anchor vocabulary and budget (task-419) ───────────────────────────────
#
# A wilderness area does not need 500 rocks. It needs a few anchors the prose
# layer expands into "rocks", "undergrowth", "fallen oak". Two shapes, both
# already expressible as ordinary nodes:
#
#   pooled resource  "gravel on the ground" — one node, described as a
#                    quantity, spawning a bounded handful on use and depleting.
#                    Same model as the berry thicket.
#   landmark cluster "boulder by the old oak" — two nodes joined by `beside`,
#                    either of which may be the `at` target.

ANCHOR_KINDS = ("pooled", "landmark")
ANCHOR_BUDGET_MIN = 3
ANCHOR_BUDGET_MAX = 8


def is_pool_anchor(node) -> bool:
    props = getattr(node, "properties", None) or {}
    return props.get("anchor_kind") == "pooled"


def pool_remaining(node) -> int:
    props = getattr(node, "properties", None) or {}
    pool = props.get("pool")
    if not isinstance(pool, dict):
        return 0
    return max(0, int(pool.get("remaining", 0)))


def describe_pool(node) -> str:
    """A pool is *described* as a quantity; the quantity is the property."""
    props = getattr(node, "properties", None) or {}
    pool = props.get("pool") or {}
    unit = pool.get("unit") or "unit"
    return f"{pool_remaining(node)} {unit}{'' if pool_remaining(node) == 1 else 's'}"


def spawn_from_pool(graph, anchor_node, area_id: Optional[str] = None,
                    wanted: Optional[int] = None) -> List[str]:
    """Take a bounded handful from a pooled anchor. Returns the spawned item ids.

    Bounded three ways, all three of which have to hold or "gravel" is a way to
    manufacture items: at most `max_spawn` per call, at most `remaining` in
    total, and never more than asked for. Spawned items are real nodes in the
    area, not a description — that is the whole difference between a pool and an
    infinite scenery item.
    """
    if not is_pool_anchor(anchor_node) or anchor_node.type != "item":
        return []
    pool = dict(anchor_node.properties.get("pool") or {})
    remaining = max(0, int(pool.get("remaining", 0)))
    if remaining <= 0:
        return []
    max_spawn = max(0, int(pool.get("max_spawn", 1)))
    if max_spawn <= 0:
        return []
    ask = max_spawn if wanted is None else max(0, int(wanted))
    count = min(max_spawn, remaining, ask)
    if count <= 0:
        return []

    area_id = area_id or _pool_area(graph, anchor_node)
    if not area_id:
        return []
    template = pool.get("item") or {}
    spawned = []
    for i in range(count):
        item_id = f"{anchor_node.id}_spawn_{int(pool.get('spawned', 0)) + i}"
        if graph.get_node(item_id) is not None:
            continue
        props = dict(template)
        props["spawned_from"] = anchor_node.id
        graph.add_node(Node(id=item_id, type="item",
                            name=template.get("name") or anchor_node.name,
                            properties=props))
        graph.add_edge(Edge(source=item_id, target=area_id, type=EDGE_IN))
        spawned.append(item_id)

    pool["remaining"] = remaining - len(spawned)
    pool["spawned"] = int(pool.get("spawned", 0)) + len(spawned)
    anchor_node.properties["pool"] = pool
    return spawned


def _pool_area(graph, anchor_node) -> Optional[str]:
    for edge in graph.get_edges_for_source(anchor_node.id, EDGE_IN):
        if graph.get_node(edge.target) and graph.get_node(edge.target).type == "area":
            return edge.target
    return None


def area_anchor_candidates(graph, area_id: str) -> List[Any]:
    """Anchor-shaped nodes in an area, cheapest-first: the pool, the cluster, the rest."""
    found = []
    for edge in graph.get_edges_for_target(area_id, EDGE_IN):
        node = graph.get_node(edge.source)
        if node is None or node.type != "item":
            continue
        props = node.properties or {}
        if props.get("anchor_kind") in ANCHOR_KINDS or props.get("anchor"):
            found.append(node)
    # Sorted by id so the budget is reproducible from a fixed world.
    found.sort(key=lambda n: n.id)
    return found


def select_area_anchors(graph, area_id: str,
                        budget: int = ANCHOR_BUDGET_MAX) -> List[str]:
    """The area's anchors, within budget, chosen deterministically.

    Pools first: one pooled node is what turns "a patch of gravel" into
    "gravel on the ground", so it buys more per node than a single rock. Then
    landmark clusters, then whatever else claims to be an anchor. Ties break by
    node id, so the same world always yields the same anchors.
    """
    budget = max(ANCHOR_BUDGET_MIN, min(ANCHOR_BUDGET_MAX, int(budget)))
    candidates = area_anchor_candidates(graph, area_id)

    def rank(node):
        kind = (node.properties or {}).get("anchor_kind")
        if kind == "pooled":
            return 0
        if kind == "landmark":
            return 1
        return 2

    ordered = sorted(candidates, key=lambda n: (rank(n), n.id))
    return [n.id for n in ordered[:budget]]


# ── Positional fidelity is an attendance tier (task-419) ───────────────────
#
# This is what keeps `at` cheap. Positional detail is allocated by the same
# decision that allocates attention (task-418/411):
#
#   background / co-present  ->  `in <area>` only            population
#   attended                  ->  `in <area>` + `at <anchor>`  <= cap
#
# 40 characters in an area produce 40 `in` edges and at most 8 `at` edges. The
# other 32 are simply "in the area", and the per-pair `at` churn disappears
# along with any need for an anchor per character.


def apply_positional_fidelity(graph, node_for_character: Dict[str, str],
                              attended: Iterable[str],
                              anchor_for: Optional[Dict[str, str]] = None,
                              keep_existing_anchors: bool = True) -> Dict[str, Any]:
    """Give exactly the attended characters one `at` edge, and nobody else one.

    `node_for_character` maps a character name to its graph node id, because the
    attended set is names and the edges are ids. `anchor_for` optionally says
    which node each attended character should be at; without it an attended
    character keeps whatever anchor it already had, and a character with none is
    simply "in the area" — attending someone does not invent a place for them.

    Returns counts, because the point of the whole thing is the numbers:
    `{"attended", "at_edges", "cleared"}`.
    """
    attended = set(attended or ())
    anchor_for = anchor_for or {}
    kept: List[str] = []
    cleared = 0

    for name in sorted(attended):
        node_id = node_for_character.get(name)
        if not node_id:
            continue
        target = anchor_for.get(name)
        if not target and keep_existing_anchors:
            current = get_character_position(graph, node_id)
            target = current["target_id"] if current and current["relation"] == EDGE_AT else None
        if target:
            set_character_position(graph, node_id, target, EDGE_AT)
            kept.append(name)
        # Enforced even for a character we did not move, because the invariant
        # is a property of the world, not of the write we just performed.
        enforce_single_at(graph, node_id, keep_target=target if target else None)

    for name, node_id in sorted(node_for_character.items()):
        if name in attended:
            continue
        cleared += clear_at(graph, node_id)

    return {"attended": len(attended), "at_edges": len(kept), "cleared": cleared}


def set_character_at_way(graph, player_node_id: str, way_id: str) -> None:
    set_character_position(graph, player_node_id, way_id, EDGE_AT)


def get_character_position(graph, player_node_id: str) -> Optional[Dict[str, str]]:
    """Return {relation, target_id} for the player's spatial anchor, if any."""
    for edge_type in _CHARACTER_POSITION_TYPES:
        for edge in graph.get_edges_for_source(player_node_id, edge_type):
            target = graph.get_node(edge.target)
            if not target:
                continue
            if target.type in ("way", "item", "character", "player"):
                return {"relation": edge.type, "target_id": edge.target}
    return None


def get_character_at_way(graph, player_node_id: str) -> Optional[str]:
    pos = get_character_position(graph, player_node_id)
    if not pos or pos["relation"] != EDGE_AT:
        return None
    way = graph.get_node(pos["target_id"])
    if way and way.type == "way":
        return pos["target_id"]
    return None


def approach_way(graph, player_node_id: str, way_id: str) -> None:
    """Walk up to a way — physical open/close/go/use implies stepping to it."""
    set_character_at_way(graph, player_node_id, way_id)


def default_relation_for_item(item_node) -> str:
    tags = set(_normalize_tags(item_node))
    if tags & {"in_roof", "on_ceiling", "ceiling"}:
        return EDGE_UNDER
    if tags & {"in_floor", "on_ground", "floor"}:
        return EDGE_ON
    return EDGE_AT


def default_relation_for_character() -> str:
    return EDGE_BESIDE


def parse_spatial_target(text: str, default_relation: str = EDGE_AT) -> Tuple[str, str]:
    """Infer relation from phrasing; return (relation, original text)."""
    lower = (text or "").lower().strip()
    relation = default_relation
    for phrase, rel in _RELATION_PHRASES:
        if re.search(rf"(?:^|\s){re.escape(phrase)}(?:\s|$)", lower):
            relation = rel
            break
    return relation, (text or "").strip()


def _item_in_area(graph, item_id: str, area_id: str) -> bool:
    if not item_id or not area_id:
        return False
    for edge_type in (EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT):
        for edge in graph.get_edges_for_target(area_id, edge_type):
            if edge.source.lower() == item_id.lower():
                return True
    for edge in graph.get_edges_for_source(item_id, EDGE_IN):
        if edge.target.lower() == area_id.lower():
            return True
    return False


def _way_connects_area(graph, way_id: str, area_id: str) -> bool:
    area_lower = area_id.lower()
    for edge in graph.get_edges_for_source(area_id, EDGE_CONNECTION):
        if edge.target.lower() == way_id.lower():
            return True
    for edge in graph.get_edges_for_source(way_id, EDGE_CONNECTION):
        if edge.target.lower() == area_lower:
            return True
    return False


def _relation_phrase(relation: str, label: str) -> str:
    article = "the "
    if relation == EDGE_ON:
        return f" on {article}{label}"
    if relation == EDGE_UNDER:
        return f" under {article}{label}"
    if relation == EDGE_BEHIND:
        return f" behind {article}{label}"
    if relation == EDGE_BESIDE:
        return f" beside {article}{label}"
    return f" at {article}{label}"


def _display_target_name(target, viewer_player=None, player_manager=None) -> str:
    if not target:
        return "something"
    if target.type in ("character", "player") and player_manager and viewer_player:
        pname = target.name or target.id.replace("player_", "").replace("_", " ")
        subject = _pm_get_player(player_manager, pname)
        if subject and pname != viewer_player:
            return subject.unknown_display_name()
        return pname
    name = (target.properties or {}).get("name") or target.name or target.id
    return str(name).replace("_", " ")


def spatial_position_phrase(
    graph,
    player_node_id: str,
    area_id: str,
    area_name: str = "",
    viewer_player: str = "",
    player_manager=None,
) -> str:
    """Return e.g. ' under the chandelier' / ' beside the man' / ' at the north'."""
    pos = get_character_position(graph, player_node_id)
    if not pos:
        return ""

    target = graph.get_node(pos["target_id"])
    if not target:
        return ""

    relation = pos["relation"]

    if target.type == "way":
        if not _way_connects_area(graph, target.id, area_id):
            return ""
        from engine.matching import NameMatching

        for edge in graph.get_edges_for_source(area_id, EDGE_CONNECTION):
            if edge.target.lower() != target.id.lower():
                continue
            handle = NameMatching.way_handle(
                target, edge.properties.get("direction", ""), area_name or "",
            )
            return _relation_phrase(EDGE_AT, handle)

    if target.type == "item":
        if not _item_in_area(graph, target.id, area_id):
            return ""
        label = _display_target_name(target)
        return _relation_phrase(relation, label)

    if target.type in ("character", "player") and player_manager:
        pname = target.name or target.id.replace("player_", "").replace("_", " ")
        subject = _pm_get_player(player_manager, pname)
        if not subject or subject.current_area != _pm_current_area_name(player_manager):
            return ""
        label = _display_target_name(target, viewer_player, player_manager)
        return _relation_phrase(relation, label)

    return ""


def at_opening_phrase(graph, player_node_id: str, area_id: str, area_name: str = "") -> str:
    """Backward-compatible alias — any spatial phrase in this area."""
    return spatial_position_phrase(graph, player_node_id, area_id, area_name)


def get_spatial_position_data(graph, player_node_id: str, player_manager=None, viewer_player: str = "") -> Optional[Dict[str, Any]]:
    pos = get_character_position(graph, player_node_id)
    if not pos:
        return None
    target = graph.get_node(pos["target_id"])
    if not target:
        return None
    target_type = "way" if target.type == "way" else (
        "character" if target.type in ("character", "player") else target.type
    )
    return {
        "relation": pos["relation"],
        "target_id": pos["target_id"],
        "target_type": target_type,
        "target_name": _display_target_name(target, viewer_player, player_manager),
    }


def approach_item(
    graph,
    player_manager,
    target_name: str,
    item_node,
    relation: str = None,
) -> None:
    """Walk up to a room item — used by examine, use-on, put/place."""
    if not _pm_active_player(player_manager) or not item_node:
        return
    current_area_name = _pm_current_area_name(player_manager)
    area_id = None
    if current_area_name:
        area_id = "area_" + current_area_name.lower().replace(" ", "_")
    if not area_id or not _item_in_area(graph, item_node.id, area_id):
        return
    pid = _pm_get_player_node_id(player_manager, _pm_active_player(player_manager))
    if not pid:
        return
    if not relation:
        relation, _ = parse_spatial_target(target_name, default_relation_for_item(item_node))
    set_character_position(graph, pid, item_node.id, relation)


def approach_character(graph, player_manager, target_pname: str, actor_name: str = None) -> None:
    """Walk up to another character — grab, give, steal, use-on, examine."""
    actor = actor_name or _pm_active_player(player_manager)
    if not actor or not target_pname or actor == target_pname:
        return
    target = _pm_get_player(player_manager, target_pname)
    if not target or target.current_area != _pm_current_area_name(player_manager):
        return
    pid = _pm_get_player_node_id(player_manager, actor)
    target_pid = _pm_get_player_node_id(player_manager, target_pname)
    if not pid or not target_pid:
        return
    set_character_position(graph, pid, target_pid, default_relation_for_character())


def set_position_examining_character(graph, player_manager, target_pname: str) -> None:
    approach_character(graph, player_manager, target_pname)


def set_position_examining_item(graph, player_manager, target_name: str, item_node) -> None:
    approach_item(graph, player_manager, target_name, item_node)


def _collect_area_ways(graph, area_id: str, area_name: str = "") -> List[Dict[str, Any]]:
    from engine.matching import NameMatching

    rows = []
    seen = set()
    for edge in graph.get_edges_for_source(area_id, EDGE_CONNECTION):
        way_id = edge.target
        if way_id in seen:
            continue
        way = graph.get_node(way_id)
        if not way or way.type != "way":
            continue
        seen.add(way_id)
        target_name = ""
        for conn in graph.get_edges_for_source(way_id, EDGE_CONNECTION):
            if conn.target.lower() != area_id.lower():
                target = graph.get_node(conn.target)
                if target:
                    target_name = target.name
                    break
        rows.append({
            "edge": edge,
            "way": way,
            "way_id": way_id,
            "handle": NameMatching.way_handle(
                way, edge.properties.get("direction", ""), area_name or "",
            ),
            "target_name": target_name,
        })
    return rows


def get_transit_roles(
    graph,
    area_id: str,
    player_node_id: str,
    area_name: str = "",
) -> Optional[Dict[str, Any]]:
    """When in a transit area and AT a way, return back/forward exit info."""
    area_node = graph.get_node(area_id)
    if not is_transit_area(area_node):
        return None
    at_way_id = get_character_at_way(graph, player_node_id)
    if not at_way_id:
        return None
    ways = _collect_area_ways(graph, area_id, area_name)
    if len(ways) < 2:
        return None
    back = next((row for row in ways if row["way_id"].lower() == at_way_id.lower()), None)
    if not back:
        return None
    forward_candidates = [row for row in ways if row["way_id"].lower() != at_way_id.lower()]
    if len(forward_candidates) != 1:
        return None
    forward = forward_candidates[0]
    return {
        "back_edge": back["edge"],
        "back_way": back["way"],
        "back_handle": "back",
        "back_real_handle": back["handle"],
        "forward_edge": forward["edge"],
        "forward_way": forward["way"],
        "forward_handle": "forward",
        "forward_real_handle": forward["handle"],
        "forward_target": forward["target_name"],
    }


def resolve_transit_movement(
    graph,
    game_state,
    area_id: str,
    direction: str,
) -> Optional[Tuple[Any, Any, str]]:
    """Resolve go back / go forward in transit areas. Returns (edge, way, handle)."""
    direction_lower = (direction or "").lower().strip()
    if direction_lower not in ("back", "forward"):
        return None
    player_name = getattr(game_state, "active_player", None)
    if not player_name:
        return None
    player_node_id = game_state._player_node_id(player_name)
    area_name = ""
    if getattr(game_state, "current_area", None):
        area_name = game_state.current_area.name or ""
    roles = get_transit_roles(graph, area_id, player_node_id, area_name)
    if not roles:
        return None
    if direction_lower == "back":
        return roles["back_edge"], roles["back_way"], roles["back_real_handle"]
    return roles["forward_edge"], roles["forward_way"], roles["forward_real_handle"]
