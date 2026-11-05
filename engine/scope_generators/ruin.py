"""Subterranean ruin and dungeon child scope procedural generator (task-884).

Implements graph-first spanning tree corridor routing, functional dwarven chamber
infill, and ancient catastrophe decay filters (cave-in collapses, chasm breaches, flooding).

@module ruin
@contributes RuinDungeonGenerator
@docs docs/virtualWorld/Items & Inventory/Items Overview.md
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Set, Tuple
from engine import world_grid as wg
from .base import GenerationConfig, GenerationResult, ScopeGenerator


class RuinDungeonGenerator:
    """Procedural generator for subterranean ruins and dungeon complexes."""

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

        # 1. Establish mandatory landmarks or generate default anchors
        default_landmarks = {
            "grand_gate": (2, height // 2),
            "great_forge": (width - 3, 3),
            "ancestral_vault": (width - 4, height - 4),
            "deep_mine": (width // 2, height - 3),
        }
        for name, default_pos in default_landmarks.items():
            if name in landmarks:
                pos = landmarks[name]
            else:
                pos = default_pos
            # Clamp to grid
            clamped_x = max(1, min(width - 2, pos[0]))
            clamped_y = max(1, min(height - 2, pos[1]))
            placed_landmarks[name] = (clamped_x, clamped_y)

        # Place landmark biomes
        landmark_biomes = {
            "grand_gate": "dwarven_great_gate",
            "great_forge": "dwarven_great_forge",
            "ancestral_vault": "dwarven_ancestral_vault",
            "deep_mine": "dwarven_deep_mine",
        }
        for name, (lx, ly) in placed_landmarks.items():
            key = wg.cell_key(lx, ly)
            biome_layer[key] = landmark_biomes.get(name, "dwarven_colonnade")
            floor_layer[key] = 0

        # 2. Graph-First Spanning Tree: connect all landmarks via corridors
        # Simple MST based on Manhattan distance between landmark points
        points = list(placed_landmarks.values())
        connected_points = [points[0]]
        unconnected_points = points[1:]

        corridor_cells: Set[Tuple[int, int]] = set()

        while unconnected_points:
            best_dist = 999999
            best_pair = (connected_points[0], unconnected_points[0])
            best_u_idx = 0

            for c_pt in connected_points:
                for u_idx, u_pt in enumerate(unconnected_points):
                    dist = abs(c_pt[0] - u_pt[0]) + abs(c_pt[1] - u_pt[1])
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (c_pt, u_pt)
                        best_u_idx = u_idx

            p1, p2 = best_pair
            unconnected_points.pop(best_u_idx)
            connected_points.append(p2)

            # Carve L-shaped corridor between p1 and p2
            x, y = p1
            tx, ty = p2
            while x != tx:
                x += 1 if tx > x else -1
                corridor_cells.add((x, y))
            while y != ty:
                y += 1 if ty > y else -1
                corridor_cells.add((x, y))

        for cx, cy in corridor_cells:
            key = wg.cell_key(cx, cy)
            if key not in biome_layer:
                biome_layer[key] = "corridor"
                road_layer[key] = "cobblestone_road"
                floor_layer[key] = 0

        # 3. Secondary chamber expansion off corridor spine
        chambers = [
            "dwarven_smelting_works", "dwarven_mechanists_guild",
            "dwarven_colonnade", "dwarven_thane_throne",
            "dwarven_brewhouse", "dwarven_scriptorium",
            "dwarven_crystal_geode"
        ]
        seed_val = config.seed
        budget_spent = 15000 + len(corridor_cells) * 50

        room_idx = 0
        sorted_corridors = sorted(corridor_cells)
        for cx, cy in sorted_corridors:
            if (seed_val + cx * 7 + cy * 13) % 4 == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rx, ry = cx + dx, cy + dy
                    if 0 < rx < width - 1 and 0 < ry < height - 1:
                        rkey = wg.cell_key(rx, ry)
                        if rkey not in biome_layer:
                            c_type = chambers[(seed_val + room_idx) % len(chambers)]
                            biome_layer[rkey] = c_type
                            floor_layer[rkey] = 0
                            budget_spent += 800
                            room_idx += 1
                            break

        # 4. Catastrophe and decay pass
        catastrophe_type = config.catastrophe or ("collapse" if seed_val % 2 == 0 else "flood")
        decay_rate = config.decay_rate

        all_keys = list(biome_layer.keys())
        decay_count = int(len(all_keys) * decay_rate)

        decayed_cells = 0
        if catastrophe_type == "collapse":
            for i in range(decay_count):
                idx = (seed_val + i * 11) % len(all_keys)
                k = all_keys[idx]
                if biome_layer[k] not in ("dwarven_great_gate", "dwarven_great_forge"):
                    biome_layer[k] = "dwarven_collapsed_shaft"
                    hazards_layer[k] = {"hazard_id": "fall", "strength": 10}
                    decayed_cells += 1
        elif catastrophe_type == "flood":
            for i in range(decay_count):
                idx = (seed_val + i * 17) % len(all_keys)
                k = all_keys[idx]
                if biome_layer[k] not in ("dwarven_great_gate", "dwarven_great_forge"):
                    biome_layer[k] = "deep_water"
                    hazards_layer[k] = {"hazard_id": "river", "strength": 5}
                    decayed_cells += 1
        elif catastrophe_type == "chasm":
            # Splice chasm breach through center
            chasm_x = width // 2
            for cy in range(height):
                ckey = wg.cell_key(chasm_x, cy)
                if ckey in biome_layer:
                    biome_layer[ckey] = "chasm"
                    hazards_layer[ckey] = {"hazard_id": "fall", "strength": 20, "damage": "20d6"}
                    decayed_cells += 1

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
                "type": "ruin",
                "width": width,
                "height": height,
                "catastrophe": catastrophe_type,
                "decayed_cells": decayed_cells,
                "corridor_length": len(corridor_cells),
            }
        )
