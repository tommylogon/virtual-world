"""Markov biome adjacency matrix and transition gradients (task-884).

Provides gradient transition buffers and forbidden adjacency validation
for WorldPainter procedural generation and smart feather brushes.

@module world_adjacencies
@contributes load_adjacency_data, is_valid_transition, suggest_buffer, feather_seam
@docs docs/virtualWorld/World Building/WorldPainter.md
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Set, Tuple

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "worldpainter", "adjacency.json"
)

_cached_data: Optional[dict] = None


def load_adjacency_data(path: Optional[str] = None, *, fresh: bool = False) -> dict:
    """Load and cache the adjacency matrix."""
    global _cached_data
    if fresh or _cached_data is None or path is not None:
        p = path or DATA_PATH
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {"version": 1, "gradients": {}, "affinities": {}, "prohibited": []}
        if path is None:
            _cached_data = data
        return data
    return _cached_data


def is_valid_transition(biome_a: str, biome_b: str, path: Optional[str] = None) -> bool:
    """True if direct adjacency between biome_a and biome_b is allowed."""
    if not biome_a or not biome_b or biome_a == biome_b:
        return True
    data = load_adjacency_data(path)
    prohibited = data.get("prohibited") or []
    for pair in prohibited:
        if len(pair) == 2:
            if (pair[0] == biome_a and pair[1] == biome_b) or (pair[1] == biome_a and pair[0] == biome_b):
                return False
    return True


def suggest_buffer(biome_a: str, biome_b: str, count: int = 1, path: Optional[str] = None) -> List[str]:
    """Suggest intermediate buffer biome(s) between contrasting biomes.

    Returns a list of intermediate biome names (length <= count).
    """
    if not biome_a or not biome_b or biome_a == biome_b:
        return []
    data = load_adjacency_data(path)
    gradients = data.get("gradients") or {}

    # Check declared linear gradients first
    for grad in gradients.values():
        if isinstance(grad, list) and biome_a in grad and biome_b in grad:
            idx_a = grad.index(biome_a)
            idx_b = grad.index(biome_b)
            if idx_a < idx_b:
                intermediate = grad[idx_a + 1:idx_b]
            else:
                intermediate = list(reversed(grad[idx_b + 1:idx_a]))
            if intermediate:
                if len(intermediate) <= count:
                    return intermediate
                # Sample evenly if count is smaller than length
                step = len(intermediate) / count
                return [intermediate[int(i * step)] for i in range(count)]

    # Fallback to BFS over affinity graph
    affinities = data.get("affinities") or {}
    if biome_a in affinities and biome_b in affinities:
        visited = {biome_a}
        queue: List[Tuple[str, List[str]]] = [(biome_a, [])]
        while queue:
            curr, path_nodes = queue.pop(0)
            for neighbor in affinities.get(curr, []):
                if neighbor == biome_b:
                    if path_nodes:
                        return path_nodes[:count]
                    return []
                if neighbor not in visited and is_valid_transition(curr, neighbor, path):
                    visited.add(neighbor)
                    queue.append((neighbor, path_nodes + [neighbor]))

    # Default fallback: pick a neutral transitional biome
    if "water" in biome_a or "water" in biome_b:
        return ["shallow_water"] if count == 1 else ["shallow_water", "beach"]
    return ["clearing"] if count == 1 else ["clearing", "sparse_forest"]


def feather_seam(biome_a: str, biome_b: str, steps: int = 2, path: Optional[str] = None) -> List[str]:
    """Generate a feathered sequence of transitional biomes across `steps` intervals."""
    if steps <= 0:
        return []
    buffers = suggest_buffer(biome_a, biome_b, count=steps, path=path)
    if not buffers:
        return [biome_a] * (steps // 2) + [biome_b] * (steps - steps // 2)
    if len(buffers) == steps:
        return buffers
    # Pad or stretch buffers to match requested steps count
    res: List[str] = []
    ratio = len(buffers) / float(steps)
    for i in range(steps):
        idx = min(len(buffers) - 1, int(i * ratio))
        res.append(buffers[idx])
    return res
