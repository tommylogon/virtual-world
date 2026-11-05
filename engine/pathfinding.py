"""Intra-area grid pathfinding (task-99).

A* pathfinding across 2D area grids with per-tile movement costs,
obstacle avoidance, and optional diagonal movement.

@module pathfinding
@contributes get_tile, get_tile_cost, is_passable, calculate_path_cost, find_path, find_path_to_adjacent
@docs docs/virtualWorld/World Building/WorldPainter.md
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple, Any

DEFAULT_TILE_COSTS: Dict[str, int] = {
    "floor": 1,
    "carpet": 1,
    "stairs": 1,
    "water": 2,
    "rubble": 3,
    "wall": 99,
}

IMPASSABLE_COST = 99


def get_tile(grid: dict, x: int, y: int) -> Optional[str]:
    """Return tile type at (x, y), or None if out of bounds."""
    width = grid.get("width", 0)
    height = grid.get("height", 0)
    if x < 0 or x >= width or y < 0 or y >= height:
        return None
    tiles = grid.get("tiles")
    if not tiles or not isinstance(tiles, list):
        return "floor"
    if y >= len(tiles):
        return "floor"
    row = tiles[y]
    if not isinstance(row, list) or x >= len(row):
        return "floor"
    return str(row[x]).lower()


def get_tile_cost(grid: dict, x: int, y: int) -> int:
    """Return the movement cost to enter tile at (x, y)."""
    tile = get_tile(grid, x, y)
    if tile is None:
        return IMPASSABLE_COST
    costs = grid.get("costs") or DEFAULT_TILE_COSTS
    return int(costs.get(tile, DEFAULT_TILE_COSTS.get(tile, 1)))


def is_passable(grid: dict, x: int, y: int) -> bool:
    """True if tile at (x, y) can be walked through."""
    tile = get_tile(grid, x, y)
    if tile is None or tile == "wall":
        return False
    return get_tile_cost(grid, x, y) < IMPASSABLE_COST


def calculate_path_cost(grid: dict, path: List[Tuple[int, int]]) -> int:
    """Calculate the total movement cost of a path (excluding starting tile)."""
    if not path or len(path) <= 1:
        return 0
    total = 0
    for x, y in path[1:]:
        total += get_tile_cost(grid, x, y)
    return total


def find_path(
    grid: dict,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    allow_diagonal: bool = False,
) -> Optional[List[Tuple[int, int]]]:
    """Find the lowest-cost path from start to goal on grid using A*.

    Returns a list of (x, y) coordinates from start to goal inclusive,
    or None if no passable path exists.
    """
    sx, sy = start
    gx, gy = goal

    if not is_passable(grid, sx, sy) or not is_passable(grid, gx, gy):
        return None

    if start == goal:
        return [start]

    width = grid.get("width", 0)
    height = grid.get("height", 0)

    # Heuristic function
    def _heuristic(x: int, y: int) -> float:
        dx = abs(x - gx)
        dy = abs(y - gy)
        if allow_diagonal:
            return max(dx, dy)
        return dx + dy

    # Priority queue: (f_score, h_score, (x, y))
    frontier: List[Tuple[float, float, Tuple[int, int]]] = []
    heapq.heappush(frontier, (_heuristic(sx, sy), _heuristic(sx, sy), (sx, sy)))

    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    cost_so_far: Dict[Tuple[int, int], int] = {(sx, sy): 0}

    # Movement deltas
    deltas = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if allow_diagonal:
        deltas.extend([(1, 1), (-1, 1), (1, -1), (-1, -1)])

    while frontier:
        _, _, current = heapq.heappop(frontier)

        if current == goal:
            # Reconstruct path
            path = [current]
            curr = current
            while curr in came_from:
                curr = came_from[curr]
                path.append(curr)
            path.reverse()
            return path

        cx, cy = current
        for dx, dy in deltas:
            nx, ny = cx + dx, cy + dy
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                continue

            if not is_passable(grid, nx, ny):
                continue

            # In diagonal movement, prevent cutting corners between impassable tiles
            if allow_diagonal and dx != 0 and dy != 0:
                if not is_passable(grid, cx + dx, cy) or not is_passable(grid, cx, cy + dy):
                    continue

            step_cost = get_tile_cost(grid, nx, ny)
            new_cost = cost_so_far[current] + step_cost

            if (nx, ny) not in cost_so_far or new_cost < cost_so_far[(nx, ny)]:
                cost_so_far[(nx, ny)] = new_cost
                priority = new_cost + _heuristic(nx, ny)
                heapq.heappush(frontier, (priority, _heuristic(nx, ny), (nx, ny)))
                came_from[(nx, ny)] = current

    return None


def find_path_to_adjacent(
    grid: dict,
    start: Tuple[int, int],
    target: Tuple[int, int],
    allow_diagonal: bool = False,
) -> Optional[List[Tuple[int, int]]]:
    """Find shortest path from start to any passable tile adjacent to target."""
    tx, ty = target
    deltas = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if allow_diagonal:
        deltas.extend([(1, 1), (-1, 1), (1, -1), (-1, -1)])

    best_path = None
    best_cost = float("inf")

    for dx, dy in deltas:
        adj = (tx + dx, ty + dy)
        path = find_path(grid, start, adj, allow_diagonal=allow_diagonal)
        if path:
            cost = calculate_path_cost(grid, path)
            if cost < best_cost:
                best_cost = cost
                best_path = path

    return best_path
