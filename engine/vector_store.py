"""VectorStore — lightweight JSON-file embedding store for semantic memory.

Task-91. Stores memory embeddings as ``{key: [float, ...]}`` in
``data/embeddings.json`` and answers cosine-similarity top-k searches.
No external dependencies: brute-force cosine over a few thousand vectors is
sub-millisecond territory compared to the LLM calls around it.

Key format is ``"<Character>::<memory_id>"`` so a character's vectors can be
listed/removed wholesale when memories are cleared.

File format::

    {"model": "nomic-embed-text", "dims": 768,
     "vectors": {"Lyrie::mem_123_456": [0.1, ...]}}

The model/dims header records what produced the stored vectors. A mismatch
between an incoming upsert and the stored dims is rejected (mixing vector
spaces makes search meaningless) — callers re-embed or clear instead.
"""

import json
import math
import os
import tempfile


def _cosine(a, b):
    """Cosine similarity of two equal-length float lists; 0.0 if either norm is 0."""
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


class VectorStore:
    """JSON-backed vector index. Instantiate per operation with the data dir."""

    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, "embeddings.json")
        self._data = None

    # -- persistence -------------------------------------------------------

    def _load(self):
        if self._data is not None:
            return self._data
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if not isinstance(raw.get("vectors"), dict):
                raise ValueError("missing vectors dict")
            self._data = {
                "model": raw.get("model") or "",
                "dims": int(raw.get("dims") or 0),
                "vectors": {str(k): [float(x) for x in v]
                            for k, v in raw["vectors"].items()},
            }
        except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
            self._data = {"model": "", "dims": 0, "vectors": {}}
        return self._data

    def _save(self):
        data = self._load()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(self.path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            os.replace(tmp_path, self.path)
        except OSError:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    # -- operations --------------------------------------------------------

    def stats(self):
        data = self._load()
        return {"count": len(data["vectors"]), "model": data["model"],
                "dims": data["dims"]}

    def upsert(self, items, model="", dims=0):
        """Insert/update ``[{key, vector}]``. Returns count written.

        Raises ``ValueError`` on dimension mismatch with existing contents so
        mixed-vector-space files can never happen.
        """
        data = self._load()
        stored_dims = data["dims"]
        for item in items:
            key = str(item.get("key") or "").strip()
            vector = item.get("vector")
            if not key or not isinstance(vector, (list, tuple)) or not vector:
                continue
            vec = [float(x) for x in vector]
            if stored_dims and len(vec) != stored_dims:
                raise ValueError(
                    f"dimension mismatch: store has {stored_dims}, "
                    f"'{key}' has {len(vec)}")
            data["vectors"][key] = vec
            if not stored_dims:
                stored_dims = len(vec)
        if items:
            data["dims"] = stored_dims or dims
            if model:
                data["model"] = model
            self._save()
        return sum(1 for i in items
                   if i.get("key") and i.get("vector"))

    def search(self, query_vector, character=None, k=5):
        """Top-k ``{key, score, character, memory_id}`` by cosine similarity.

        ``character`` filters to one character's keys. Zero-norm query
        vectors return no results.
        """
        data = self._load()
        query = [float(x) for x in (query_vector or [])]
        qnorm = math.sqrt(sum(x * x for x in query))
        if qnorm == 0.0:
            return []
        prefix = f"{character}::" if character else None
        scored = []
        for key, vec in data["vectors"].items():
            if len(vec) != len(query):
                continue
            if prefix and not key.startswith(prefix):
                continue
            scored.append(((_cosine(query, vec)), key))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        results = []
        for score, key in scored[: max(1, int(k))]:
            char, _, mem_id = key.partition("::")
            results.append({"key": key, "score": round(score, 6),
                            "character": char, "memory_id": mem_id})
        return results

    def remove_character(self, character):
        """Drop all vectors for one character. Returns count removed."""
        data = self._load()
        prefix = f"{character}::"
        doomed = [k for k in data["vectors"] if k.startswith(prefix)]
        for k in doomed:
            del data["vectors"][k]
        if doomed:
            self._save()
        return len(doomed)

    def known_keys(self, character=None):
        data = self._load()
        if character:
            prefix = f"{character}::"
            return [k for k in data["vectors"] if k.startswith(prefix)]
        return list(data["vectors"].keys())
