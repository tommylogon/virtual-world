"""Memory dynamics: activation decay, spaced reinforcement, contradictions, and consolidation.

Delegates pure-Python dynamics math and lifecycle transforms to the shared
``story_memory.core.dynamics`` module while preserving VirtualWorld's
runtime config lookup for ``consolidation_pressure``.

@module memory_dynamics
@contributes ensure_dynamics defaults, effective_importance scoring, reinforcement, activation decay with per-memory resistance, contradiction linking, consolidation
@powers Memory - what characters remember, and when they reflect on it
@docs docs/virtualWorld/AI & Narration/Memory Dynamics.md
"""
from __future__ import annotations

from engine.vector_store import _ensure_story_memory

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
    _memory_matches_tags,
    _removable,
    _unit,
    apply_decay,
    category_for,
    consolidate,
    consolidate_sleep,
    decay_resistance,
    detect_contradiction,
    effective_importance,
    ensure_dynamics,
    link,
    reinforce,
    reinforce_all,
    revise_contradicted_belief,
)


def consolidation_pressure(player) -> bool:
    """True when the store is crowded enough to warrant consolidation."""
    try:
        from player import MEMORY_LIMIT_KEY
        from engine.runtime_config import config

        limit = int(config.get(MEMORY_LIMIT_KEY, 0) or 0)
    except Exception:
        return False
    return _core_dynamics.consolidation_pressure(player, memory_limit=limit)


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
    "decay_resistance",
    "_removable",
    "apply_decay",
    "_forget_index",
    "_content_tokens",
    "_has_negation",
    "_is_attitude_statement",
    "link",
    "detect_contradiction",
    "consolidation_pressure",
    "consolidate",
    "consolidate_sleep",
    "revise_contradicted_belief",
]
