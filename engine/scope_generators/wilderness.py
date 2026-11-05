"""Wilderness and river reach child scope procedural generator (task-884).

Generates natural channel carving, elevation-conforming terrain, and Markov
adjacency buffer feathering between aquatic, clearing, and dense woodland biomes.

@module wilderness
@contributes WildernessGenerator
@docs docs/virtualWorld/Gameplay/The Commons.md
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple
from engine import world_grid as wg
from engine import world_adjacencies
from .base import GenerationConfig, GenerationResult, ScopeGenerator


class WildernessGenerator:
    """Procedural generator for wilderness, river reach, and valley child scopes."""

    def generate(
        self,
        grid_bounds: Tuple[int, int],
        landmarks: Dict[str, Tuple[int, int]],
        config: GenerationConfig,
    ) -> GenerationResult:
        width, height = grid_bounds

        biome_layer: Dict[str, str] = {}
        road_layer: Dict[str, str] = {}
        floor_layer: Dict[str, int] = {}
        hazards_layer: Dict[str, dict] = {}
        placed_landmarks: Dict[str, Tuple[int, int]] = {}

        seed_val = config.seed

        # 1. Carve sinuous river channel from north to south
        # Centerline oscillates via sine wave
        channel_cells: List[Tuple[int, int]] = []
        for y in range(height):
            # Sinuous curve
            offset = int(math.sin((y + seed_val) * 0.4) * (width * 0.25))
            cx = (width // 2) + offset
            cx = max(1, min(width - 2, cx))
            channel_cells.append((cx, y))

        # River width (1-2 cells)
        water_cells: set = set()
        for cx, y in channel_cells:
            water_cells.add((cx, y))
            key = wg.cell_key(cx, y)
            biome_layer[key] = "river"
            floor_layer[key] = max(0, (height - y) // 4)  # Elevation gradient down
            hazards_layer[key] = {"hazard_id": "river", "strength": 5}

        # 2. Markov Adjacency Buffer: feather outward from river
        # Buffer rings: shallow_water/banks -> clearing -> sparse_forest -> dense_forest
        gradient = ["shallow_water", "beach", "clearing", "sparse_forest", "dense_forest"]

        for y in range(height):
            for x in range(width):
                key = wg.cell_key(x, y)
                if key in biome_layer:
                    continue

                # Distance to closest water cell
                min_dist = min(abs(x - wx) for wx, wy in channel_cells if wy == y)
                grad_idx = min(len(gradient) - 1, max(0, min_dist - 1))
                chosen_biome = gradient[grad_idx]

                biome_layer[key] = chosen_biome
                floor_layer[key] = max(0, (height - y) // 4)

        # Place landmark if specified
        if "ford" in landmarks:
            fx, fy = landmarks["ford"]
            placed_landmarks["ford"] = (fx, fy)
            road_layer[wg.cell_key(fx, fy)] = "ford"

        layers = {
            "biome": biome_layer,
            "road": road_layer,
            "floor": floor_layer,
            "hazards": hazards_layer,
        }

        return GenerationResult(
            layers=layers,
            landmarks_placed=placed_landmarks,
            budget_spent=25000,
            cells_painted=len(biome_layer),
            report={
                "type": "wilderness",
                "width": width,
                "height": height,
                "river_length": len(channel_cells),
            }
        )
