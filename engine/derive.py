"""Experience-driven relationship derivation (task-350).

Delegates deterministic relationship profile derivation to the shared
``story_memory.core.derive`` package while injecting VirtualWorld's
``engine.relationships.get_relationship`` seed lookup.

@module derive
@contributes _fresh, clamp, expand_emotion_data, fold_emotions_into_profile, _memory_for, derive_person_profile
@docs docs/virtualWorld/AI & Narration/Memory System.md
"""
from __future__ import annotations

from typing import Optional

from engine.vector_store import _ensure_story_memory

_ensure_story_memory()

from story_memory.core import derive as _core_derive
from story_memory.core.derive import (
    CONSENT_SCALE,
    DATA_KEY_TO_DIM,
    DIMS,
    EMOTION_DELTA_MAX,
    SIGNAL_DIMS,
    _fresh,
    _infer_role,
    _memory_for,
    _memory_weight,
    _to_nl,
    clamp,
    expand_emotion_data,
    finalize,
    fold_emotions_into_profile,
)


def _viwo_get_relationship(player, other_name: str) -> Optional[dict]:
    try:
        from engine.relationships import get_relationship

        return get_relationship(player, other_name)
    except Exception:
        return None


def derive_person_profile(player, other_name: str) -> dict:
    """Return derived relationship profile for ``other_name`` (never None)."""
    return _core_derive.derive_person_profile(
        player,
        other_name,
        relationship_getter=_viwo_get_relationship,
    )


__all__ = [
    "DIMS",
    "CONSENT_SCALE",
    "SIGNAL_DIMS",
    "EMOTION_DELTA_MAX",
    "DATA_KEY_TO_DIM",
    "_fresh",
    "clamp",
    "_memory_weight",
    "expand_emotion_data",
    "fold_emotions_into_profile",
    "_memory_for",
    "derive_person_profile",
    "finalize",
    "_infer_role",
    "_to_nl",
]
