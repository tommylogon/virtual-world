"""WorldPainter distribution spawners (tasks 569/570).

`data/worldpainter/biomes.json` declares, per biome, what a painted area is
likely to **hold**:

- ``resource_distribution`` — weighted tag sets; this module resolves them to
  real library items and stages them into a compiled area. A tag that resolves
  to nothing is reported in :attr:`GenerationReport.unresolved_tags`, never
  silently substituted.
- ``hostile_distribution`` — base / per-area-from-settlement / capped chances
  per hostile kind, evaluated at runtime when somebody is in an area.

Both are data-driven: a modder edits the JSON, not this file.
"""

from __future__ import annotations

import random
from typing import Callable, Dict, List, Optional, Tuple

from engine import biomes
from engine.generation import provenance
from engine.library_nodes import build_item_subtree, spatial_edge
from engine.population import FURNITURE_TAG, LibraryIndex
from graph import Edge, Node

#: Provenance recipe ids, so a spawned node is recognisable and regenerable.
RESOURCE_RECIPE_ID = "resource_distribution.v1"
HOSTILE_RECIPE_ID = "hostile_distribution.v1"


# ── resources (task-569) ────────────────────────────────────────────────

def _weighted_pick(entries: List[dict], rng: random.Random) -> Optional[dict]:
    """Pick one entry by ``weight``. Deterministic for a fixed rng."""
    weights = [max(0.0, float(e.get("weight", 1) or 0)) for e in entries]
    total = sum(weights)
    if total <= 0:
        return None
    roll = rng.random() * total
    upto = 0.0
    for entry, weight in zip(entries, weights):
        upto += weight
        if roll <= upto:
            return entry
    return entries[-1]


def _resolve_tags(index: LibraryIndex, tags: List[str]) -> Tuple[List[str], List[str]]:
    """Items carrying **all** *tags*, and the tags that resolve to nothing.

    Never falls back to a partial match: "berry" alone is not "berry, fruit".
    """
    wanted = [str(t).lower() for t in (tags or []) if str(t).strip()]
    if not wanted:
        return [], []
    missing = [t for t in wanted if t not in index.by_tag]
    if missing:
        return [], missing
    candidates = index.candidates(wanted, require_all=wanted,
                                  exclude_tags=[FURNITURE_TAG])
    if not candidates:
        return [], list(wanted)
    return candidates, []


def spawn_resources(area_nodes: List[Node], index: LibraryIndex, *,
                    scope_id: str, seed: str, tick: int = 0,
                    per_area: int = 1,
                    rng: Optional[random.Random] = None,
                    distribution: Optional[Dict[str, list]] = None,
                    ) -> Tuple[List[Node], List[Edge], Dict[str, int]]:
    """Stage resource items into compiled *area_nodes* (task-569).

    For each area whose ``properties.biome`` declares a resource distribution,
    pick ``per_area`` weighted entries and place the resolved library item in
    the area by a normal ``in`` edge, stamped with generation provenance so it
    unloads with its scope (task-584) and is regenerable.

    Returns ``(nodes, edges, unresolved_tags)`` where ``unresolved_tags`` counts
    every requested tag (or missing container content) the library could not
    satisfy. A request that resolves to nothing places no item — it is surfaced,
    not substituted.
    """
    rng = rng or random.Random(f"{scope_id}|{seed}|resources")
    distribution = distribution if distribution is not None else biomes.resource_distribution()
    nodes: List[Node] = []
    edges: List[Edge] = []
    unresolved: Dict[str, int] = {}

    for area in area_nodes:
        biome_id = (getattr(area, "properties", None) or {}).get("biome")
        if not biome_id:
            continue
        entries = distribution.get(str(biome_id)) or []
        if not entries:
            continue
        for slot in range(max(0, int(per_area))):
            entry = _weighted_pick(entries, rng)
            if entry is None:
                continue
            candidates, missing = _resolve_tags(index, entry.get("tags") or [])
            for tag in missing:
                unresolved[tag] = unresolved.get(tag, 0) + 1
            if not candidates:
                continue
            library_id = candidates[rng.randrange(len(candidates))]
            node_id = f"item_{scope_id}_{area.id}_res{slot}"
            extra = provenance(scope_id, RESOURCE_RECIPE_ID, seed, tick)
            item_nodes, item_edges, missing_contents = build_item_subtree(
                library_id, index.entries[library_id], node_id,
                index.entries.get, extra=extra)
            nodes.extend(item_nodes)
            edges.extend(item_edges)
            edges.append(spatial_edge(node_id, area.id, "in"))
            for content_id in missing_contents:
                unresolved[content_id] = unresolved.get(content_id, 0) + 1
    return nodes, edges, unresolved


# ── hostiles (task-570) ─────────────────────────────────────────────────

def hostile_chance(biome_id: str, distance_from_settlement: float,
                   entries: Optional[List[dict]] = None) -> Dict[str, float]:
    """Per-kind spawn chance for a biome at a distance from settlement.

    ``base_chance + per_area_from_settlement * distance``, capped at
    ``max_chance`` and never above 1. Distance is counted in **areas**, not
    kilometres — a settlement's own area is 0.
    """
    entries = entries if entries is not None else (biomes.hostile_distribution().get(str(biome_id)) or [])
    out: Dict[str, float] = {}
    distance = max(0.0, float(distance_from_settlement or 0))
    for entry in entries:
        kind = str(entry.get("kind") or "")
        if not kind:
            continue
        base = float(entry.get("base_chance", 0) or 0)
        per = float(entry.get("per_area_from_settlement", 0) or 0)
        cap = float(entry.get("max_chance", 1) or 1)
        out[kind] = max(0.0, min(1.0, min(cap, base + per * distance)))
    return out


def roll_hostiles(biome_id: str, distance_from_settlement: float,
                  rng: random.Random,
                  entries: Optional[List[dict]] = None) -> List[str]:
    """The hostile kinds that appear this roll, in a stable order."""
    chances = hostile_chance(biome_id, distance_from_settlement, entries=entries)
    return [kind for kind, chance in sorted(chances.items()) if rng.random() < chance]


def hostile_character_node(kind: str, node_id: str, *, scope_id: str,
                           seed: str, tick: int = 0) -> Node:
    """A bare hostile character node, tagged and generation-stamped.

    The node is the graph anchor; turning it into a live simple NPC (a
    ``Player`` in the manager) is the population layer's job — this is the same
    graph-vs-runtime split every other generated thing follows.
    """
    return Node(
        id=node_id, type="character", name=str(kind).title(),
        properties={
            "simple_npc": True,
            "tags": [str(kind), "hostile"],
            "npc_behavior": "wander",
            "generated": provenance(scope_id, HOSTILE_RECIPE_ID, seed, tick)["generated"],
        },
    )
