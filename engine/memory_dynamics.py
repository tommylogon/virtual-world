"""Memory dynamics: activation decay, spaced reinforcement, contradictions, and consolidation.

Delegates pure-Python dynamics math and lifecycle transforms to the shared
``story_memory.core.dynamics`` module while preserving VirtualWorld's
runtime config lookup for ``consolidation_pressure`` and reference cleanup
for deleted/consolidated memories.

@module memory_dynamics
@contributes ensure_dynamics defaults, effective_importance scoring, reinforcement, activation decay with per-memory resistance, contradiction linking, consolidation, unlink_memory_references
@powers Memory - what characters remember, and when they reflect on it
@docs docs/virtualWorld/AI & Narration/Memory Dynamics.md
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from engine.vector_store import VectorStore, _ensure_story_memory

_ensure_story_memory()

from story_memory.core import dynamics as _core_dynamics
from story_memory.core.dynamics import (
    ACTIVATION_FLOOR,
    BELIEF,
    CATEGORY_FOR_TYPE,
    CONSOLIDATE_KEY,
    DECAY_RATE_KEY,
    EPISODIC,
    HALF_DECAY_SOURCES,
    NON_DECAYING_SOURCES,
    PROCEDURAL,
    QUESTION,
    SEMANTIC,
    SOCIAL,
    _CONTENT_STOPWORDS,
    _NEGATION_WORDS,
    _SENTIMENT_VERBS,
    _WORD_RE,
    _content_tokens,
    _forget_index,
    _has_negation,
    _is_attitude_statement,
    _memory_contradicts_list,
    _memory_emotions,
    _memory_entities,
    _memory_importance,
    _memory_matches_tags,
    _memory_seq,
    _memory_text,
    _removable,
    _unit,
    apply_decay as _core_apply_decay,
    category_for as _core_category_for,
    consolidate_sleep,
    decay_resistance,
    detect_contradiction,
    effective_importance,
    ensure_dynamics as _core_ensure_dynamics,
    link,
    reinforce as _core_reinforce,
    reinforce_all,
    revise_contradicted_belief,
)

SEMANTIC_SEED_TAGS = frozenset({
    "school", "family", "parent", "hobby", "trade", "knowledge_seed", "education", "lore", "backstory",
})
PROCEDURAL_DISUSE_GRACE_TICKS = 50


def category_for(memory: Dict[str, Any]) -> str:
    """Derive memory category, keeping semantic school/life seeds and procedural skills distinct."""
    explicit = memory.get("category")
    if explicit:
        return str(explicit)
    kind = str(memory.get("kind") or "").strip().lower()
    if kind == "semantic":
        return SEMANTIC
    if kind == "procedural":
        return PROCEDURAL
    mtype = str(memory.get("type") or "").strip().lower()
    if mtype in ("recipe", "skill", "procedural"):
        return PROCEDURAL
    if mtype in ("semantic", "fact", "lore"):
        return SEMANTIC
    source = str(memory.get("source") or "").strip().lower()
    if source in ("backstory", "knowledge"):
        return SEMANTIC
    tags = {str(t).strip().lower() for t in (memory.get("tags") or ()) if t}
    if tags & SEMANTIC_SEED_TAGS:
        return SEMANTIC
    return _core_category_for(memory)


def ensure_dynamics(memory: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure lifecycle defaults while preserving semantic/procedural categorization."""
    if not memory.get("category"):
        memory["category"] = category_for(memory)
    return _core_ensure_dynamics(memory)


def reinforce(memory: Dict[str, Any], *args: Any, **kwargs: Any) -> Any:
    """Reinforce memory activation and reset procedural disuse tracking when used."""
    res = _core_reinforce(memory, *args, **kwargs)
    if category_for(memory) == PROCEDURAL:
        tick = kwargs.get("tick")
        if tick is None and args:
            tick = args[0]
        if tick is not None:
            memory["last_used_tick"] = int(tick)
        memory["disuse_ticks"] = 0
    return res


def mark_procedural_used(memory: Dict[str, Any], tick: Optional[int] = None) -> Any:
    """Record active use of a procedural skill/recipe and reinforce its activation."""
    return reinforce(memory, tick=tick)


def apply_decay(
    player: Any,
    rate: float,
    tick: Optional[int] = None,
    procedural_grace_ticks: int = PROCEDURAL_DISUSE_GRACE_TICKS,
) -> int:
    """Apply activation decay: semantic school/life knowledge never decays;
    procedural skills/recipes follow disuse-decay; episodic memories decay normally.
    """
    if rate <= 0:
        return 0
    persona_tags = {
        "dislike_tags": getattr(player, "dislike_tags", None) or (),
        "interest_tags": getattr(player, "interest_tags", None) or (),
        "fear_tags": getattr(player, "fear_tags", None) or (),
    }
    for memory in list(getattr(player, "memories", []) or []):
        ensure_dynamics(memory)
        source = str(memory.get("source", ""))
        if source in NON_DECAYING_SOURCES or memory.get("core"):
            continue
        cat = category_for(memory)
        if cat == SEMANTIC or memory.get("kind") == "semantic":
            continue
        res = decay_resistance(memory, persona_tags=persona_tags)
        cur_act = _core_dynamics._memory_activation(memory)
        if cat == PROCEDURAL or memory.get("kind") == "procedural":
            if tick is not None:
                last_used = memory.get("last_used_tick")
                if last_used is None:
                    last_used = memory.get("last_recalled_tick", memory.get("tick", 0))
                disuse = max(0, int(tick) - int(last_used or 0))
                memory["disuse_ticks"] = disuse
                if disuse <= procedural_grace_ticks:
                    continue
                over_grace = disuse - procedural_grace_ticks
                disuse_mult = min(2.0, 0.25 + (over_grace / max(1, procedural_grace_ticks)) * 0.5)
                step = rate * disuse_mult * res
            else:
                step = rate * 0.25 * res
            next_act = round(max(ACTIVATION_FLOOR, cur_act - step), 4)
            _core_dynamics._set_memory_activation(memory, next_act)
            continue
        step = rate * (0.5 if source in HALF_DECAY_SOURCES else 1.0) * res
        next_act = round(max(0.0, cur_act - step), 4)
        _core_dynamics._set_memory_activation(memory, next_act)
    return 0


