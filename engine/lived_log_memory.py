"""Phrase meaningful lived_log entries into first-person memories (task-727).

The lived log (``engine/lived_log.py``) is the objective record; memories are
the subjective read the character Mind panel shows. ``engine/promotion.py``
bridges a background *span* into one aggregate memory. This module bridges
*individual* entries whose facts have no other memory writer, so a death, a
relationship shift, or a pursuit reads back as a first-person memory instead of
being lost.

Kinds already covered elsewhere and deliberately NOT re-phrased here:

- ``social``  -> ``engine/social_text.py`` (background_social writes the memory)
- ``threat``  -> ``background_social`` writes a memory at the same site
- ``need``    -> ``engine/agent_memory._surface_need_recall``
- ``act`` / ``move`` / ``traversal`` -> ``record_observation`` area/item memories

Deterministic, no LLM (v1) -- same rule as promotion (task-412). Idempotent per
entry: ``player.lived_log_memorized_through`` marks the newest tick already
phrased, so re-running a turn never duplicates a memory.

@module lived_log_memory
@contributes the per-entry lived_log -> first-person memory bridge
@docs docs/design/lived-log-format.md
"""

from __future__ import annotations

from collections import deque
import logging
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

#: Kinds with no other memory writer. See the module docstring for the kinds
#: that ARE covered elsewhere, so this list must not repeat them.
MEMORIZABLE_KINDS = ("death", "resurrection", "relationship", "pursuit")

#: Two-Lane Factual Invariant (task-950): deterministic ground-truth state stays
#: on LANE_FACTUAL; subjective reconsolidation / palimpsest syntheses live on
#: LANE_PALIMPSEST.
LANE_FACTUAL = "factual"
LANE_PALIMPSEST = "palimpsest"

FACTUAL_KINDS = frozenset({
    "inventory",
    "item",
    "area",
    "spatial",
    "spatial_memory",
    "door",
    "lock",
    "way",
    "way_state",
    "way_aspect",
    "already_known",
    "absence",
})

FACTUAL_TYPES = frozenset({
    "fact",
    "location",
    "way_aspect",
    "inventory",
    "spatial",
    "door",
    "lock",
})

FACTUAL_TAGS = frozenset({
    "factual",
    "inventory",
    "spatial_memory",
    "door",
    "lock",
    "way_aspect",
    "already_known",
    "absence",
})

FACTUAL_WHY_PREFIXES = (
    "inventory:",
    "spatial:",
    "spatial_memory:",
    "door:",
    "lock:",
    "way:",
    "already_known:",
)

_SUBJECTIVE_SOURCES = frozenset({
    "intermediator",
    "lived_log",
    "reflection",
    "dream",
    "background",
})

_SUBJECTIVE_TYPES = frozenset({
    "reflection",
    "belief",
    "reaction",
    "thought",
    "expectation",
    "conversation",
    "dialogue",
    "speech",
    "emotion",
    "trauma",
})

_SUBJECTIVE_CATEGORIES = frozenset({
    "belief",
    "social",
    "procedural",
})


def _sanitize_source_ids(raw_ids: Any) -> List[str]:
    if not isinstance(raw_ids, (list, tuple, set)):
        return []
    out: List[str] = []
    seen = set()
    for item in raw_ids:
        sid = str(item or "").strip()
        if sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def _generation_depth_of(memory: Dict[str, Any]) -> int:
    raw = memory.get("generation_depth")
    if raw is None:
        raw = memory.get("reflection_depth", 0)
    try:
        return max(0, int(raw or 0))
    except (TypeError, ValueError):
        return 0


