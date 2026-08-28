"""One reachability rule for item verbs.

Anything a character can legitimately act on counts as reachable:

* carried or equipped,
* inside a carried/equipped container that isn't closed,
* anywhere in the current area — directly, placed on/under/beside a
  surface (``get_edges_for_target(area, EDGE_IN)`` expands spatial edges),
* inside an OPEN container in the area, at any nesting depth,

and NOT hidden (``current_state == "hidden"`` stays invisible until found)
and not inside a closed/locked container.

Used by use / use_on / eat / drink / place / put / toggleable flips so all
verbs agree on what "the thing right there" means.
"""

from typing import Optional

from graph import EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN

# States that seal a container's contents away (node itself stays visible).
_CLOSED_STATES = {"closed", "locked", "sealed"}


def _norm(s) -> str:
    return (s or "").lower().replace("_", " ").replace("-", " ").strip()


import re

_ARTICLES = ("the ", "a ", "an ")

def _core(s) -> str:
    """Normalized match key: lowercase, underscores/dashes -> spaces, with a
    leading article and a trailing parenthetical qualifier stripped.

    Lets "the steamed meal" resolve to "Steamed Meal (Holding Chute)", and
    "use the warm crunchy taco" to "Warm Crunchy Taco" — so partial / articled /
    parenthetically-named items match (task: item name resolution).
    """
    s = _norm(s)
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    for a in _ARTICLES:
        if s.lower().startswith(a):
            s = s[len(a):].strip()
            break
    return s




def _props(node) -> dict:
    return node.properties if node and node.properties else {}


def _is_hidden(node) -> bool:
    """Hidden per engine convention: current_state == 'hidden'.

    The boolean ``hidden:`` property is deliberately ignored — visibility
    filters across the engine only honor the state machine."""
    return _norm(_props(node).get("current_state")) == "hidden"


def _is_open(node) -> bool:
    p = _props(node)
    if p.get("locked"):
        return False
    return _norm(p.get("current_state")) not in _CLOSED_STATES


def _match_tier(node, wanted: str, fuzzy_wanted: Optional[str]) -> Optional[int]:
    """0 exact · 1 fuzzy-exact · 2 containment · 3 core · None no match."""
    name = _norm(node.name)
    if not name:
        return None
    if name == wanted:
        return 0
    if fuzzy_wanted and name == fuzzy_wanted:
        return 1
    if len(wanted) >= 3 and wanted in name:
        return 2
    if len(name) > 3 and name in wanted:
        return 2
    # Core match: strip article + parenthetical qualifier from both sides.
    ncore = _core(node.name)
    wcore = _core(wanted)
    fcore = _core(fuzzy_wanted) if fuzzy_wanted else ""
    if ncore and ncore == wcore:
        return 3
    if fcore and ncore == fcore:
        return 3
    if ncore and wcore and (len(wcore) >= 3 and wcore in ncore):
        return 3
    if ncore and wcore and (len(ncore) > 3 and ncore in wcore):
        return 3
    return None


def find_reachable(graph, matcher, player_manager, item_name: str) -> Optional[object]:
    """Resolve *item_name* to the best reachable node, or None.

    Duck-typed throughout: works with the VirtualWorld facade, the real
    PlayerManager, and test mocks. Matching prefers exact names over
    fuzzy over containment, inventory over room (carried wins first via
    ``find_item_node``).
    """
    if not item_name or graph is None:
        return None

    # 0) carried first — preserves existing semantics everywhere.
    getter = getattr(player_manager, "find_item_node", None)
    if callable(getter):
        try:
            carried = getter(item_name)
            if carried:
                return carried
        except Exception:
            pass

    wanted = _norm(item_name)
    fuzzy_wanted = None
    if matcher is not None and hasattr(matcher, "_match_item_name"):
        try:
            fuzzy = matcher._match_item_name(item_name)
            fw = _norm(fuzzy)
            if fw and fw != wanted:
                fuzzy_wanted = fw
        except Exception:
            fuzzy_wanted = None

    for limit in (0, 1, 2):
        for node in _visible_ordered(graph, player_manager):
            tier = _match_tier(node, wanted, fuzzy_wanted)
            if tier is not None and tier <= limit:
                return node
    return None


def _visible_ordered(graph, player_manager) -> list:
    """Every visible reachable item node, in priority order: carried/equipped
    roots (with open-container contents) then the area subtree. Hidden
    branches are pruned entirely; closed containers seal their contents."""
    ordered = []
    seen = set()

    def walk(parent_id: str):
        for edge in graph.get_edges_for_target(parent_id, EDGE_IN):
            node = graph.get_node(edge.source)
            if not node or node.id in seen:
                continue
            seen.add(node.id)
            if _is_hidden(node):
                continue
            ordered.append(node)
            if _is_open(node):
                walk(node.id)

    # Resolve ids defensively (mocks/facades vary).
    player_id = area_id = None
    try:
        from engine.character_spatial import _pm_get_player_node_id
        pid = _pm_get_player_node_id(player_manager,
                                     getattr(player_manager, "active_player", None))
        if isinstance(pid, str):
            player_id = pid
    except Exception:
        pass
    try:
        aid = player_manager._get_current_area_id()
        if isinstance(aid, str):
            area_id = aid
    except Exception:
        pass

    if player_id:
        for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
            for edge in graph.get_edges_for_target(player_id, edge_type):
                root = graph.get_node(edge.source)
                if root and root.id not in seen:
                    seen.add(root.id)
                    ordered.append(root)  # holding it beats any state
                    if _is_open(root):
                        walk(root.id)
    if area_id:
        walk(area_id)

    return ordered


def reachable_items(graph, player_manager) -> list:
    """All visible reachable item nodes — same rule as ``find_reachable``
    without a name filter (carried first, then the area subtree). Used by
    bare eat/drink to auto-pick something consumable."""
    if graph is None:
        return []
    return [n for n in _visible_ordered(graph, player_manager)
            if getattr(n, "type", "") == "item"]