def unlink_memory_references(
    player: Any,
    memory_id: Optional[str],
    data_dir: Optional[str] = None,
) -> Dict[str, int]:
    """Remove dangling contradicts links, memory_index pointers, and VectorStore vectors.

    Used when a memory is deleted or folded during consolidation (bug-602).
    """
    counts = {"contradicts_removed": 0, "index_removed": 0, "vectors_removed": 0}
    if not memory_id:
        return counts
    mid = str(memory_id)

    for mem in (getattr(player, "memories", None) or []):
        if not isinstance(mem, dict):
            continue
        contra = mem.get("contradicts")
        if isinstance(contra, list) and mid in contra:
            before = len(contra)
            mem["contradicts"] = [cid for cid in contra if cid != mid]
            counts["contradicts_removed"] += before - len(mem["contradicts"])
        lc = mem.get("lifecycle")
        if isinstance(lc, dict) and isinstance(lc.get("contradicts"), list) and mid in lc["contradicts"]:
            before = len(lc["contradicts"])
            lc["contradicts"] = [cid for cid in lc["contradicts"] if cid != mid]
            counts["contradicts_removed"] += before - len(lc["contradicts"])

    index = getattr(player, "memory_index", None)
    if isinstance(index, dict):
        stale = [k for k, v in index.items() if v == mid]
        for k in stale:
            index.pop(k, None)
        counts["index_removed"] = len(stale)

    if data_dir:
        try:
            keys: List[str] = []
            pname = getattr(player, "name", None)
            pid = getattr(player, "id", None)
            if pname:
                keys.append(f"{pname}::{mid}")
            if pid and pid != pname:
                keys.append(f"{pid}::{mid}")
            if keys:
                counts["vectors_removed"] = VectorStore(data_dir).remove_keys(keys)
        except Exception:
            pass

    return counts


def consolidation_pressure(player) -> bool:
    """True when the store is crowded enough to warrant consolidation."""
    try:
        from player import MEMORY_LIMIT_KEY
        from engine.runtime_config import config

        limit = int(config.get(MEMORY_LIMIT_KEY, 0) or 0)
    except Exception:
        return False
    return _core_dynamics.consolidation_pressure(player, memory_limit=limit)


def consolidate(
    player,
    tick: Optional[int] = None,
    min_group: int = 3,
    max_importance: float = 4.0,
    data_dir: Optional[str] = None,
) -> Dict[str, int]:
    """Fold stale low-importance episodes and scrub dangling references from surviving records."""
    before_ids = {
        str(m.get("id"))
        for m in (getattr(player, "memories", None) or [])
        if isinstance(m, dict) and m.get("id")
    }
    result = _core_dynamics.consolidate(
        player,
        tick=tick,
        min_group=min_group,
        max_importance=max_importance,
    )
    after_ids = {
        str(m.get("id"))
        for m in (getattr(player, "memories", None) or [])
        if isinstance(m, dict) and m.get("id")
    }
    removed_ids = before_ids - after_ids
    resolved_dir = data_dir or getattr(player, "data_dir", None)
    for rid in removed_ids:
        unlink_memory_references(player, rid, data_dir=resolved_dir)
    return result


__all__ = [
    "EPISODIC",
    "SEMANTIC",
    "PROCEDURAL",
    "SOCIAL",
    "BELIEF",
    "QUESTION",
    "CATEGORY_FOR_TYPE",
    "NON_DECAYING_SOURCES",
    "HALF_DECAY_SOURCES",
    "ACTIVATION_FLOOR",
    "DECAY_RATE_KEY",
    "CONSOLIDATE_KEY",
    "_NEGATION_WORDS",
    "_CONTENT_STOPWORDS",
    "_WORD_RE",
    "_SENTIMENT_VERBS",
    "category_for",
    "ensure_dynamics",
    "effective_importance",
    "_unit",
    "reinforce",
    "reinforce_all",
    "_memory_matches_tags",
    "_memory_importance",
    "_memory_emotions",
    "_memory_entities",
    "_memory_contradicts_list",
    "_memory_text",
    "_memory_seq",
    "decay_resistance",
    "_removable",
    "apply_decay",
    "mark_procedural_used",
    "SEMANTIC_SEED_TAGS",
    "PROCEDURAL_DISUSE_GRACE_TICKS",
    "_forget_index",
    "_content_tokens",
    "_has_negation",
    "_is_attitude_statement",
    "link",
    "detect_contradiction",
    "unlink_memory_references",
    "consolidation_pressure",
    "consolidate",
    "consolidate_sleep",
    "revise_contradicted_belief",
]