def is_factual_entry(entry: Any) -> bool:
    """True when a lived_log entry records deterministic inventory, spatial,
    door/lock, or AlreadyKnown facts that must never be palimpsest-varnished."""
    if not isinstance(entry, dict):
        return False
    lane = str(entry.get("lane") or "").strip().lower()
    if lane == LANE_FACTUAL or entry.get("factual") is True:
        return True
    if lane == LANE_PALIMPSEST:
        return False
    kind = str(entry.get("kind") or "").strip().lower()
    if kind in FACTUAL_KINDS:
        return True
    why = str(entry.get("why") or "").strip().lower()
    if why.startswith(FACTUAL_WHY_PREFIXES):
        return True
    tags = {str(t).strip().lower() for t in (entry.get("tags") or []) if t}
    return bool(tags & FACTUAL_TAGS)


def is_factual_memory(memory: Any) -> bool:
    """True when a memory entry belongs to the unvarnished deterministic lane."""
    if not isinstance(memory, dict):
        return False
    lane = str(memory.get("lane") or "").strip().lower()
    if lane == LANE_FACTUAL:
        return True
    if lane in (LANE_PALIMPSEST, "subjective"):
        return False

    source = str(memory.get("source") or "").strip().lower()
    mtype = str(memory.get("type") or "").strip().lower()
    category = str(memory.get("category") or "").strip().lower()
    if (
        source in _SUBJECTIVE_SOURCES
        or mtype in _SUBJECTIVE_TYPES
        or category in _SUBJECTIVE_CATEGORIES
        or _generation_depth_of(memory) > 0
    ):
        return False

    kind = str(memory.get("kind") or "").strip().lower()
    if kind in FACTUAL_KINDS:
        return True
    if mtype in FACTUAL_TYPES:
        return True
    data = memory.get("data")
    if isinstance(data, dict) and (
        data.get("event") == "scene_observed" or data.get("polarity") == "absent"
    ):
        return True
    tags = {str(t).strip().lower() for t in (memory.get("tags") or []) if t}
    return bool(tags & FACTUAL_TAGS)


def classify_memory_lane(memory: Any) -> str:
    """Return LANE_FACTUAL for deterministic grounding or LANE_PALIMPSEST otherwise."""
    return LANE_FACTUAL if is_factual_memory(memory) else LANE_PALIMPSEST


