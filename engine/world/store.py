"""Durable per-scope graph slices for production chunk loading.

@module world_scope_store
@contributes atomic scope chunk persistence and reloads
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WorldChunkStore:
    """Store one atomically replaced JSON graph slice per scope."""

    def __init__(self, root: str | os.PathLike):
        self.root = Path(root)

    def _path(self, scope_id: str) -> Path:
        digest = hashlib.sha256(str(scope_id).encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def load_scope(self, scope_id: str) -> Optional[dict]:
        path = self._path(scope_id)
        if not path.is_file():
            return None
        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
        if not isinstance(payload, dict) or payload.get("scope_id") != str(scope_id):
            raise ValueError(f"Invalid persisted graph slice for scope {scope_id!r}")
        if not isinstance(payload.get("nodes"), dict) or not isinstance(
                payload.get("edges"), list):
            raise ValueError(f"Incomplete persisted graph slice for scope {scope_id!r}")
        return payload

    def save_scope(self, scope_id: str, payload: dict) -> None:
        if not isinstance(payload, dict) or payload.get("scope_id") != str(scope_id):
            raise ValueError(f"Graph slice does not belong to scope {scope_id!r}")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(scope_id)
        temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        logger.debug("persisted scope %s (%d bytes)", scope_id, path.stat().st_size)


def configure_scope_store(world, data_dir: str | os.PathLike) -> WorldChunkStore:
    """Attach the production store to the current world's global scope index."""
    index = getattr(world, "world_index", None)
    if index is None:
        raise ValueError("Cannot configure scope storage without a world index")

    stable_id = getattr(world, "_scope_store_id", None)
    if not stable_id:
        source = getattr(world, "_scenario_source", None)
        name = getattr(world, "_scenario_name", None)
        identity = os.path.normcase(os.path.abspath(source)) if source else (
            str(name).strip() or "unnamed")
        stable_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        world._scope_store_id = stable_id
    world_key = hashlib.sha256(str(stable_id).encode("utf-8")).hexdigest()
    store = WorldChunkStore(Path(data_dir) / "world_chunks" / world_key)
    index.register_loader(store.load_scope, store.save_scope)
    world.scope_store = store
    return store
