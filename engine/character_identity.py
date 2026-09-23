"""One character, one graph node (task-463).

Authored scenarios used to carry two character nodes per person: a
``character_<slug>`` node with the prose description and the ``in``/``carrying``
edges, and a runtime ``player_<Name>`` anchor with the ``x``/``y`` props and the
``at``/``equipped``/``grappled`` edges. This module collapses them into the
canonical anchor and keeps the retired id resolvable.

Pure data: no graph objects, no Flask, so both the load path and the offline
migration tool can call it.
"""

from typing import Any, Dict, List, Optional, Tuple

#: Authored prose wins over runtime node props during a merge.
PROSE_KEYS = ("description", "base_description", "personality")


def character_slug(name: Any) -> str:
    """The slug the offline generator uses for an authored character id."""
    return str(name or "").lower().replace(" ", "_").replace("-", "_")


def authored_character_node_id(name: Any) -> str:
    """Legacy authored node id for a character: ``character_<slug>``."""
    return f"character_{character_slug(name)}"


def canonical_character_node_id(name: Any) -> str:
    """The runtime anchor id for a unique display name (``player_<Name>``)."""
    return f"player_{name}".replace(" ", "_")


def anchor_node_id(key: str, player_data: Dict[str, Any]) -> str:
    """The canonical node id for a player (mirrors ``PlayerManager.reindex``).

    A unique name keeps the legacy ``player_<Name>`` anchor; a duplicated
    display name (its registry key differs) gets the stable ``__<uid6>`` suffix.
    """
    name = str((player_data or {}).get("name") or key)
    base = canonical_character_node_id(name)
    if str(key) != name:
        uid = str((player_data or {}).get("id") or "dup")[:6]
        return f"{base}__{uid}"
    return base


def _same(a: Any, b: Any) -> bool:
    return str(a).lower() == str(b).lower()


def _find_key(nodes: Dict[str, Any], node_id: Any) -> Optional[str]:
    if node_id is None:
        return None
    if node_id in nodes:
        return node_id
    lowered = str(node_id).lower()
    for key in nodes:
        if str(key).lower() == lowered:
            return key
    return None


def _find_character_node_by_name(
    nodes: Dict[str, Any],
    name: str,
    canonical_ids: set,
    claimed: set,
) -> Optional[str]:
    """The single authored character node carrying *name*, or None if ambiguous.

    Filename-derived ids can drift from the display-name slug
    (``character_eldenford_guard`` for "Eldenford Road Guard Captain"), so a
    by-name match is the fallback when the derived id misses.
    """
    hits = []
    for key, node in nodes.items():
        if not isinstance(node, dict) or node.get("type") != "character":
            continue
        if key in canonical_ids or key in claimed:
            continue
        if str(node.get("name") or "") == str(name):
            hits.append(key)
    return hits[0] if len(hits) == 1 else None


def _dedupe_edges(edges: List[Dict[str, Any]]) -> int:
    """Drop edges that repeat another's (source, target, type). Returns count."""
    seen = set()
    kept = []
    dropped = 0
    for edge in edges:
        if not isinstance(edge, dict):
            kept.append(edge)
            continue
        key = (
            str(edge.get("source", "")).lower(),
            str(edge.get("target", "")).lower(),
            edge.get("type"),
        )
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        kept.append(edge)
    if dropped:
        edges[:] = kept
    return dropped