def ensure_memory_lineage(entry: Dict[str, Any], pool: Optional[Iterable[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Normalize source_memory_ids, generation_depth, and lane in place."""
    if not isinstance(entry, dict):
        return entry
    entry["source_memory_ids"] = _sanitize_source_ids(entry.get("source_memory_ids"))
    entry["generation_depth"] = _generation_depth_of(entry)
    lane = str(entry.get("lane") or "").strip().lower()
    if lane not in (LANE_FACTUAL, LANE_PALIMPSEST):
        entry["lane"] = classify_memory_lane(entry)
    else:
        entry["lane"] = lane
    return entry


def resolve_source_lineage(
    memories: Iterable[Dict[str, Any]],
    source_ids: Iterable[Any],
    max_hops: int = 16,
) -> Dict[str, Any]:
    """Trace source_memory_ids back to immutable raw observation references."""
    by_id: Dict[str, Dict[str, Any]] = {}
    for m in (memories or []):
        if isinstance(m, dict) and m.get("id"):
            by_id[str(m["id"])] = m

    direct_ids = _sanitize_source_ids(list(source_ids or []))
    raw_source_ids: List[str] = []
    raw_seen = set()
    raw_sources: List[Dict[str, Any]] = []
    max_source_depth = 0

    for sid in direct_ids:
        src = by_id.get(sid)
        if src is not None:
            max_source_depth = max(max_source_depth, _generation_depth_of(src))

    queue = deque((sid, 0) for sid in direct_ids)
    visited = set()
    while queue:
        sid, hop = queue.popleft()
        if sid in visited:
            continue
        visited.add(sid)
        src = by_id.get(sid)
        if src is None:
            if sid not in raw_seen:
                raw_seen.add(sid)
                raw_source_ids.append(sid)
            continue
        parents = _sanitize_source_ids(src.get("source_memory_ids"))
        if parents and hop < max_hops:
            for pid in parents:
                if pid not in visited:
                    queue.append((pid, hop + 1))
        else:
            if sid not in raw_seen:
                raw_seen.add(sid)
                raw_source_ids.append(sid)
                raw_sources.append({
                    "id": sid,
                    "text": str(src.get("text") or ""),
                    "tick": src.get("tick"),
                    "type": str(src.get("type") or ""),
                    "source": str(src.get("source") or ""),
                    "lane": classify_memory_lane(src),
                    "generation_depth": _generation_depth_of(src),
                })

    return {
        "direct_source_ids": direct_ids,
        "raw_source_ids": raw_source_ids,
        "raw_sources": raw_sources,
        "max_source_depth": max_source_depth,
    }


def _resolve_player_node_id(player: Any, gs: Any = None) -> Optional[str]:
    if player is None:
        return None
    nid = getattr(player, "node_id", None)
    if nid:
        return str(nid)
    pm = getattr(gs, "player_manager", None) if gs is not None else None
    if pm is not None and callable(getattr(pm, "get_player_node_id", None)):
        try:
            return pm.get_player_node_id(player)
        except Exception:
            pass
    if gs is not None and callable(getattr(gs, "_player_node_id", None)):
        try:
            return gs._player_node_id(getattr(player, "name", ""))
        except Exception:
            pass
    pname = str(getattr(player, "name", "") or "").strip()
    return f"player_{pname.replace(' ', '_')}" if pname else None


def build_factual_lane(player: Any, gs: Any = None) -> Dict[str, Any]:
    """Assemble the unvarnished deterministic lane for a character.

    Reads only deterministic world/player state (inventory, spatial_memory
    topology, door/lock states, and AlreadyKnown grounding) and never reads
    subjective palimpsest reflections or Intermediator summaries.
    """
    graph = getattr(gs, "graph", None) if gs is not None else None
    player_node_id = _resolve_player_node_id(player, gs)

    # 1. Deterministic inventory (carried & equipped graph edges, fallback to player.inventory)
    inventory: List[Dict[str, Any]] = []
    seen_inv = set()
    if graph is not None and player_node_id:
        try:
            from graph import EDGE_CARRYING, EDGE_EQUIPPED
            for etype in (EDGE_CARRYING, EDGE_EQUIPPED):
                for edge in graph.get_edges_for_target(player_node_id, etype):
                    item_node = graph.get_node(edge.source)
                    if item_node is None or item_node.id in seen_inv:
                        continue
                    seen_inv.add(item_node.id)
                    inventory.append({
                        "id": item_node.id,
                        "name": str(getattr(item_node, "name", "") or item_node.id),
                        "equipped": etype == EDGE_EQUIPPED,
                    })
        except Exception:
            pass
    if not inventory:
        for item in (getattr(player, "inventory", None) or []):
            if isinstance(item, dict):
                iid = str(item.get("id") or item.get("name") or "")
                if iid and iid not in seen_inv:
                    seen_inv.add(iid)
                    inventory.append({
                        "id": iid,
                        "name": str(item.get("name") or iid),
                        "equipped": bool(item.get("equipped")),
                    })
            elif item:
                iid = str(item)
                if iid not in seen_inv:
                    seen_inv.add(iid)
                    inventory.append({"id": iid, "name": iid, "equipped": False})

    # 2. Deterministic spatial_memory topology
    current_area = getattr(player, "current_area", None)
    known_areas: List[str] = []
    if graph is not None:
        try:
            from engine.spatial_memory import known_route_areas
            known_areas = sorted(str(a) for a in known_route_areas(player, graph) if a)
        except Exception:
            known_areas = []
    if not known_areas:
        raw_known = set()
        for entry in (getattr(player, "known", None) or []):
            if entry:
                raw_known.add(str(entry))
        for entry in (getattr(player, "known_areas", None) or []):
            if entry:
                raw_known.add(str(entry))
        if current_area:
            raw_known.add(str(current_area))
        known_areas = sorted(raw_known)

    known_way_aspects: Dict[str, List[str]] = {}
    for k, v in (getattr(player, "known_way_aspects", None) or {}).items():
        key_str = f"{k[0]}:{k[1]}" if isinstance(k, tuple) and len(k) == 2 else str(k)
        known_way_aspects[key_str] = sorted(str(x) for x in (v or []) if x)

    # 3. Deterministic door/lock states from graph ways/nodes & factual lock memories
    door_locks: List[Dict[str, Any]] = []
    seen_doors = set()
    known_set = {a.lower() for a in known_areas}
    if current_area:
        known_set.add(str(current_area).lower())
    if graph is not None:
        try:
            from engine.matching import way_endpoint_name
        except Exception:
            way_endpoint_name = None
        for node in (getattr(graph, "nodes", None) or {}).values():
            ntype = str(getattr(node, "type", "") or "").lower()
            props = getattr(node, "properties", None) or {}
            has_lock = any(k in props for k in ("locked", "is_locked", "lock_id", "key_id"))
            state_str = str(props.get("current_state") or "").strip().lower()
            is_door_like = ntype == "way" or has_lock or state_str in ("locked", "unlocked", "open", "closed")
            if not is_door_like:
                continue
            relevant = False
            if ntype == "way" and way_endpoint_name is not None:
                from_name = str(way_endpoint_name(node, graph, "from") or "").lower()
                to_name = str(way_endpoint_name(node, graph, "to") or "").lower()
                relevant = (from_name in known_set) or (to_name in known_set) or (str(node.id).lower() in known_set)
            else:
                relevant = (str(node.id).lower() in known_set) or not known_set
            if not relevant or node.id in seen_doors:
                continue
            seen_doors.add(node.id)
            door_locks.append({
                "id": node.id,
                "name": str(getattr(node, "name", "") or node.id),
                "state": str(props.get("current_state") or ""),
                "locked": bool(props.get("locked") or props.get("is_locked") or state_str == "locked"),
            })
    for m in (getattr(player, "memories", None) or []):
        if not isinstance(m, dict) or m.get("superseded_by"):
            continue
        if not is_factual_memory(m):
            continue
        mkind = str(m.get("kind") or "").strip().lower()
        if mkind not in ("door", "lock", "way", "way_state"):
            continue
        mdata = m.get("data") if isinstance(m.get("data"), dict) else {}
        did = str(mdata.get("id") or mdata.get("way_id") or m.get("id") or "")
        if did and did not in seen_doors:
            seen_doors.add(did)
            mstate = str(mdata.get("state") or mdata.get("current_state") or "").strip().lower()
            door_locks.append({
                "id": did,
                "name": str(mdata.get("name") or m.get("text") or did),
                "state": mstate,
                "locked": bool(mdata.get("locked") or mdata.get("is_locked") or mstate == "locked"),
            })

    # 4. Deterministic AlreadyKnown grounding (visited areas, discovered items, active absences)
    visited_areas: List[str] = []
    if callable(getattr(player, "visited_area_names", None)):
        try:
            visited_areas = sorted(str(a) for a in (player.visited_area_names(graph) or ()) if a)
        except TypeError:
            visited_areas = sorted(str(a) for a in (player.visited_area_names() or ()) if a)

    discovered_items: List[str] = []
    if callable(getattr(player, "discovered_item_names", None)):
        try:
            discovered_items = sorted(str(i) for i in (player.discovered_item_names(graph) or ()) if i)
        except TypeError:
            discovered_items = sorted(str(i) for i in (player.discovered_item_names() or ()) if i)

    absences: List[Dict[str, Any]] = []
    for m in (getattr(player, "memories", None) or []):
        if not isinstance(m, dict) or m.get("superseded_by"):
            continue
        if m.get("kind") == "absence":
            data = m.get("data") if isinstance(m.get("data"), dict) else {}
            absences.append({
                "id": m.get("id"),
                "target": str(m.get("target") or data.get("expected_item") or ""),
                "location": str(m.get("location") or data.get("subject") or ""),
                "tick": m.get("tick"),
            })

    return {
        "inventory": inventory,
        "spatial_memory": {
            "current_area": current_area,
            "known_areas": known_areas,
            "known_way_aspects": known_way_aspects,
        },
        "door_locks": door_locks,
        "already_known": {
            "visited_areas": visited_areas,
            "discovered_items": discovered_items,
            "absences": absences,
        },
    }


extract_factual_lane = build_factual_lane


def partition_memories_by_lane(memories: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Split memories into deterministic factual records and subjective palimpsest entries."""
    factual: List[Dict[str, Any]] = []
    palimpsest: List[Dict[str, Any]] = []
    for m in (memories or []):
        if is_factual_memory(m):
            factual.append(m)
        else:
            palimpsest.append(m)
    return {LANE_FACTUAL: factual, LANE_PALIMPSEST: palimpsest}


def synthesize_palimpsest_memory(
    player: Any,
    text: str,
    tick: int,
    *,
    source_memories: Optional[Iterable[Dict[str, Any]]] = None,
    source_memory_ids: Optional[Iterable[str]] = None,
    importance: int = 6,
    memory_type: str = "reflection",
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    source: str = "intermediator",
    location: Optional[str] = None,
    emotion: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Persist a derived subjective palimpsest memory with immutable source lineage.

    Deterministic factual memories (inventory, spatial_memory, door/lock,
    AlreadyKnown) are never modified or superseded by palimpsest synthesis, and
    the derived record carries immutable raw ``source_memory_ids`` plus
    ``generation_depth``.
    """
    clean_text = str(text or "").strip()
    if player is None or not clean_text:
        return None

    pool = list(getattr(player, "memories", None) or [])
    cand_ids = _sanitize_source_ids(list(source_memory_ids or []))
    for sm in (source_memories or []):
        if isinstance(sm, dict) and sm.get("id"):
            sid = str(sm["id"]).strip()
            if sid and sid not in cand_ids:
                cand_ids.append(sid)

    lineage = resolve_source_lineage(pool, cand_ids)
    # Keep immutable raw source observation refs when traceable, otherwise direct refs
    immutable_sources = lineage["raw_source_ids"] or lineage["direct_source_ids"]
    gen_depth = max(1, lineage["max_source_depth"] + 1)

    resolved_loc = str(location if location is not None else (getattr(player, "current_area", "") or ""))
    mem = player.add_memory(
        clean_text,
        tick=int(tick or 0),
        importance=importance,
        memory_type=memory_type,
        tags=list(tags or [source]),
        source=source,
        location=resolved_loc,
        category=category,
    )
    if isinstance(mem, dict):
        mem["source_memory_ids"] = list(immutable_sources)
        mem["generation_depth"] = gen_depth
        mem["lane"] = LANE_PALIMPSEST
        if mem.get("reflection_depth") is None or int(mem.get("reflection_depth") or 0) < 1:
            mem["reflection_depth"] = 1
        if isinstance(emotion, dict) and emotion.get("label"):
            mem["emotion"] = dict(emotion)
    return mem


def _closeness_text(entry) -> str:
    delta = entry.get("delta") or {}
    other = str(delta.get("with") or "them")
    try:
        amount = int(delta.get("closeness", 0) or 0)
    except (TypeError, ValueError):
        amount = 0
    cause = str(delta.get("cause") or "").strip()
    if amount > 0:
        base = f"I feel a little closer to {other} now."
    elif amount < 0:
        base = f"Something about {other} has me wary."
    else:
        base = f"Something involving {other} stayed with me."
    return f"{base} ({cause})" if cause else base


def _capitalize(text: str) -> str:
    text = text.strip()
    return (text[:1].upper() + text[1:]) if text else text


def phrase(entry) -> str:
    """First-person memory text for a lived entry, or ``''`` when none."""
    kind = str(entry.get("kind") or "")
    what = str(entry.get("what") or "")
    if kind == "relationship":
        return _closeness_text(entry)
    if kind == "death":
        cause = what[len("died of "):] if what.startswith("died of ") else what
        cause = cause.strip()
        return f"I died - {cause}." if cause else "I died."
    if kind == "resurrection":
        cause = what[len("resurrected: "):] if what.startswith("resurrected: ") else what
        cause = cause.strip()
        return f"I was brought back from death - {cause}." if cause else "I was brought back from death."
    if kind == "pursuit":
        text = _capitalize(what)
        return text + ("." if text and not text.endswith(".") else "")
    return ""


def _importance(entry) -> int:
    if entry.get("salient"):
        return 8
    kind = str(entry.get("kind") or "")
    if kind in ("death", "resurrection"):
        return 5
    return 4


def bridge(player, gs=None) -> int:
    """Write a first-person memory for each un-phrased meaningful lived entry.

    Returns the number of memories written. Never raises.
    """
    log = getattr(player, "lived_log", []) or []
    if not log:
        return 0
    mark = int(getattr(player, "lived_log_memorized_through", 0) or 0)
    processed_at_mark = getattr(player, "lived_log_memorized_at_mark", None)
    newest = mark
    seen_at_mark = 0
    newest_count = 0
    written = 0
    for idx, entry in enumerate(log):
        try:
            tick = int(entry.get("tick", 0) or 0)
        except (TypeError, ValueError):
            tick = 0
        if tick < mark:
            continue
        if tick == mark:
            seen_at_mark += 1
            if processed_at_mark is None:
                if mark > 0:
                    continue
            elif seen_at_mark <= int(processed_at_mark):
                continue
        if tick > newest:
            newest = tick
            newest_count = 1
        elif tick == newest and newest > mark:
            newest_count += 1
        # Two-Lane Factual Invariant: never paraphrase deterministic inventory,
        # spatial_memory, door/lock, or AlreadyKnown entries into palimpsest memories.
        if is_factual_entry(entry):
            continue
        kind = str(entry.get("kind") or "")
        if kind not in MEMORIZABLE_KINDS:
            continue
        text = phrase(entry)
        if not text:
            continue
        tags = [kind]
        if kind == "relationship":
            other = str((entry.get("delta") or {}).get("with") or "").strip()
            if other:
                tags.append("rel:" + other)
        entry_ref = str(entry.get("id") or f"lived_log:{tick}:{idx}")
        source_ids = _sanitize_source_ids(list(entry.get("source_memory_ids") or []) + [entry_ref])
        gen_depth = max(1, _generation_depth_of(entry))
        try:
            mem = player.add_memory(
                text, tick=tick, importance=_importance(entry),
                memory_type="reaction", tags=tags, source="lived_log",
                location=str(entry.get("area") or ""),
            )
            if isinstance(mem, dict):
                mem["source_memory_ids"] = list(source_ids)
                mem["generation_depth"] = gen_depth
                mem["lane"] = LANE_PALIMPSEST
            written += 1
        except Exception as exc:  # a memory write must never break a turn
            logger.warning("[lived_log_memory] %s: %s",
                           getattr(player, "name", "?"), exc)
    if newest > mark:
        player.lived_log_memorized_through = newest
        player.lived_log_memorized_at_mark = newest_count
    elif seen_at_mark > (int(processed_at_mark) if processed_at_mark is not None else 0):
        player.lived_log_memorized_at_mark = seen_at_mark
    return written


def bridge_all(gs) -> int:
    """Bridge every player's un-phrased lived entries. Safe to call per turn."""
    players = getattr(gs, "players", None)
    if not players:
        return 0
    total = 0
    for player in list(players.values()):
        total += bridge(player, gs)
    return total
