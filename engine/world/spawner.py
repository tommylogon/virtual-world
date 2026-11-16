"""WorldPainter distribution spawners (tasks 569/570).

`data/worldpainter/biomes.json` declares, per biome, what a painted area is
likely to **hold**:

- ``resource_distribution`` - weighted tag sets; this module resolves them to
  real library items and stages them into a compiled area. A tag that resolves
  to nothing is reported in :attr:`GenerationReport.unresolved_tags`, never
  silently substituted.
- ``hostile_distribution`` - base / per-area-from-settlement / capped chances
  per hostile kind, evaluated at runtime when somebody is in an area.

Both are data-driven: a modder edits the JSON, not this file.

@module spawner
@contributes _weighted_pick, _resolve_tags, spawn_resources, hostile_chance, roll_hostiles, hostile_character_node
@docs docs/virtualWorld/Items & Inventory/Items Overview.md
"""

from __future__ import annotations

import json
import os
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
    satisfy. A request that resolves to nothing places no item - it is surfaced,
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
            extra["source"] = "worldpainter"
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
    kilometres - a settlement's own area is 0.
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
    ``Player`` in the manager) is the population layer's job - this is the same
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



def _load_character_templates(char_dir: str) -> Dict[str, List[dict]]:
    """Index character cards in char_dir by their tags."""
    by_kind: Dict[str, List[dict]] = {}
    if not os.path.isdir(char_dir):
        return by_kind
    for fname in os.listdir(char_dir):
        if not fname.endswith(".json"):
            continue
        p = os.path.join(char_dir, fname)
        try:
            with open(p, "r", encoding="utf-8-sig") as f:
                card = json.load(f)
            tags = [str(t).lower() for t in card.get("tags") or []]
            for tag in tags:
                by_kind.setdefault(tag, []).append(card)
        except Exception:
            continue
    return by_kind


def spawn_hostiles_for_area(world: Any, area_name: str, *,
                            distance_from_settlement: Optional[float] = None,
                            seed: Optional[str] = None,
                            tick: int = 0,
                            data_dir: Optional[str] = None,
                            entries: Optional[List[dict]] = None,
                            rng: Optional[random.Random] = None,
                            templates: Optional[Dict[str, List[dict]]] = None) -> List[Any]:
    """Runtime consumer: evaluate hostile chances and register spawned simple_npc Players (task-570).

    Computes distance from settlement (if not supplied), rolls deterministic hostile kinds,
    resolves character definitions from the character library, registers them as live
    simple_npc Player objects via world.add_player, and records an encounter event.
    """
    area_id = None
    if hasattr(world, "_area_node_id"):
        try:
            area_id = world._area_node_id(area_name)
        except Exception:
            pass
    elif hasattr(world, "area_node_id"):
        try:
            area_id = world.area_node_id(area_name)
        except Exception:
            pass

    area_node = None
    if area_id and getattr(world, "graph", None) is not None:
        area_node = world.graph.get_node(area_id)

    biome_id = None
    if area_node is not None:
        props = getattr(area_node, "properties", {}) or {}
        biome_id = props.get("biome")
        if distance_from_settlement is None:
            distance_from_settlement = props.get("distance_from_settlement", props.get("settlement_distance", 0.0))
    else:
        area_obj = getattr(world, "movement", None)
        if area_obj and hasattr(area_obj, "get_area"):
            a = area_obj.get_area(area_name)
            if a:
                biome_id = getattr(a, "biome", None)

    if not biome_id:
        return []

    dist_val = max(0.0, float(distance_from_settlement or 0.0))
    active_rng = rng or random.Random(f"{seed or getattr(world, 'seed', 'hostiles')}|{area_name}|{tick}")
    rolled = roll_hostiles(str(biome_id), dist_val, active_rng, entries=entries)
    if not rolled:
        return []

    if templates is None:
        if data_dir:
            c_dir = os.path.join(data_dir, "library", "characters")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            c_dir = os.path.join(base_dir, "data", "library", "characters")
        templates = _load_character_templates(c_dir)

    from player import Player
    spawned = []

    for kind in rolled:
        candidates = templates.get(kind.lower()) or []
        if not candidates:
            # Fallback bare minimal card if library lacks this kind
            cdata = {
                "name": kind.title(),
                "personality": f"A hostile {kind}.",
                "description": f"A dangerous wild {kind}.",
                "base_description": f"Wild {kind}.",
                "tags": [kind, "hostile"],
                "traits": {"hostile": True},
                "stats": {"STR": 10, "DEX": 10, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8},
                "vitals": {"HP": 50, "Max_HP": 50, "Energy": 80, "Hunger": 20, "Thirst": 20},
                "simple_npc": True,
            }
        else:
            cdata = active_rng.choice(candidates)

        base_name = cdata.get("name", kind.title())
        existing = getattr(world, "players", {}) or {}
        count = sum(1 for p in existing.values() if p.name.startswith(base_name))
        pname = f"{base_name} {count + 1}" if count > 0 else base_name

        player = Player(pname)
        player.simple_npc = True
        player.npc_behavior = cdata.get("npc_behavior", "wander")
        player.personality = cdata.get("personality", "")
        player.description = cdata.get("description", "")
        player.base_description = cdata.get("base_description", "")
        player.species = cdata.get("species")
        player.size = cdata.get("size")
        player.stats = dict(cdata.get("stats", player.stats))
        player.vitals = {**player.vitals, **dict(cdata.get("vitals", player.vitals))}
        player.decay_rates = dict(cdata.get("decay_rates", player.decay_rates))
        player.skills = dict(cdata.get("skills", player.skills))
        player.traits = dict(cdata.get("traits", player.traits))
        player.tags = list(cdata.get("tags", player.tags))
        player.interest_tags = list(cdata.get("interest_tags", player.interest_tags))
        player.fear_tags = list(cdata.get("fear_tags", player.fear_tags))
        player.dislike_tags = list(cdata.get("dislike_tags", player.dislike_tags))
        player.current_area = area_name

        if hasattr(world, "add_player"):
            world.add_player(player)
        if hasattr(world, "set_player_area"):
            world.set_player_area(pname, area_name)

        if hasattr(world, "add_log_entry"):
            world.add_log_entry(f"[Encounter] A {pname} emerges in {area_name}!")
        if hasattr(world, "record_turn_event"):
            world.record_turn_event(pname, "encounter", f"A {pname} emerges in {area_name}.", area_name=area_name, tick=tick)

        spawned.append(player)

    return spawned
