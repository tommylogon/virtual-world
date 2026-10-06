"""Activity definition loader — data-driven activity metadata (task-716).

Activities are JSON files under ``data/library/activities/``. Adding a new
activity is a JSON edit; no Python change is required unless the activity needs
a new tick action or completion checker.
"""

import json
import os
from typing import Dict, Optional

_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "library", "activities",
)

_cache: Dict[str, dict] = {}


def load(fresh: bool = False) -> Dict[str, dict]:
    key = os.path.abspath(_DATA_PATH)
    if fresh or key not in _cache:
        catalog: Dict[str, dict] = {}
        if os.path.isdir(key):
            for fname in sorted(os.listdir(key)):
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(key, fname)
                try:
                    with open(path, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                    aid = str(data.get("id") or fname[:-5])
                    catalog[aid] = data
                except Exception:
                    pass
        _cache[key] = catalog
    return _cache.get(key, {})


def clear_cache() -> None:
    _cache.clear()


def get(activity_id: str) -> Optional[dict]:
    return load().get(str(activity_id))
