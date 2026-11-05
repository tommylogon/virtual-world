"""Settlement child scope procedural generator (task-884).

Generates central civic squares, arterial avenues, alleys, and zoned building lots.

@module settlement
@contributes SettlementGenerator
@docs docs/virtualWorld/World Building/Graph System.md
"""

from __future__ import annotations

from typing import Dict, List, Tuple
from engine import world_grid as wg
from .base import GenerationConfig, GenerationResult, ScopeGenerator


class SettlementGenerator:
    """Procedural generator for town and village child scopes."""

    def generate(
        self,
        grid_bounds: Tuple[int, int],
        landmarks: Dict[str, Tuple[int, int]],
        config: GenerationConfig,
    ) -> GenerationResult:
        width, height = grid_bounds
        cx, cy = width // 2, height // 2

        biome_layer: Dict[str, str] = {}
        road_layer: Dict[str, str] = {}
        floor_layer: Dict[str, int] = {}
        hazards_layer: Dict[str, dict] = {}
        placed_landmarks: Dict[str, Tuple[int, int]] = {}

        # 1. Place central square or authored landmarks
        if "town_square" in landmarks:
            cx, cy = landmarks["town_square"]
            placed_landmarks["town_square"] = (cx, cy)
        else:
            placed_landmarks["town_square"] = (cx, cy)

        # 2x2 or 3x3 central square
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = cx + dx, cy + dy
                if 0 <= x < width and 0 <= y < height:
                    key = wg.cell_key(x, y)
                    biome_layer[key] = "courtyard"
                    road_layer[key] = "cobblestone_road"
                    floor_layer[key] = 0

        # 2. Carve cardinal arterial avenues from center to borders
        # North / South
        for y in range(height):
            for x in (cx - 1, cx):
                key = wg.cell_key(x, y)
                if key not in road_layer:
                    road_layer[key] = "cobblestone_road"
                    biome_layer[key] = "cobblestone_road"
                    floor_layer[key] = 0

        # East / West
        for x in range(width):
            for y in (cy - 1, cy):
                key = wg.cell_key(x, y)
                if key not in road_layer:
                    road_layer[key] = "cobblestone_road"
                    biome_layer[key] = "cobblestone_road"
                    floor_layer[key] = 0

        # 3. Zoned building lots with frontages
        building_biomes = [
            "tavern", "shopfront", "workshop", "apothecary",
            "residential", "bakery", "smithy", "cottage"
        ]

        seed_val = config.seed
        budget_spent = 5000  # Base street paving cost

        lot_index = 0
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                key = wg.cell_key(x, y)
                if key in road_layer or key in biome_layer:
                    continue

                # Check if adjacent to road
                adj_to_road = False
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nx, ny = x + dx, y + dy
                    if wg.cell_key(nx, ny) in road_layer:
                        adj_to_road = True
                        break

                if adj_to_road:
                    # Deterministic pick from building biomes
                    lot_choice = building_biomes[(seed_val + lot_index * 7) % len(building_biomes)]
                    biome_layer[key] = lot_choice
                    floor_layer[key] = 0
                    budget_spent += 600
                    lot_index += 1
                else:
                    # Secondary yard or garden
                    if (seed_val + x * 3 + y * 5) % 3 == 0:
                        biome_layer[key] = "garden"
                    else:
                        biome_layer[key] = "clearing"
                    floor_layer[key] = 0
                    budget_spent += 150

        layers = {
            "biome": biome_layer,
            "road": road_layer,
            "floor": floor_layer,
            "hazards": hazards_layer,
        }

        return GenerationResult(
            layers=layers,
            landmarks_placed=placed_landmarks,
            budget_spent=budget_spent,
            cells_painted=len(biome_layer),
            report={
                "type": "settlement",
                "width": width,
                "height": height,
                "lots_zoned": lot_index,
            }
        )