def collapse_character_identity(
    graph_data: Dict[str, Any],
    players: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge each player's authored ``character_*`` node into their anchor.

    Returns a report: ``collapsed`` (retired id, canonical id) pairs,
    ``aliases`` (retired id → canonical id, lowercase keys) for the graph's id
    index, and the edge rewrite/dedupe counts. Mutates *graph_data* in place.
    """
    report: Dict[str, Any] = {
        "collapsed": [],
        "aliases": {},
        "edges_rewritten": 0,
        "edges_deduped": 0,
    }
    if not isinstance(graph_data, dict) or not isinstance(players, dict) or not players:
        return report
    raw_nodes = graph_data.get("nodes")
    raw_edges = graph_data.get("edges")
    if not isinstance(raw_nodes, dict) or not isinstance(raw_edges, list):
        return report
    # Work on shallow copies so a live ``to_dict()`` payload is never mutated
    # through its shared property/edge references.
    nodes: Dict[str, Any] = dict(raw_nodes)
    edges: List[Any] = [
        dict(edge) if isinstance(edge, dict) else edge for edge in raw_edges
    ]

    anchors = {key: anchor_node_id(key, pdata) for key, pdata in players.items()}
    canonical_ids = set(anchors.values())
    by_name: Dict[str, List[str]] = {}
    for key, pdata in players.items():
        by_name.setdefault(str((pdata or {}).get("name") or key), []).append(key)

    claimed = set()
    for key, pdata in players.items():
        name = str((pdata or {}).get("name") or key)
        canonical = anchors[key]
        # An authored node cannot be assigned unambiguously when two players
        # share the display name — leave it alone rather than guess.
        if len(by_name.get(name, [])) != 1:
            continue
        # A suffixed anchor needs the stable uid; without it the runtime derives
        # a fresh one, so the collapse could not predict where to merge.
        if str(key) != name and not (pdata or {}).get("id"):
            continue

        candidate = _find_key(nodes, authored_character_node_id(name))
        if candidate is None:
            candidate = _find_character_node_by_name(nodes, name, canonical_ids, claimed)
        if candidate is None or candidate in claimed or _same(candidate, canonical):
            continue
        node = nodes.get(candidate)
        if not isinstance(node, dict) or node.get("type") != "character":
            continue
        if candidate in canonical_ids:
            continue

        claimed.add(candidate)
        _merge_node(nodes, candidate, canonical, name)
        report["edges_rewritten"] += _rewrite_edges(edges, candidate, canonical)
        nodes.pop(candidate, None)

        report["aliases"][str(candidate).lower()] = canonical
        derived = authored_character_node_id(name)
        if not _same(derived, candidate):
            report["aliases"][derived.lower()] = canonical
        report["collapsed"].append((candidate, canonical))

    report["edges_deduped"] = _dedupe_edges(edges)
    graph_data["nodes"] = nodes
    graph_data["edges"] = edges
    return report


def _merge_node(nodes: Dict[str, Any], candidate: str, canonical: str, name: str):
    """Fold *candidate* into *canonical* (creating it when absent)."""
    cand = nodes.get(candidate) or {}
    cand_props = cand.get("properties") if isinstance(cand.get("properties"), dict) else {}
    canonical_key = _find_key(nodes, canonical)
    if canonical_key is not None:
        target = nodes[canonical_key]
        target_props = target.get("properties") if isinstance(target.get("properties"), dict) else {}
        merged = dict(cand_props)
        merged.update(target_props)
        for prose in PROSE_KEYS:
            value = cand_props.get(prose)
            if value:
                merged[prose] = value
        new_target = dict(target)
        new_target["properties"] = merged
        nodes[canonical_key] = new_target
        return
    new_node = dict(cand)
    new_node["id"] = canonical
    new_node["type"] = "character"
    new_node.setdefault("name", name)
    new_node["properties"] = dict(cand_props)
    nodes[canonical] = new_node


def _rewrite_edges(edges: List[Dict[str, Any]], retired: str, surviving: str) -> int:
    """Point every edge endpoint mentioning *retired* at *surviving*."""
    rewritten = 0
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if _same(edge.get("source"), retired):
            edge["source"] = surviving
            rewritten += 1
        if _same(edge.get("target"), retired):
            edge["target"] = surviving
            rewritten += 1
    return rewritten


def rewrite_known(known: Any, aliases: Dict[str, str]) -> Tuple[List[str], int]:
    """Map retired character ids in a ``known`` list to their surviving ids."""
    if not isinstance(known, (list, tuple)):
        return [], 0
    out = []
    changed = 0
    for entry in known:
        replacement = aliases.get(str(entry).lower())
        if replacement is not None and not _same(replacement, entry):
            out.append(replacement)
            changed += 1
        else:
            out.append(entry)
    return out, changed


def normalize_known_lists(players: Dict[str, Any], aliases: Dict[str, str]) -> int:
    """Rewrite authored ``known`` lists on raw player dicts. Returns changes."""
    if not isinstance(players, dict) or not aliases:
        return 0
    changed = 0
    for pdata in players.values():
        if not isinstance(pdata, dict) or "known" not in pdata:
            continue
        known, moved = rewrite_known(pdata.get("known"), aliases)
        if moved:
            pdata["known"] = known
            changed += moved
    return changed
