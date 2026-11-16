"""Associative multi-facet memory retrieval engine.

Delegates cue extraction, multi-facet scoring, open-question matching, and
three-lane retrieval to the shared ``story_memory.core.retrieval`` module.

@module engine/memory_retrieval
@contributes retrieve_associative_memories, score_memory, extract_cues
@docs docs/virtualWorld/memory_architecture.md
"""
from __future__ import annotations

import logging

from engine.vector_store import _ensure_story_memory

_ensure_story_memory()

from story_memory.core.retrieval import (
    NEED_TAG_MAP,
    STOPWORDS,
    extract_cues,
    is_active_memory,
    is_open_question_match,
    normalize_tokens,
    retrieve_associative_memories,
    score_memory,
)

logger = logging.getLogger(__name__)

__all__ = [
    "logger",
    "STOPWORDS",
    "NEED_TAG_MAP",
    "normalize_tokens",
    "extract_cues",
    "is_active_memory",
    "score_memory",
    "is_open_question_match",
    "retrieve_associative_memories",
]
