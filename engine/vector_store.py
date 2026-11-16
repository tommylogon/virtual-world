"""VectorStore - lightweight JSON-file embedding store for semantic memory.

Task-91. Delegates directly to the shared ``story_memory.core.vector_store``
engine so VirtualWorld and standalone story_memory share one implementation.

@module vector_store
@contributes VectorStore, _cosine
@docs docs/virtualWorld/Gameplay/Search & Forage.md
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_story_memory() -> None:
    try:
        import story_memory  # noqa: F401
        return
    except ImportError:
        pass
    candidates = []
    if os.environ.get("STORY_MEMORY_PATH"):
        candidates.append(Path(os.environ["STORY_MEMORY_PATH"]))
    candidates.append(Path(__file__).resolve().parents[3] / "code" / "story_memory")
    for cand in candidates:
        if cand.is_dir() and str(cand) not in sys.path:
            sys.path.insert(0, str(cand))
            return


_ensure_story_memory()

from story_memory.core.vector_store import VectorStore, _cosine

__all__ = ["VectorStore", "_cosine"]
